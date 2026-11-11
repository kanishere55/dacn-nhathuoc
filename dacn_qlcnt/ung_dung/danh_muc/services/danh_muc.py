import re

from django.apps import apps
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Sum

from ung_dung.chung.permissions import kiem_tra_quyen, thay_toan_chuoi
from ung_dung.chung.ten_csdl import MA_NGHIEP_VU
from ung_dung.chung.van_ban import cat_khoang_trang

from ..models import ChiNhanh, KhuyenMai, QuyDoiBaoGoi, Thuoc
from ..selectors import DANH_MUC

# Đơn đã kết thúc; mọi trạng thái khác (kể cả trạng thái thêm sau này) coi là đơn chưa xong.
TRANG_THAI_DON_KET_THUC = {"hoan_thanh", "da_huy", "het_han", "giao_that_bai"}


def _so(gia_tri):
    return f"{gia_tri:,}".replace(",", ".")


def kiem_tra_ngung(doi_tuong):
    """Chặn ngừng chi nhánh/thuốc khi còn hàng hoặc còn đơn chưa xong, nêu số liệu và việc cần làm.

    Ngừng hoạt động (Q29) nghĩa là không phát sinh nghiệp vụ mới; hàng còn trong kho hoặc đơn
    đang giữ sẽ bị kẹt (không bán, không chuyển được), nên phải xử lý hết trước khi ngừng.
    """
    from ung_dung.ban_hang.models import TRANG_THAI_DON

    dang_mo = [ma for ma, _ in TRANG_THAI_DON if ma not in TRANG_THAI_DON_KET_THUC]
    TonKho = apps.get_model("kho", "TonKho")
    ChiTietDonHang = apps.get_model("ban_hang", "ChiTietDonHang")
    if isinstance(doi_tuong, ChiNhanh):
        ton = TonKho.objects.filter(chi_nhanh=doi_tuong, so_luong__gt=0)
        don = ChiTietDonHang.objects.filter(
            don_hang__chi_nhanh=doi_tuong, don_hang__trang_thai__in=dang_mo
        )
        ten, viec = (
            f"chi nhánh {doi_tuong.ten_chi_nhanh}",
            (
                "chuyển hàng sang chi nhánh khác, trả nhà cung cấp hoặc xuất hủy cho hết tồn; giao "
                "hoặc hủy xong các đơn"
            ),
        )
    else:
        ton = TonKho.objects.filter(lo_thuoc__thuoc=doi_tuong, so_luong__gt=0)
        don = ChiTietDonHang.objects.filter(thuoc=doi_tuong, don_hang__trang_thai__in=dang_mo)
        ten, viec = (
            f"thuốc {doi_tuong.ten_thuoc}",
            (
                "bán hết, trả nhà cung cấp hoặc xuất hủy phần còn trong kho; giao hoặc hủy xong các "
                "đơn có thuốc này"
            ),
        )
    tong = ton.aggregate(luong=Sum("so_luong"), so_lo=Count("lo_thuoc", distinct=True))
    so_don = don.values("don_hang").distinct().count()
    con_lai = []
    if tong["luong"]:
        con_lai.append(f"còn {_so(tong['luong'])} đơn vị hàng ở {tong['so_lo']} lô trong kho")
    if so_don:
        con_lai.append(f"còn {so_don} đơn chưa xong")
    if con_lai:
        raise ValidationError(
            {
                "dang_hoat_dong": (
                    f"Chưa thể ngừng {ten}: {' và '.join(con_lai)}. Hãy {viec}, rồi ngừng sau "
                    "(xem trang Tồn kho và Đơn hàng, lọc theo đúng mục này)."
                )
            }
        )


