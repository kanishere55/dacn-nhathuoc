from datetime import timedelta
from random import Random

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.gis.geos import Point
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ung_dung.chung.permissions import kiem_tra_vai_tro
from ung_dung.danh_muc.models import (
    ChiNhanh,
    DanhMucSanPham,
    DonViTinh,
    KhuyenMai,
    NhaCungCap,
    NhanVien,
    NhomATC,
    QuyDoiBaoGoi,
    Thuoc,
)
from ung_dung.tai_khoan.services.tai_khoan import tao_tai_khoan_ky_thuat

from .phieu_nhap import nhap_hang

CHI_NHANH_MO_PHONG = (
    ("MP-CN-01", "Nhà thuốc mô phỏng Bến Thành", "Khu vực Bến Thành, TP.HCM", 106.6981, 10.7724),
    ("MP-CN-02", "Nhà thuốc mô phỏng Tân Định", "Khu vực Tân Định, TP.HCM", 106.6902, 10.7896),
    ("MP-CN-03", "Nhà thuốc mô phỏng Bình Thạnh", "Khu vực Bình Thạnh, TP.HCM", 106.7132, 10.8031),
)
NHOM_MO_PHONG = (
    ("M01AB", "Kháng viêm nhóm dẫn xuất acid acetic", "Chế phẩm mô phỏng 01"),
    ("M01AE", "Kháng viêm nhóm dẫn xuất acid propionic", "Chế phẩm mô phỏng 02"),
    ("N02BA", "Giảm đau nhóm salicylat", "Chế phẩm mô phỏng 03"),
    ("N02BE", "Giảm đau nhóm anilid", "Chế phẩm mô phỏng 04"),
    ("N05B", "Nhóm giải lo âu", "Chế phẩm mô phỏng 05"),
    ("N05C", "Nhóm an thần, gây ngủ", "Chế phẩm mô phỏng 06"),
    ("R03", "Nhóm dùng cho bệnh tắc nghẽn đường thở", "Chế phẩm mô phỏng 07"),
    ("R06", "Nhóm kháng histamin toàn thân", "Chế phẩm mô phỏng 08"),
)
DANH_MUC_MO_PHONG = (
    ("GIAM-DAU", "Giảm đau, hạ sốt", "Thuốc giảm đau, hạ sốt thông dụng.", "thermometer", 1),
    ("KHANG-VIEM", "Kháng viêm", "Thuốc kháng viêm không steroid.", "flame", 2),
    ("THAN-KINH", "Thần kinh, giấc ngủ", "Thuốc an thần và giải lo âu, bán theo đơn.", "brain", 3),
    ("HO-HAP", "Hô hấp, dị ứng", "Thuốc dùng cho đường thở và dị ứng.", "wind", 4),
)
# Mã thuốc -> (mã danh mục, là thuốc kê đơn). Nhóm N05 là thuốc kê đơn ngoài thực tế.
XEP_THUOC_MO_PHONG = {
    "MP-T-01": ("KHANG-VIEM", False),
    "MP-T-02": ("KHANG-VIEM", False),
    "MP-T-03": ("GIAM-DAU", False),
    "MP-T-04": ("GIAM-DAU", False),
    "MP-T-05": ("THAN-KINH", True),
    "MP-T-06": ("THAN-KINH", True),
    "MP-T-07": ("HO-HAP", False),
    "MP-T-08": ("HO-HAP", False),
}
NHAN_SU_MO_PHONG = (
    ("mp_quan_ly", "quan_ly_chi_nhanh", "Quản lý mô phỏng"),
    ("mp_nhan_vien", "nhan_vien", "Nhân viên mô phỏng"),
)
# Họ tên hiển thị của quản lý và nhân viên từng chi nhánh, theo thứ tự NHAN_SU_MO_PHONG.
HO_TEN_NHAN_SU = (
    ("Nguyễn Thị Lan", "Lê Văn Hùng"),
    ("Phạm Thu Hà", "Võ Minh Tuấn"),
    ("Đặng Ngọc Mai", "Bùi Quốc Bảo"),
)


