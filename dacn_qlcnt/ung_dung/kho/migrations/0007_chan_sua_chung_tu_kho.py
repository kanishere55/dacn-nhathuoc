"""Lớp chặn ở CSDL cho Q02, Q06, Q12: chứng từ kho đã xác nhận không sửa hoặc xóa được.

- Bảng chứng từ kho và nhật ký khóa lô: mọi DELETE bị từ chối; UPDATE bị từ chối, trừ một
  ngoại lệ là chỉnh `thoi_diem_tao` của phiếu được tạo ngay trong cùng giao dịch (chưa
  commit nên chưa ai thấy). Ngoại lệ này phục vụ lệnh dựng lịch sử bán mô phỏng.
  Phiếu mới được ghi nhận vào biến cấu hình cục bộ của giao dịch `dacn.chung_tu_moi`;
  biến tự mất khi giao dịch kết thúc hoặc khi savepoint chứa lệnh INSERT bị hủy.
- Thuốc đã có lô: không đổi đơn vị cơ sở (Q02).
- Lô đã có trong kho: không đổi thuốc hoặc mã lô (Q01, mã lô đã in trên chứng từ).

Migration sau này cần sửa dữ liệu các bảng này phải tạm `ALTER TABLE ... DISABLE TRIGGER`.
"""

from django.db import migrations

BANG_PHIEU = (
    "phieu_nhap",
    "phieu_tra_nha_cung_cap",
    "phieu_dieu_chuyen",
    "phieu_kiem_ke",
    "phieu_xuat_huy",
)
BANG_CHI_TIET = (
    "chi_tiet_phieu_nhap",
    "chi_tiet_phieu_tra_nha_cung_cap",
    "chi_tiet_phieu_dieu_chuyen",
    "chi_tiet_phieu_kiem_ke",
    "chi_tiet_phieu_xuat_huy",
    "lich_su_dieu_kien_lo",
)

HAM = r"""
CREATE OR REPLACE FUNCTION ghi_nhan_chung_tu_moi() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    -- Đánh dấu phiếu vừa tạo trong giao dịch hiện tại; set_config(..., true) chỉ sống tới
    -- cuối giao dịch và được hoàn lại nếu savepoint chứa lệnh INSERT bị hủy.
    PERFORM set_config(
        'dacn.chung_tu_moi',
        coalesce(current_setting('dacn.chung_tu_moi', true), '')
            || ' ' || TG_TABLE_NAME || ':' || (to_jsonb(NEW) ->> ('id_' || TG_TABLE_NAME)) || ' ',
        true
    );
    RETURN NULL;
END;
$$;
COMMENT ON FUNCTION ghi_nhan_chung_tu_moi() IS
    'Ghi nhận phiếu kho tạo trong giao dịch hiện tại để chan_sua_chung_tu_kho cho phép chỉnh thời điểm trước khi commit.';

CREATE OR REPLACE FUNCTION chan_sua_chung_tu_kho() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    khoa text;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        khoa := ' ' || TG_TABLE_NAME || ':' || (to_jsonb(OLD) ->> ('id_' || TG_TABLE_NAME)) || ' ';
        IF (to_jsonb(NEW) - 'thoi_diem_tao') = (to_jsonb(OLD) - 'thoi_diem_tao')
           AND position(khoa IN coalesce(current_setting('dacn.chung_tu_moi', true), '')) > 0 THEN
            RETURN NEW;
        END IF;
    END IF;
    RAISE EXCEPTION 'Chứng từ kho đã xác nhận không được sửa hoặc xóa (bảng %).', TG_TABLE_NAME
        USING ERRCODE = 'restrict_violation',
              HINT = 'Sai sót được điều chỉnh bằng chứng từ mới: kiểm kê, trả nhà cung cấp hoặc xuất hủy.';
END;
$$;
COMMENT ON FUNCTION chan_sua_chung_tu_kho() IS
    'Từ chối UPDATE/DELETE chứng từ kho đã xác nhận (Q06, Q12); chỉ cho chỉnh thoi_diem_tao của phiếu tạo trong cùng giao dịch.';

CREATE OR REPLACE FUNCTION chan_doi_don_vi_thuoc_da_co_lo() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.id_don_vi_tinh IS DISTINCT FROM OLD.id_don_vi_tinh
       AND EXISTS (SELECT 1 FROM lo_thuoc WHERE id_thuoc = OLD.id_thuoc) THEN
        RAISE EXCEPTION 'Không đổi đơn vị cơ sở của thuốc % vì thuốc đã có lô trong kho.', OLD.ma_thuoc
            USING ERRCODE = 'restrict_violation',
                  HINT = 'Tạo thuốc mới với đơn vị đúng và cho thuốc cũ ngừng hoạt động.';
    END IF;
    RETURN NEW;
END;
$$;
COMMENT ON FUNCTION chan_doi_don_vi_thuoc_da_co_lo() IS
    'Q02: đơn vị cơ sở cố định sau khi thuốc có lô, để số lượng trên chứng từ cũ giữ đúng nghĩa.';

CREATE OR REPLACE FUNCTION chan_doi_ma_lo_da_co_ton() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF (NEW.id_thuoc, NEW.ma_lo_thuoc) IS DISTINCT FROM (OLD.id_thuoc, OLD.ma_lo_thuoc)
       AND EXISTS (SELECT 1 FROM ton_kho WHERE id_lo_thuoc = OLD.id_lo_thuoc) THEN
        RAISE EXCEPTION 'Không đổi thuốc hoặc mã của lô % vì lô đã có trong kho và trên chứng từ.', OLD.ma_lo_thuoc
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END;
$$;
COMMENT ON FUNCTION chan_doi_ma_lo_da_co_ton() IS
    'Q01: lô định danh bằng thuốc và mã lô in trên bao bì; lô đã nhập kho thì không đổi định danh.';
"""


