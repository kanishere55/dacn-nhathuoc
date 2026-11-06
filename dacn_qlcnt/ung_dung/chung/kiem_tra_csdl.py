"""Đối chiếu catalog thật với tên, kiểu và index của các model nghiệp vụ."""

import re
from collections import defaultdict

from django.apps import apps

from .ten_csdl import ten_rang_buoc
from .tu_dien_csdl import DINH_DANH_CO_BOI_CANH, TEN_CAM, TIEN_TO_BOOLEAN, TIEN_TO_CAM, TU_VUNG

BANG_DJANGO = {
    "auth_group",
    "auth_group_permissions",
    "auth_permission",
    "django_admin_log",
    "django_content_type",
    "django_migrations",
    "django_session",
}


def kiem_ten(ten, bao_loi, *, co_phan_cach=False):
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", ten):
        bao_loi("L01", f"Tên không đúng mẫu hoặc vượt 63 byte: {ten}")
    tu_la = set(ten.replace("__", "_").split("_")) - TU_VUNG
    if tu_la:
        bao_loi("L02", f"Từ chưa đăng ký trong {ten}: {', '.join(sorted(tu_la))}")
    if not co_phan_cach and ("__" in ten or ten in TEN_CAM or ten.startswith(TIEN_TO_CAM)):
        bao_loi("L03", f"Tên bảng/cột dùng dấu phân cách hoặc từ cấm: {ten}")


def kiem_cot(truong, thong_tin, checks, ket_noi, bao_loi):
    cot = truong.column
    kieu, bat_buoc, mac_dinh, chu_thich, loai_pg = thong_tin
    bang = truong.model._meta.db_table
    kieu_model = truong.db_type(ket_noi).lower().replace("varchar", "character varying")
    if kieu.lower().replace(", ", ",") != kieu_model.replace(", ", ",") or bat_buoc == truong.null:
        bao_loi("L05", f"{cot} có kiểu hoặc NULL khác khai báo: {kieu}")
    if cot.startswith("id_") and not (truong.primary_key or truong.many_to_one):
        bao_loi("L05", f"{cot} dùng tiền tố id_ nhưng không phải khóa")
    if truong.many_to_one:
        cot_dich = truong.target_field.column
        if cot != cot_dich and not cot.startswith(cot_dich + "_"):
            bao_loi("L05", f"{cot} phải giữ tên hoặc tiền tố khóa chính {cot_dich}")
    if (
        cot.startswith(("ma_", "ten_"))
        and cot.split("_", 1)[1] != bang
        and (bang, cot) not in DINH_DANH_CO_BOI_CANH
    ):
        bao_loi("L06", f"{cot} thiếu bối cảnh định danh đã đăng ký")
    if kieu == "boolean" and (not bat_buoc or not cot.startswith(TIEN_TO_BOOLEAN)):
        bao_loi("L07", f"{cot} phải có tiền tố boolean và NOT NULL")
    if cot.startswith("ngay_") and kieu != "date":
        bao_loi("L07", f"{cot} phải có kiểu date")
    if cot.startswith("thoi_diem_") and kieu != "timestamp with time zone":
        bao_loi("L07", f"{cot} phải có kiểu timestamptz")
    if (
        kieu in {"money", "json", "timestamp without time zone"}
        or kieu.startswith("character(")
        or loai_pg == "e"
    ):
        bao_loi("L09", f"{cot} dùng kiểu bị cấm: {kieu}")
    if kieu in {"real", "double precision"} and "xấp xỉ" not in (chu_thich or ""):
        bao_loi("L09", f"{cot} kiểu số thực chưa chú thích là giá trị xấp xỉ")
    tap_gia_tri = next((check for check in checks if " = ANY (ARRAY[" in check), "")
    if cot.startswith(("trang_thai", "loai_")) or cot in {
        "loai",
        "vai_tro",
        "mo_hinh",
        "ky_danh_gia",
    }:
        if not tap_gia_tri:
            bao_loi("L10", f"{cot} thiếu CHECK giới hạn tập giá trị")
        for gia_tri in re.findall(r"'([a-z][a-z0-9_]*)'::text", tap_gia_tri):
            kiem_ten(gia_tri, bao_loi)
    if (
        (kieu == "text" or kieu.startswith("character varying"))
        and bat_buoc
        and not (mac_dinh or "").startswith("''")
        and not tap_gia_tri
        and not any("khong_rong(" in check or " ~ " in check for check in checks)
    ):
        bao_loi("L11", f"{cot} thiếu CHECK từ chối chuỗi rỗng")
    if kieu.startswith("numeric") and not any("'NaN'::numeric" in check for check in checks):
        bao_loi("L12", f"{cot} thiếu CHECK chặn NaN")
    if cot.startswith("ma_") and not any(" ~ " in check for check in checks):
        bao_loi("L11", f"{cot} thiếu CHECK đúng định dạng mã")
    if not chu_thich or chu_thich != truong.db_comment:
        bao_loi("L13", f"{cot} thiếu chú thích hoặc lệch chú thích model")
    if kieu.startswith(("character varying(", "numeric(")) and not re.search(
        r"ký tự|chữ số", chu_thich or ""
    ):
        bao_loi("L13", f"{cot} thiếu lý do cho giới hạn kiểu dữ liệu")