@transaction.atomic
def tao_du_lieu_mo_phong(nguoi, *, mat_khau=None):
    kiem_tra_vai_tro(nguoi, "quan_tri_chuoi")
    # Sau lệnh nap_thuoc_thuc_te, chi nhánh mô phỏng đổi mã sang CN-...; vẫn coi là đã tạo.
    if ChiNhanh.objects.filter(
        Q(ma_chi_nhanh__startswith="MP-CN-") | Q(ma_chi_nhanh="CN-BEN-THANH")
    ).exists():
        raise ValueError("Đã có chi nhánh mô phỏng. Lệnh không ghi lặp hoặc ghi đè.")
    cac_hau_to = ["" if so == 1 else f"_{so:02d}" for so in range(1, len(CHI_NHANH_MO_PHONG) + 1)]
    cac_ten_dang_nhap = [
        f"{ten}{hau_to}" for hau_to in cac_hau_to for ten, _, _ in NHAN_SU_MO_PHONG
    ]
    if mat_khau is not None:
        validate_password(mat_khau)
        cac_ten_dang_nhap.append("mp_khach")
    if get_user_model().objects.filter(ten_dang_nhap__in=cac_ten_dang_nhap).exists():
        raise ValueError("Tên tài khoản mô phỏng đã được sử dụng.")

    # Mã duy nhất giữ hai lượt chạy đồng thời khỏi cùng sinh dữ liệu.
    nha_cung_cap, da_tao = NhaCungCap.objects.get_or_create(
        ma_nha_cung_cap="MP-NCC-01", defaults={"ten_nha_cung_cap": "Nhà cung cấp mô phỏng"}
    )
    if not da_tao:
        raise ValueError("Đã có nhà cung cấp mô phỏng. Lệnh không ghi lặp hoặc ghi đè.")
    ngau_nhien = Random(1250080021)
    don_vi, _ = DonViTinh.objects.get_or_create(
        ma_don_vi_tinh="VIEN", defaults={"ten_don_vi_tinh": "Viên"}
    )
    cac_thuoc = []
    for so, (ma_atc, ten_nhom, ten_thuoc) in enumerate(NHOM_MO_PHONG, start=1):
        nhom, _ = NhomATC.objects.get_or_create(
            ma_nhom_atc=ma_atc, defaults={"ten_nhom_atc": ten_nhom}
        )
        thuoc = Thuoc.objects.create(
            ma_thuoc=f"MP-T-{so:02d}",
            ten_thuoc=ten_thuoc,
            nhom_atc=nhom,
            don_vi_tinh=don_vi,
            ham_luong="Mô phỏng",
            dang_bao_che="Viên",
            nha_san_xuat="Nhà sản xuất mô phỏng",
            gia_ban=ngau_nhien.randrange(2, 16) * 1000,
            nguong_canh_bao=15,
        )
        QuyDoiBaoGoi.objects.create(thuoc=thuoc, ten_quy_doi_bao_goi="Hộp 10 viên", he_so=10)
        cac_thuoc.append(thuoc)
    hom_nay = timezone.localdate()
    for so, (mau, hau_to) in enumerate(zip(CHI_NHANH_MO_PHONG, cac_hau_to, strict=True), start=1):
        ma, ten, dia_chi, kinh_do, vi_do = mau
        chi_nhanh = ChiNhanh.objects.create(
            ma_chi_nhanh=ma,
            ten_chi_nhanh=ten,
            dia_chi=dia_chi,
            vi_tri=Point(kinh_do, vi_do, srid=4326),
        )
        cac_tai_khoan = {}
        for (ten, vai_tro, _), ho_ten in zip(NHAN_SU_MO_PHONG, HO_TEN_NHAN_SU[so - 1], strict=True):
            tai_khoan = tao_tai_khoan_ky_thuat(
                f"{ten}{hau_to}", mat_khau, vai_tro=vai_tro, chi_nhanh=chi_nhanh, ho_ten=ho_ten
            )
            NhanVien.objects.create(
                ma_nhan_vien=f"MP-{vai_tro.upper()}{hau_to}",
                ten_nhan_vien=ho_ten,
                tai_khoan=tai_khoan,
            )
            cac_tai_khoan[vai_tro] = tai_khoan
        cac_dong = [
            {
                "thuoc": thuoc,
                "ma_lo_thuoc": f"MP-{so:02d}-{thuoc.ma_thuoc}-{so_lo}",
                "ngay_het_han": hom_nay + timedelta(days=han),
                "so_luong": ngau_nhien.randint(12, 80),
                "don_gia": thuoc.gia_ban // 2,
            }
            for thuoc in cac_thuoc
            for so_lo, han in ((1, 25), (2, 180))
        ]
        nhap_hang(
            cac_tai_khoan["quan_ly_chi_nhanh"],
            chi_nhanh,
            nha_cung_cap,
            cac_dong,
            "Nhập tồn ban đầu mô phỏng",
        )
    if mat_khau is not None:
        tao_tai_khoan_ky_thuat("mp_khach", mat_khau)
    bo_sung_noi_dung_mo_phong(nguoi)
    return (
        f"Đã tạo {len(CHI_NHANH_MO_PHONG)} chi nhánh và {len(cac_thuoc)} thuốc mô phỏng. "
        "Mỗi chi nhánh có một quản lý, một nhân viên và một phiếu nhập ban đầu."
    )


