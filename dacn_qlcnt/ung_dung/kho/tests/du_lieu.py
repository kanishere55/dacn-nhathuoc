from datetime import timedelta
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.utils import timezone

from ung_dung.danh_muc.models import ChiNhanh, DonViTinh, NhaCungCap, NhomATC, Thuoc
from ung_dung.kho.models import LoThuoc, TonKho


def tao_du_lieu():
    nguoi = get_user_model()
    cn = ChiNhanh.objects.create(
        ma_chi_nhanh="CN1",
        ten_chi_nhanh="Chi nhánh một",
        dia_chi="TP.HCM",
        vi_tri=Point(106.7, 10.77, srid=4326),
    )
    cn2 = ChiNhanh.objects.create(
        ma_chi_nhanh="CN2",
        ten_chi_nhanh="Chi nhánh hai",
        dia_chi="TP.HCM",
        vi_tri=Point(106.71, 10.78, srid=4326),
    )
    dvt = DonViTinh.objects.create(ma_don_vi_tinh="VIEN", ten_don_vi_tinh="Viên")
    nhom = NhomATC.objects.create(ma_nhom_atc="N02BE", ten_nhom_atc="Nhóm thử nghiệm")
    ncc = NhaCungCap.objects.create(ma_nha_cung_cap="NCC1", ten_nha_cung_cap="Đối tác thử nghiệm")
    thuoc = Thuoc.objects.create(
        ma_thuoc="THUOC1",
        ten_thuoc="Thuốc thử nghiệm",
        nhom_atc=nhom,
        don_vi_tinh=dvt,
        ham_luong="500 mg",
        dang_bao_che="Viên nén",
        nha_san_xuat="Nhà sản xuất mô phỏng",
        gia_ban=2000,
    )
    admin = nguoi.objects.create_superuser("quan_tri_thu", password="Mat-khau-thu-2026!")
    nv = nguoi.objects.create_user(
        "nhan_vien_thu", password="Mat-khau-thu-2026!", vai_tro="nhan_vien", chi_nhanh=cn
    )
    ql = nguoi.objects.create_user(
        "quan_ly_thu", password="Mat-khau-thu-2026!", vai_tro="quan_ly_chi_nhanh", chi_nhanh=cn
    )
    khach = nguoi.objects.create_user("khach_thu", password="Mat-khau-thu-2026!")
    khac = nguoi.objects.create_user("khach_khac", password="Mat-khau-thu-2026!")
    return SimpleNamespace(
        cn=cn,
        cn2=cn2,
        thuoc=thuoc,
        dvt=dvt,
        nhom=nhom,
        ncc=ncc,
        admin=admin,
        nv=nv,
        ql=ql,
        khach=khach,
        khac=khac,
    )


def tao_ton(du_lieu, ma="LO1", ngay=10, luong=10, duoc_ban=True, chi_nhanh=None):
    lo = LoThuoc.objects.create(
        thuoc=du_lieu.thuoc,
        ma_lo_thuoc=ma,
        ngay_het_han=timezone.localdate() + timedelta(days=ngay),
        duoc_phep_ban=duoc_ban,
    )
    return TonKho.objects.create(chi_nhanh=chi_nhanh or du_lieu.cn, lo_thuoc=lo, so_luong=luong)
