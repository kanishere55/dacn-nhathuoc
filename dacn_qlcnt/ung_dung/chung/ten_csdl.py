from django.db import models
from django.db.models import Q

from .so_hoc import KhongPhaiNaN
from .van_ban import DaCatKhoangTrang, KhongRong, LaMotDong

MA_NGHIEP_VU = r"^[A-Z0-9][A-Z0-9_-]{0,31}$"
MA_UUID = r"^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$"
# Email lưu chữ thường sau khi chuẩn hóa ở form; phần tên miền phải có dấu chấm.
EMAIL = r"^[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)+$"
# Số điện thoại Việt Nam dạng nội địa: di động 10 chữ số, cố định 11 chữ số.
SO_DIEN_THOAI = r"^0[0-9]{9,10}$"

# Chỉ rút gọn tên bảng trong tên ràng buộc khi tên đầy đủ vượt giới hạn PostgreSQL.
TEN_RUT_GON = {
    "chi_tiet_phieu_nhap": "ct_nhap",
    "phieu_tra_nha_cung_cap": "tra_ncc",
    "chi_tiet_phieu_tra_nha_cung_cap": "ct_tra_ncc",
    "chi_tiet_phieu_dieu_chuyen": "ct_dieu_chuyen",
    "chi_tiet_phieu_kiem_ke": "ct_kiem_ke",
    "chi_tiet_phieu_ban": "ct_ban",
    "chi_tiet_don_dat_giu": "ct_dat_giu",
    "phan_bo_dat_giu": "pb_giu",
    "chi_tiet_don_hang": "ct_don_hang",
    "phan_bo_phieu_ban": "pb_ban",
    "phan_bo_don_hang": "pb_don_hang",
    "chi_tiet_phieu_hoan_kho": "ct_hoan_kho",
    "giao_dich_thanh_toan": "giao_dich",
    "chi_tiet_tra_hang": "ct_tra",
    "yeu_cau_tra_hang": "tra_hang",
    "thong_tin_cua_hang": "cua_hang",
    "banner_trang_chu": "banner",
    "trang_noi_dung": "trang",
    "ket_qua_mo_hinh": "ket_qua",
    "du_bao_bay_ngay": "du_bao",
    "quan_sat_ban_hang": "quan_sat",
    "phien_xac_thuc": "xac_thuc",
}


def ten_rang_buoc(loai, bang, *mo_ta):
    ten = "__".join((loai, TEN_RUT_GON.get(bang, bang), *mo_ta))
    if len(ten.encode()) > 63:
        raise ValueError(f"Tên CSDL vượt 63 byte, cần đăng ký tên rút gọn: {ten}")
    return ten


def rang_buoc_van_ban(bang, cot, *, rong=False, nhieu_dong=False, dinh_dang=None, nhan=None):
    cac_luat = [(DaCatKhoangTrang(cot), "da_cat_khoang_trang")]
    if not rong:
        cac_luat.append((KhongRong(cot), "khong_rong"))
    if not nhieu_dong:
        cac_luat.append((LaMotDong(cot), "mot_dong"))
    if dinh_dang is None and cot.startswith("ma_"):
        dinh_dang = MA_NGHIEP_VU
    if dinh_dang:
        cac_luat.append((Q(**{f"{cot}__regex": dinh_dang}), "dung_dinh_dang"))
    # `nhan` đặt tên cột trong tên ràng buộc khi cột ma_/ten_ không phải định danh của bảng.
    ten_cot = nhan or ("ma" if cot.startswith("ma_") else "ten" if cot.startswith("ten_") else cot)
    return [
        models.CheckConstraint(
            condition=bieu_thuc, name=ten_rang_buoc("kiem_tra", bang, f"{ten_cot}_{luat}")
        )
        for bieu_thuc, luat in cac_luat
    ]


def rang_buoc_so(bang, cot, *, duong=False, tien=False):
    cac_luat = [
        models.CheckConstraint(
            condition=Q(**{f"{cot}__gt" if duong else f"{cot}__gte": 0}),
            name=ten_rang_buoc("kiem_tra", bang, f"{cot}_{'duong' if duong else 'khong_am'}"),
        )
    ]
    if tien:
        cac_luat.append(
            models.CheckConstraint(
                condition=KhongPhaiNaN(cot),
                name=ten_rang_buoc("kiem_tra", bang, f"{cot}_khong_phai_nan"),
            )
        )
    return cac_luat