@transaction.atomic
def bo_sung_noi_dung_mo_phong(nguoi):
    """Thêm danh mục, nội dung hiển thị, giờ mở cửa và khuyến mãi cho dữ liệu mô phỏng.

    Chạy lại được: chỉ điền chỗ còn trống, không ghi đè nội dung quản trị đã sửa.
    """
    kiem_tra_vai_tro(nguoi, "quan_tri_chuoi")
    cac_danh_muc = {}
    for ma, ten, mo_ta, bieu_tuong, thu_tu in DANH_MUC_MO_PHONG:
        cac_danh_muc[ma], _ = DanhMucSanPham.objects.get_or_create(
            ma_danh_muc_san_pham=ma,
            defaults={
                "ten_danh_muc_san_pham": ten,
                "mo_ta": mo_ta,
                "bieu_tuong": bieu_tuong,
                "thu_tu": thu_tu,
            },
        )
    for thuoc in Thuoc.objects.filter(ma_thuoc__in=XEP_THUOC_MO_PHONG).select_for_update():
        ma_danh_muc, ke_don = XEP_THUOC_MO_PHONG[thuoc.ma_thuoc]
        if thuoc.danh_muc_san_pham_id is None:
            thuoc.danh_muc_san_pham = cac_danh_muc[ma_danh_muc]
            thuoc.la_thuoc_ke_don = ke_don
        thuoc.quy_cach_dong_goi = thuoc.quy_cach_dong_goi or "Hộp 10 vỉ x 10 viên"
        thuoc.nuoc_san_xuat = thuoc.nuoc_san_xuat or "Việt Nam"
        thuoc.mo_ta_ngan = thuoc.mo_ta_ngan or "Sản phẩm mô phỏng phục vụ chạy thử hệ thống."
        thuoc.noi_dung_chi_tiet = thuoc.noi_dung_chi_tiet or (
            "<h3>Công dụng</h3><p>Nội dung mô phỏng. Khi vận hành thật, quản trị nhập công dụng "
            "theo tờ hướng dẫn sử dụng đã được Bộ Y tế phê duyệt.</p>"
            "<h3>Liều dùng và cách dùng</h3><p>Dùng theo chỉ dẫn của bác sĩ hoặc dược sĩ.</p>"
            "<h3>Bảo quản</h3><p>Nơi khô, dưới 30°C, tránh ánh sáng.</p>"
        )
        thuoc.save()
    for so, chi_nhanh in enumerate(
        ChiNhanh.objects.filter(ma_chi_nhanh__startswith="MP-CN-").order_by("ma_chi_nhanh"),
        start=1,
    ):
        if not chi_nhanh.so_dien_thoai:
            chi_nhanh.so_dien_thoai = f"028390000{so:02d}"
            chi_nhanh.save(update_fields=["so_dien_thoai"])
    hom_nay = timezone.localdate()
    for ma_thuoc, phan_tram in (("MP-T-03", 10), ("MP-T-07", 15)):
        thuoc = Thuoc.objects.filter(ma_thuoc=ma_thuoc).first()
        if thuoc:
            KhuyenMai.objects.get_or_create(
                ma_khuyen_mai=f"MP-KM-{ma_thuoc[-2:]}",
                defaults={
                    "ten_khuyen_mai": "Ưu đãi mô phỏng tháng này",
                    "thuoc": thuoc,
                    "phan_tram_giam": phan_tram,
                    "ngay_bat_dau": hom_nay,
                    "ngay_ket_thuc": hom_nay + timedelta(days=30),
                },
            )