def doc_cot(con_tro, bang):
    con_tro.execute(
        """
        SELECT a.attnum, a.attname, format_type(a.atttypid, a.atttypmod), a.attnotnull,
               pg_get_expr(d.adbin, d.adrelid), col_description(a.attrelid, a.attnum), t.typtype
        FROM pg_attribute a
        JOIN pg_type t ON t.oid = a.atttypid
        LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
        WHERE a.attrelid = %s::regclass AND a.attnum > 0 AND NOT a.attisdropped
        """,
        [bang],
    )
    return {ten: (so, thong_tin) for so, ten, *thong_tin in con_tro.fetchall()}


def kiem_bang(con_tro, ket_noi, model, them_loi, them_canh_bao):
    meta = model._meta
    bang = meta.db_table

    def loi(ma, chi_tiet):
        them_loi(f"{ma} {bang} · {chi_tiet}")

    kiem_ten(bang, loi)
    cot = doc_cot(con_tro, bang)
    truong = {f.column: f for f in meta.local_fields}
    if cot.keys() != truong.keys():
        loi("L05", f"Cột khác model: {', '.join(sorted(cot.keys() ^ truong.keys()))}")
    pk = ten_rang_buoc("khoa_chinh", bang)
    ngoai = {
        ten_rang_buoc("khoa_ngoai", bang, f.column): f
        for f in truong.values()
        if f.many_to_one and f.db_constraint
    }
    khai_bao = {r.name: r for r in meta.constraints}
    mong_doi = {pk, *ngoai, *khai_bao}
    chi_muc = {
        ten_rang_buoc("chi_muc", bang, f.column)
        for f in truong.values()
        if (f.db_index and not f.unique) or getattr(f, "spatial_index", False)
    } | {idx.name for idx in meta.indexes}
    checks = defaultdict(list)
    cac_khoa_ngoai = {}
    con_tro.execute(
        """
        SELECT conname, contype, conkey, confdeltype, condeferrable, convalidated,
               pg_get_constraintdef(oid), obj_description(oid, 'pg_constraint'),
               confrelid::regclass::text,
               ARRAY(SELECT a.attname FROM pg_attribute a
                     WHERE a.attrelid = c.confrelid AND a.attnum = ANY(c.confkey))
        FROM pg_constraint c
        WHERE conrelid = %s::regclass AND contype IN ('p', 'f', 'u', 'c')
        """,
        [bang],
    )
    thuc_te = set()
    for (
        ten,
        loai,
        so_cot,
        on_delete,
        tri_hoan,
        da_kiem,
        dinh_nghia,
        chu_thich,
        bang_dich,
        cot_dich,
    ) in con_tro.fetchall():
        thuc_te.add(ten)
        kiem_ten(ten, loi, co_phan_cach=True)
        if not da_kiem:
            loi("L08", f"Ràng buộc chưa VALIDATE: {ten}")
        if loai == "p":
            if so_cot != [cot.get(f"id_{bang}", (None,))[0]]:
                loi("L04", f"Khóa chính phải gồm đúng id_{bang}")
            chi_muc.add(ten)
        elif loai == "f":
            cac_khoa_ngoai[ten] = so_cot
            if ten not in ngoai or on_delete != "r" or tri_hoan:
                loi("L08", f"Khóa ngoại sai tên hoặc không dùng RESTRICT: {ten}")
            if ten in ngoai:
                f = ngoai[ten]
                if (
                    bang_dich != f.related_model._meta.db_table
                    or cot_dich != [f.target_field.column]
                    or so_cot != [cot.get(f.column, (None,))[0]]
                ):
                    loi("L05", f"Khóa ngoại khác cột hoặc đích đã khai báo: {ten}")
        elif loai == "u":
            if ten in khai_bao:
                cac_cot = [meta.get_field(f).column for f in khai_bao[ten].fields]
                if ten != ten_rang_buoc("duy_nhat", bang, *cac_cot):
                    loi("L08", f"Tên UNIQUE không theo thứ tự cột: {ten}")
                if so_cot != [cot.get(c, (None,))[0] for c in cac_cot]:
                    loi("L08", f"UNIQUE dùng cột khác khai báo: {ten}")
            chi_muc.add(ten)
        else:
            if not ten.startswith(ten_rang_buoc("kiem_tra", bang) + "__"):
                loi("L08", f"Tên CHECK không đúng mẫu: {ten}")
            if not chu_thich:
                loi("L13", f"CHECK thiếu chú thích: {ten}")
            if "btrim(" in dinh_nghia:
                loi("L11", f"CHECK dùng btrim: {ten}")
            for so in so_cot or []:
                checks[so].append(dinh_nghia)
    if thuc_te != mong_doi:
        loi("L08", f"Ràng buộc khác model: {', '.join(sorted(thuc_te ^ mong_doi))}")
    for ten in sorted(cot):
        kiem_ten(ten, loi)
        if ten in truong:
            so, thong_tin = cot[ten]
            kiem_cot(truong[ten], thong_tin, checks[so], ket_noi, loi)
    kiem_chi_muc(con_tro, bang, chi_muc, cac_khoa_ngoai, loi, them_canh_bao)