def chuan_hoa_v1(apps, schema_editor, ten_app, *, dao=False):
    from psycopg import sql

    with schema_editor.connection.cursor() as con_tro:
        for model in apps.get_app_config(ten_app).get_models():
            bang = model._meta.db_table
            con_tro.execute(
                "SELECT conname, contype, conkey, pg_get_constraintdef(oid), confdeltype FROM pg_constraint WHERE conrelid = %s::regclass AND contype IN ('p','f')",
                [bang],
            )
            for ten_cu, loai, cot, dinh_nghia, hanh_vi in con_tro.fetchall():
                if loai == "p":
                    ten_moi = (
                        bang + "_pkey"
                        if dao and bang != "tai_khoan"
                        else ten_rang_buoc("khoa_chinh", bang)
                    )
                    if ten_cu != ten_moi:
                        con_tro.execute(
                            sql.SQL("ALTER TABLE {} RENAME CONSTRAINT {} TO {}").format(
                                sql.Identifier(bang),
                                sql.Identifier(ten_cu),
                                sql.Identifier(ten_moi),
                            )
                        )
                else:
                    con_tro.execute(
                        "SELECT attname FROM pg_attribute WHERE attrelid = %s::regclass AND attnum = ANY(%s) ORDER BY attnum",
                        [bang, list(cot)],
                    )
                    ten_cot = [dong[0] for dong in con_tro.fetchall()]
                    ten_moi = ten_rang_buoc("khoa_ngoai", bang, *ten_cot)
                    if not dao and ten_cu == ten_moi and hanh_vi == "r":
                        continue
                    con_tro.execute(
                        sql.SQL("ALTER TABLE {} DROP CONSTRAINT {}").format(
                            sql.Identifier(bang), sql.Identifier(ten_cu)
                        )
                    )
                    if dao:
                        truong = next(
                            truong
                            for truong in model._meta.local_fields
                            if truong.column == ten_cot[0]
                        )
                        schema_editor.execute(
                            schema_editor._create_fk_sql(
                                model, truong, "_fk_%(to_table)s_%(to_column)s"
                            )
                        )
                        continue
                    dinh_nghia = (
                        dinh_nghia.split(" ON DELETE")[0]
                        .split(" NOT DEFERRABLE")[0]
                        .split(" DEFERRABLE")[0]
                    )
                    con_tro.execute(
                        sql.SQL(
                            "ALTER TABLE {} ADD CONSTRAINT {} {} ON DELETE RESTRICT NOT DEFERRABLE"
                        ).format(sql.Identifier(bang), sql.Identifier(ten_moi), sql.SQL(dinh_nghia))
                    )
            con_tro.execute(
                "SELECT i.indexrelid::regclass::text, array_agg(a.attname ORDER BY k.thu_tu) FROM pg_index i CROSS JOIN LATERAL unnest(i.indkey) WITH ORDINALITY k(attnum,thu_tu) JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.attnum WHERE i.indrelid=%s::regclass AND NOT i.indisunique GROUP BY i.indexrelid",
                [bang],
            )
            for ten_cu, cac_cot in con_tro.fetchall():
                ten_moi = ten_rang_buoc("chi_muc", bang, *cac_cot)
                if dao:
                    truong = next(
                        (
                            truong
                            for truong in model._meta.local_fields
                            if truong.column == cac_cot[0]
                        ),
                        None,
                    )
                    ten_moi = (
                        schema_editor._create_spatial_index_name(model, truong)
                        if getattr(truong, "spatial_index", False)
                        else schema_editor._create_index_name(bang, cac_cot)
                    )
                if ten_cu != ten_moi:
                    con_tro.execute(
                        sql.SQL("ALTER INDEX {} RENAME TO {}").format(
                            sql.Identifier(ten_cu), sql.Identifier(ten_moi)
                        )
                    )
            if dao:
                con_tro.execute(
                    """SELECT conname FROM pg_constraint WHERE conrelid=%s::regclass
                       AND contype='c' AND obj_description(oid, 'pg_constraint') LIKE 'Lớp bảo vệ cuối của CSDL,%%'""",
                    [bang],
                )
                for (ten,) in con_tro.fetchall():
                    con_tro.execute(
                        sql.SQL("COMMENT ON CONSTRAINT {} ON {} IS NULL").format(
                            sql.Identifier(ten), sql.Identifier(bang)
                        )
                    )
                continue
            con_tro.execute(
                "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid=%s::regclass AND contype='c' AND obj_description(oid, 'pg_constraint') IS NULL",
                [bang],
            )
            for ten, dinh_nghia in con_tro.fetchall():
                con_tro.execute(
                    sql.SQL("COMMENT ON CONSTRAINT {} ON {} IS {}").format(
                        sql.Identifier(ten),
                        sql.Identifier(bang),
                        sql.Literal(
                            "Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: " + dinh_nghia
                        ),
                    )
                )