@transaction.atomic
def luu_danh_muc(nguoi, loai, du_lieu, doi_tuong=None):
    kiem_tra_quyen(nguoi, f"{loai}.sua")
    model = DANH_MUC[loai][0]
    if loai == "chi_nhanh" and not thay_toan_chuoi(nguoi):
        if doi_tuong is None or doi_tuong.pk != nguoi.chi_nhanh_id:
            raise PermissionDenied(
                "Chỉ sửa được chi nhánh được phân công; tạo chi nhánh cần phạm vi toàn chuỗi."
            )
    if doi_tuong:
        doi_tuong = model.objects.select_for_update().get(pk=doi_tuong.pk)
    else:
        doi_tuong = model()
    don_vi_cu = doi_tuong.don_vi_tinh_id if isinstance(doi_tuong, Thuoc) else None
    dang_hoat_dong_cu = bool(doi_tuong.pk) and getattr(doi_tuong, "dang_hoat_dong", False)
    for ten, gia_tri in du_lieu.items():
        if ten not in {cot.name for cot in model._meta.fields if not cot.primary_key}:
            continue
        if isinstance(gia_tri, str):
            gia_tri = cat_khoang_trang(gia_tri)
            if ten.startswith("ma_") and not re.fullmatch(MA_NGHIEP_VU, gia_tri):
                raise ValidationError("Mã gồm tối đa 32 chữ hoa, số, gạch ngang hoặc gạch dưới.")
        setattr(doi_tuong, ten, gia_tri)
    if don_vi_cu and doi_tuong.don_vi_tinh_id != don_vi_cu:
        raise ValidationError(
            {
                "don_vi_tinh": (
                    "Đơn vị cơ sở của thuốc đã tạo được giữ cố định để bảo toàn số liệu kho."
                )
            }
        )
    if isinstance(doi_tuong, QuyDoiBaoGoi) and doi_tuong.pk:
        cu = model.objects.get(pk=doi_tuong.pk)
        if cu.thuoc_id != doi_tuong.thuoc_id or cu.he_so != doi_tuong.he_so:
            raise ValidationError("Không đổi thuốc/hệ số của quy đổi đã tạo; hãy tạo bao gói mới.")
    if loai == "nhan_vien" and doi_tuong.tai_khoan.vai_tro not in {
        "nhan_vien",
        "quan_ly_chi_nhanh",
    }:
        raise ValidationError(
            "Hồ sơ nhân viên phải liên kết tài khoản nhân viên hoặc quản lý chi nhánh."
        )
    if loai == "nhan_vien" and not thay_toan_chuoi(nguoi):
        if doi_tuong.tai_khoan.chi_nhanh_id != nguoi.chi_nhanh_id:
            raise ValidationError("Chỉ quản lý hồ sơ nhân viên thuộc chi nhánh của bạn.")
    if (
        isinstance(doi_tuong, ChiNhanh | Thuoc)
        and dang_hoat_dong_cu
        and not doi_tuong.dang_hoat_dong
    ):
        kiem_tra_ngung(doi_tuong)
    if isinstance(doi_tuong, KhuyenMai):
        kiem_khuyen_mai_trung(doi_tuong)
    doi_tuong.full_clean()
    doi_tuong.save()
    return doi_tuong


def kiem_khuyen_mai_trung(khuyen_mai):
    """Một thuốc chỉ có một đợt giảm giá đang hoạt động trong cùng một ngày.

    Khóa dòng thuốc để hai quản trị lưu cùng lúc không tạo được hai đợt trùng.
    """
    thuoc = Thuoc.objects.select_for_update().get(pk=khuyen_mai.thuoc_id)
    if thuoc.la_thuoc_ke_don:
        raise ValidationError(
            "Không tạo khuyến mãi cho thuốc kê đơn: Luật Dược không cho quảng cáo thuốc kê đơn "
            "tới công chúng."
        )
    if not khuyen_mai.dang_hoat_dong:
        return
    trung = (
        KhuyenMai.objects.filter(
            thuoc_id=khuyen_mai.thuoc_id,
            dang_hoat_dong=True,
            ngay_bat_dau__lte=khuyen_mai.ngay_ket_thuc,
            ngay_ket_thuc__gte=khuyen_mai.ngay_bat_dau,
        )
        .exclude(pk=khuyen_mai.pk)
        .first()
    )
    if trung:
        raise ValidationError(
            f"Thuốc đã có đợt {trung.ma_khuyen_mai} từ {trung.ngay_bat_dau:%d/%m/%Y} "
            f"đến {trung.ngay_ket_thuc:%d/%m/%Y}. Hãy dừng đợt đó hoặc chọn ngày khác."
        )
