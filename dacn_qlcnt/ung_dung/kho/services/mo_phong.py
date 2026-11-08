from datetime import timedelta
from random import Random

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.gis.geos import Point
from django.db import transaction
from django.utils import timezone

from ung_dung.chung.permissions import kiem_tra_vai_tro
from ung_dung.danh_muc.models import (
    ChiNhanh,
    DonViTinh,
    NhaCungCap,
    NhanVien,
    NhomATC,
    QuyDoiBaoGoi,
    Thuoc,
)
from ung_dung.tai_khoan.services import tao_tai_khoan_ky_thuat

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
NHAN_SU_MO_PHONG = (
    ("mp_quan_ly", "quan_ly_chi_nhanh", "Quản lý mô phỏng"),
    ("mp_nhan_vien", "nhan_vien", "Nhân viên mô phỏng"),
)


@transaction.atomic
def tao_du_lieu_mo_phong(nguoi, *, mat_khau=None):
    kiem_tra_vai_tro(nguoi, "quan_tri_chuoi")
    if ChiNhanh.objects.filter(ma_chi_nhanh__startswith="MP-CN-").exists():
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
        for ten, vai_tro, ho_ten in NHAN_SU_MO_PHONG:
            tai_khoan = tao_tai_khoan_ky_thuat(
                f"{ten}{hau_to}", mat_khau, vai_tro=vai_tro, chi_nhanh=chi_nhanh
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
    return (
        f"Đã tạo {len(CHI_NHANH_MO_PHONG)} chi nhánh và {len(cac_thuoc)} thuốc mô phỏng. "
        "Mỗi chi nhánh có một quản lý, một nhân viên và một phiếu nhập ban đầu."
    )