def _tach_cau(van_ban):
    """Tách khối SQL thành từng câu ở dòng trống, để không phụ thuộc bộ tách câu khi gặp $$."""
    return [cau.strip() for cau in van_ban.split("\n\n") if cau.strip()]


def tao_trigger():
    cau = _tach_cau(HAM)
    for bang in BANG_PHIEU:
        cau.append(
            f"CREATE TRIGGER ghi_nhan_chung_tu_moi AFTER INSERT ON {bang} "
            "FOR EACH ROW EXECUTE FUNCTION ghi_nhan_chung_tu_moi();"
        )
    for bang in (*BANG_PHIEU, *BANG_CHI_TIET):
        cau.append(
            f"CREATE TRIGGER chan_sua_chung_tu BEFORE UPDATE OR DELETE ON {bang} "
            "FOR EACH ROW EXECUTE FUNCTION chan_sua_chung_tu_kho();"
        )
    cau.append(
        "CREATE TRIGGER chan_doi_don_vi_thuoc BEFORE UPDATE OF id_don_vi_tinh ON thuoc "
        "FOR EACH ROW EXECUTE FUNCTION chan_doi_don_vi_thuoc_da_co_lo();"
    )
    cau.append(
        "CREATE TRIGGER chan_doi_ma_lo BEFORE UPDATE OF id_thuoc, ma_lo_thuoc ON lo_thuoc "
        "FOR EACH ROW EXECUTE FUNCTION chan_doi_ma_lo_da_co_ton();"
    )
    return cau


def xoa_trigger():
    cau = [f"DROP TRIGGER IF EXISTS ghi_nhan_chung_tu_moi ON {bang};" for bang in BANG_PHIEU]
    cau += [
        f"DROP TRIGGER IF EXISTS chan_sua_chung_tu ON {bang};"
        for bang in (*BANG_PHIEU, *BANG_CHI_TIET)
    ]
    cau += [
        "DROP TRIGGER IF EXISTS chan_doi_don_vi_thuoc ON thuoc;",
        "DROP TRIGGER IF EXISTS chan_doi_ma_lo ON lo_thuoc;",
        "DROP FUNCTION IF EXISTS ghi_nhan_chung_tu_moi();",
        "DROP FUNCTION IF EXISTS chan_sua_chung_tu_kho();",
        "DROP FUNCTION IF EXISTS chan_doi_don_vi_thuoc_da_co_lo();",
        "DROP FUNCTION IF EXISTS chan_doi_ma_lo_da_co_ton();",
    ]
    return cau


class Migration(migrations.Migration):
    dependencies = [
        ("kho", "0006_chuan_hoa_ten_csdl"),
        ("danh_muc", "0015_chuan_hoa_ten_csdl"),
    ]
    operations = [migrations.RunSQL(tao_trigger(), xoa_trigger())]