def kiem_chi_muc(con_tro, bang, mong_doi, cac_khoa_ngoai, loi, them_canh_bao):
    con_tro.execute(
        """
        SELECT c.relname, i.indisvalid, i.indpred IS NULL,
               (i.indkey::smallint[])[0:i.indnkeyatts-1], pg_get_indexdef(i.indexrelid)
        FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid
        WHERE i.indrelid = %s::regclass
        """,
        [bang],
    )
    thuc_te = set()
    bieu_thuc = {}
    cac_khoa_co_chi_muc = []
    for ten, hop_le, toan_bang, cac_cot, dinh_nghia in con_tro.fetchall():
        thuc_te.add(ten)
        kiem_ten(ten, loi, co_phan_cach=True)
        if not hop_le:
            loi("L14", f"Index chưa hợp lệ: {ten}")
        if hop_le and toan_bang:
            cac_khoa_co_chi_muc.append(cac_cot)
        dinh_nghia = re.sub(r"^(CREATE (?:UNIQUE )?INDEX) \S+", r"\1", dinh_nghia)
        if dinh_nghia in bieu_thuc:
            them_canh_bao(f"L16 {bang} · {ten} trùng {bieu_thuc[dinh_nghia]}")
        bieu_thuc[dinh_nghia] = ten
    if thuc_te != mong_doi:
        loi("L14", f"Index khác khai báo: {', '.join(sorted(thuc_te ^ mong_doi))}")
    for ten, cot in cac_khoa_ngoai.items():
        if not any(idx[: len(cot)] == cot for idx in cac_khoa_co_chi_muc):
            them_canh_bao(f"L15 {bang} · {ten} chưa có index dẫn đầu phù hợp")


def kiem_tra_csdl(ket_noi):
    cac_loi, cac_canh_bao = [], []
    mong_doi = {
        m._meta.db_table: m
        for m in apps.get_models()
        if m._meta.app_config.name.startswith("ung_dung.") and m._meta.managed
    }
    with ket_noi.cursor() as con_tro:
        con_tro.execute(
            """
            SELECT c.relname, obj_description(c.oid, 'pg_class')
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = current_schema() AND c.relkind IN ('r', 'p', 'v', 'm')
              AND NOT EXISTS (
                  SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_class'::regclass
                    AND d.objid = c.oid AND d.deptype = 'e'
              )
            """
        )
        cac_bang = {ten: mo_ta for ten, mo_ta in con_tro.fetchall() if ten not in BANG_DJANGO}
        if cac_bang.keys() != mong_doi.keys():
            cac_loi.append(
                f"L13 Bảng/view khác model: {', '.join(sorted(cac_bang.keys() ^ mong_doi.keys()))}"
            )
        for bang in sorted(cac_bang.keys() & mong_doi.keys()):
            model = mong_doi[bang]
            if not cac_bang[bang] or cac_bang[bang] != model._meta.db_table_comment:
                cac_loi.append(f"L13 {bang} · Thiếu chú thích hoặc lệch chú thích model")
            kiem_bang(con_tro, ket_noi, model, cac_loi.append, cac_canh_bao.append)
    return len(mong_doi), cac_loi, cac_canh_bao
