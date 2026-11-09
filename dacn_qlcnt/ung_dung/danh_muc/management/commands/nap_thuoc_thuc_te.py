"""Thay dữ liệu thuốc, chi nhánh mô phỏng bằng danh mục thực tế và ảnh minh họa đúng sản phẩm.

Chạy lại được: chỉ thêm thứ còn thiếu. Ảnh minh họa vẽ tại chỗ bằng Pillow rồi lưu bytea.
    python manage.py nap_thuoc_thuc_te [--ve-lai-anh]
"""

from datetime import timedelta
from random import Random

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import ProtectedError
from django.utils import timezone

from ung_dung.kho.models import TonKho
from ung_dung.kho.services.phieu_nhap import nhap_hang
from ung_dung.tai_khoan.models import TaiKhoan

from ...anh_minh_hoa import ve_anh_san_pham
from ...du_lieu_thuc_te import CHI_NHANH, DANH_MUC, DON_VI, KHUYEN_MAI, NHOM_ATC_MOI, THUOC
from ...models import (
    AnhThuoc,
    ChiNhanh,
    DanhMucSanPham,
    DonViTinh,
    KhuyenMai,
    NhaCungCap,
    NhomATC,
    QuyDoiBaoGoi,
    Thuoc,
)


class Command(BaseCommand):
    help = "Nạp danh mục thuốc thực tế, ảnh minh họa và tồn kho chạy thử."

    def add_arguments(self, parser):
        parser.add_argument("--ve-lai-anh", action="store_true", help="Vẽ lại ảnh cho mọi thuốc.")

    def handle(self, *args, **options):
        nha_cung_cap = NhaCungCap.objects.filter(dang_hoat_dong=True).order_by("pk").first()
        if nha_cung_cap is None:
            raise CommandError(
                "Cần ít nhất một nhà cung cấp đang hoạt động (chạy tạo dữ liệu mô phỏng trước)."
            )
        with transaction.atomic():
            self._chi_nhanh()
            cac_danh_muc = self._danh_muc()
            cac_thuoc = self._thuoc(cac_danh_muc, options["ve_lai_anh"])
            self._khuyen_mai()
        self._ton_kho(cac_thuoc, nha_cung_cap)
        self.stdout.write(self.style.SUCCESS(f"Đã nạp {len(cac_thuoc)} thuốc."))

    def _chi_nhanh(self):
        for ma_cu, (ma, ten, dia_chi) in CHI_NHANH.items():
            n = ChiNhanh.objects.filter(ma_chi_nhanh=ma_cu).update(
                ma_chi_nhanh=ma, ten_chi_nhanh=ten, dia_chi=dia_chi
            )
            if n:
                self.stdout.write(f"Đổi chi nhánh {ma_cu} thành {ten}")

    def _danh_muc(self):
        ket_qua = {}
        for ma, ten, mo_ta, bieu_tuong, thu_tu in DANH_MUC:
            ket_qua[ma], _ = DanhMucSanPham.objects.update_or_create(
                ma_danh_muc_san_pham=ma,
                defaults={
                    "ten_danh_muc_san_pham": ten,
                    "mo_ta": mo_ta,
                    "bieu_tuong": bieu_tuong,
                    "thu_tu": thu_tu,
                },
            )
        for ma, ten in NHOM_ATC_MOI.items():
            NhomATC.objects.get_or_create(ma_nhom_atc=ma, defaults={"ten_nhom_atc": ten})
        for ma, ten in DON_VI.items():
            DonViTinh.objects.get_or_create(ma_don_vi_tinh=ma, defaults={"ten_don_vi_tinh": ten})
        return ket_qua

    def _thuoc(self, cac_danh_muc, ve_lai_anh):
        cac_thuoc = []
        for sp in THUOC:
            thuoc = Thuoc.objects.filter(ma_thuoc=sp["ma"]).first()
            doi_tu_mo_phong = False
            if thuoc is None and sp["ma_cu"]:
                thuoc = Thuoc.objects.filter(ma_thuoc=sp["ma_cu"]).first()
                doi_tu_mo_phong = thuoc is not None
            thuoc = thuoc or Thuoc()
            thuoc.ma_thuoc = sp["ma"]
            thuoc.ten_thuoc = sp["ten"]
            thuoc.nhom_atc = NhomATC.objects.get(ma_nhom_atc=sp["atc"])
            thuoc.don_vi_tinh = DonViTinh.objects.get(ma_don_vi_tinh=sp["don_vi"])
            thuoc.danh_muc_san_pham = cac_danh_muc[sp["danh_muc"]]
            thuoc.la_thuoc_ke_don = sp["ke_don"]
            thuoc.ham_luong = sp["ham_luong"]
            thuoc.dang_bao_che = sp["dang"]
            thuoc.nha_san_xuat = sp["nsx"]
            thuoc.gia_ban = sp["gia"]
            thuoc.nguong_canh_bao = 5 if sp["don_vi"] in ("BINH", "CHAI") else 20
            thuoc.hoat_chat = sp["hoat_chat"]
            thuoc.quy_cach_dong_goi = sp["quy_cach"]
            thuoc.nuoc_san_xuat = sp["nuoc"]
            thuoc.mo_ta_ngan = sp["mo_ta"]
            for cot in (
                "cong_dung",
                "cach_dung",
                "chong_chi_dinh",
                "tac_dung_phu",
                "luu_y",
                "bao_quan",
            ):
                setattr(thuoc, cot, sp[cot])
            thuoc.full_clean()
            thuoc.save()
            if doi_tu_mo_phong:
                self.stdout.write(f"Đổi {sp['ma_cu']} thành {sp['ten']}")
                for cu in QuyDoiBaoGoi.objects.filter(thuoc=thuoc):
                    try:
                        cu.delete()
                    except ProtectedError:
                        pass
            for ten_bao_goi, he_so in sp["bao_goi"]:
                QuyDoiBaoGoi.objects.get_or_create(
                    thuoc=thuoc, ten_quy_doi_bao_goi=ten_bao_goi, defaults={"he_so": he_so}
                )
            if ve_lai_anh or doi_tu_mo_phong or not AnhThuoc.objects.filter(thuoc=thuoc).exists():
                AnhThuoc.objects.filter(thuoc=thuoc).delete()
                anh = AnhThuoc(thuoc=thuoc, thu_tu=0)
                anh.gan_du_lieu(
                    SimpleUploadedFile(
                        f"{thuoc.ma_thuoc}.png",
                        ve_anh_san_pham(
                            {
                                "ten_hien_thi": sp["ten"],
                                "hoat_chat": sp["hoat_chat"],
                                "dang_bao_che": sp["dang"],
                                "quy_cach": sp["quy_cach"],
                                "nha_san_xuat": sp["nsx"],
                                "ke_don": sp["ke_don"],
                                "mau": sp["mau"],
                                "hinh": sp["hinh"],
                            }
                        ),
                        "image/png",
                    )
                )
                anh.save()
            cac_thuoc.append(thuoc)
        return cac_thuoc

    def _khuyen_mai(self):
        KhuyenMai.objects.filter(thuoc__la_thuoc_ke_don=True, dang_hoat_dong=True).update(
            dang_hoat_dong=False
        )
        KhuyenMai.objects.filter(ten_khuyen_mai__icontains="mô phỏng").update(
            ten_khuyen_mai="Ưu đãi tháng này"
        )
        hom_nay = timezone.localdate()
        for so, (ma_thuoc, phan_tram, ten) in enumerate(KHUYEN_MAI, start=1):
            thuoc = Thuoc.objects.get(ma_thuoc=ma_thuoc)
            if KhuyenMai.objects.filter(
                thuoc=thuoc, dang_hoat_dong=True, ngay_ket_thuc__gte=hom_nay
            ).exists():
                continue
            KhuyenMai.objects.get_or_create(
                ma_khuyen_mai=f"TA-KM-{hom_nay:%y%m}-{so:02d}",
                defaults={
                    "ten_khuyen_mai": ten,
                    "thuoc": thuoc,
                    "phan_tram_giam": phan_tram,
                    "ngay_bat_dau": hom_nay,
                    "ngay_ket_thuc": hom_nay + timedelta(days=30),
                },
            )

    def _ton_kho(self, cac_thuoc, nha_cung_cap):
        ngau_nhien = Random(2026)
        hom_nay = timezone.localdate()
        for chi_nhanh in ChiNhanh.objects.filter(dang_hoat_dong=True).order_by("pk"):
            quan_ly = TaiKhoan.objects.filter(
                vai_tro="quan_ly_chi_nhanh", chi_nhanh=chi_nhanh, dang_hoat_dong=True
            ).first()
            if quan_ly is None:
                continue
            cac_dong = []
            for thuoc in cac_thuoc:
                if TonKho.objects.filter(chi_nhanh=chi_nhanh, lo_thuoc__thuoc=thuoc).exists():
                    continue
                lon = thuoc.don_vi_tinh.ma_don_vi_tinh not in ("BINH", "CHAI")
                for so_lo, thang in ((1, 7), (2, 19)):
                    cac_dong.append(
                        {
                            "thuoc": thuoc,
                            "ma_lo_thuoc": f"{thuoc.ma_thuoc[3:]}-{chi_nhanh.pk}{so_lo}{hom_nay:%y%m}",
                            "ngay_het_han": hom_nay + timedelta(days=30 * thang),
                            "so_luong": ngau_nhien.randint(40, 160)
                            if lon
                            else ngau_nhien.randint(8, 24),
                            "don_gia": int(thuoc.gia_ban) * 72 // 100,
                        }
                    )
            if cac_dong:
                nhap_hang(quan_ly, chi_nhanh, nha_cung_cap, cac_dong, "Nhập hàng đầu kỳ")
                self.stdout.write(f"Nhập {len(cac_dong)} lô cho {chi_nhanh.ten_chi_nhanh}")
