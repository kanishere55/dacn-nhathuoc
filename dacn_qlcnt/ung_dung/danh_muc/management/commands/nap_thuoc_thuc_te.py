"""Thay dữ liệu thuốc, chi nhánh mô phỏng bằng danh mục thực tế và ảnh minh họa đúng sản phẩm.

Chạy lại được: chỉ thêm thứ còn thiếu, giữ nguyên thuốc và danh mục đã sửa trong khu quản lý.
Không tạo ảnh: ảnh thật có giấy phép mở nạp riêng bằng `manage.py nap_anh_that`.
Không sửa lịch sử kho (Q02, Q06): thuốc đã có lô thì không đổi đơn vị cơ sở (thuốc mô phỏng khác
đơn vị được cho ngừng và tạo thuốc thật mới), lô đã nằm trên chứng từ thì không đổi mã lô.
    python manage.py nap_thuoc_thuc_te [--ghi-de]
"""

from datetime import timedelta
from random import Random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import ProtectedError
from django.utils import timezone

from ung_dung.kho.models import (
    ChiTietPhieuDieuChuyen,
    ChiTietPhieuKiemKe,
    ChiTietPhieuNhap,
    ChiTietPhieuTraNhaCungCap,
    ChiTietPhieuXuatHuy,
    LoThuoc,
    TonKho,
)
from ung_dung.kho.services.phieu_nhap import nhap_hang
from ung_dung.tai_khoan.models import TaiKhoan

from ...du_lieu_thuc_te import (
    CHI_NHANH,
    DANH_MUC,
    DON_VI,
    KHUYEN_MAI,
    NHOM_ATC_MOI,
    THUOC,
    ghep_noi_dung,
)
from ...models import (
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
    help = "Nạp danh mục thuốc thực tế và tồn kho chạy thử (ảnh nạp bằng nap_anh_that)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ghi-de",
            action="store_true",
            help="Ghi lại thông tin chuẩn cho thuốc và danh mục đã có, kể cả phần đã sửa.",
        )

    def handle(self, *args, **options):
        nha_cung_cap = NhaCungCap.objects.filter(dang_hoat_dong=True).order_by("pk").first()
        if nha_cung_cap is None:
            raise CommandError(
                "Cần ít nhất một nhà cung cấp đang hoạt động (chạy tạo dữ liệu mô phỏng trước)."
            )
        with transaction.atomic():
            self._chi_nhanh()
            cac_danh_muc = self._danh_muc(options["ghi_de"])
            cac_thuoc = self._thuoc(cac_danh_muc, options["ghi_de"])
            self._khuyen_mai()
            self._ma_lo()
        self._ton_kho(cac_thuoc, nha_cung_cap)
        self.stdout.write(self.style.SUCCESS(f"Đã nạp {len(cac_thuoc)} thuốc."))

    def _chi_nhanh(self):
        for ma_cu, (ma, ten, dia_chi) in CHI_NHANH.items():
            n = ChiNhanh.objects.filter(ma_chi_nhanh=ma_cu).update(
                ma_chi_nhanh=ma, ten_chi_nhanh=ten, dia_chi=dia_chi
            )
            if n:
                self.stdout.write(f"Đổi chi nhánh {ma_cu} thành {ten}")

    def _danh_muc(self, ghi_de):
        ket_qua = {}
        for ma, ten, mo_ta, bieu_tuong, thu_tu in DANH_MUC:
            gia_tri = {
                "ten_danh_muc_san_pham": ten,
                "mo_ta": mo_ta,
                "bieu_tuong": bieu_tuong,
                "thu_tu": thu_tu,
            }
            if ghi_de:
                ket_qua[ma], _ = DanhMucSanPham.objects.update_or_create(
                    ma_danh_muc_san_pham=ma, defaults=gia_tri
                )
            else:
                ket_qua[ma], _ = DanhMucSanPham.objects.get_or_create(
                    ma_danh_muc_san_pham=ma, defaults=gia_tri
                )
        for ma, ten in NHOM_ATC_MOI.items():
            NhomATC.objects.get_or_create(ma_nhom_atc=ma, defaults={"ten_nhom_atc": ten})
        for ma, ten in DON_VI.items():
            DonViTinh.objects.get_or_create(ma_don_vi_tinh=ma, defaults={"ten_don_vi_tinh": ten})
        return ket_qua

    def _thuoc(self, cac_danh_muc, ghi_de):
        cac_thuoc = []
        for sp in THUOC:
            thuoc = Thuoc.objects.filter(ma_thuoc=sp["ma"]).first()
            if thuoc is not None and not ghi_de:
                cac_thuoc.append(thuoc)
                continue
            doi_tu_mo_phong = False
            don_vi = DonViTinh.objects.get(ma_don_vi_tinh=sp["don_vi"])
            if thuoc is None and sp["ma_cu"]:
                thuoc = Thuoc.objects.filter(ma_thuoc=sp["ma_cu"]).first()
                doi_tu_mo_phong = thuoc is not None
                if doi_tu_mo_phong and self._khong_doi_duoc_don_vi(thuoc, don_vi):
                    self._ngung_thuoc_mo_phong(thuoc, sp)
                    thuoc, doi_tu_mo_phong = None, False
            if thuoc is not None and self._khong_doi_duoc_don_vi(thuoc, don_vi):
                # --ghi-de trên thuốc đã có lô: giữ đơn vị cũ, số lượng cũ vẫn đúng nghĩa.
                self.stdout.write(
                    self.style.WARNING(
                        f"Giữ đơn vị {thuoc.don_vi_tinh} của {thuoc.ma_thuoc}: thuốc đã có lô trong kho."
                    )
                )
                don_vi = thuoc.don_vi_tinh
            thuoc = thuoc or Thuoc()
            thuoc.ma_thuoc = sp["ma"]
            thuoc.ten_thuoc = sp["ten"]
            thuoc.nhom_atc = NhomATC.objects.get(ma_nhom_atc=sp["atc"])
            thuoc.don_vi_tinh = don_vi
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
            thuoc.noi_dung_chi_tiet = ghep_noi_dung(sp)
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
            cac_thuoc.append(thuoc)
        return cac_thuoc

    @staticmethod
    def _khong_doi_duoc_don_vi(thuoc, don_vi):
        return thuoc.don_vi_tinh_id != don_vi.pk and LoThuoc.objects.filter(thuoc=thuoc).exists()

    def _ngung_thuoc_mo_phong(self, thuoc, sp):
        """Thuốc mô phỏng đã có tồn theo đơn vị khác: giữ nguyên để chứng từ cũ đúng nghĩa,
        đổi mã sang MP-NGUNG-... cho ngừng kinh doanh; thuốc thật được tạo mới."""
        thuoc.ma_thuoc = "MP-NGUNG-" + sp["ma_cu"].removeprefix("MP-T-")
        thuoc.dang_hoat_dong = False
        thuoc.full_clean()
        thuoc.save(update_fields=["ma_thuoc", "dang_hoat_dong"])
        self.stdout.write(
            f"Giữ {thuoc.ten_thuoc} (đơn vị {thuoc.don_vi_tinh}) thành {thuoc.ma_thuoc}, ngừng kinh "
            f"doanh; tạo mới {sp['ten']} đơn vị {sp['don_vi']}."
        )

    def _ma_lo(self):
        """Lô của dữ liệu mô phỏng mang mã MP-...: đổi sang dạng số lô in trên bao bì.

        Chỉ đổi lô chưa có trong kho và chưa nằm trên chứng từ nào; mã lô đã in trên phiếu
        nhập, phiếu bán... được giữ nguyên (CSDL cũng chặn bằng trigger chan_doi_ma_lo).
        """
        da_dung = set()
        for model in (
            ChiTietPhieuNhap,
            ChiTietPhieuDieuChuyen,
            ChiTietPhieuKiemKe,
            ChiTietPhieuXuatHuy,
            ChiTietPhieuTraNhaCungCap,
        ):
            da_dung.update(model.objects.values_list("lo_thuoc_id", flat=True))
        da_dung.update(TonKho.objects.values_list("lo_thuoc_id", flat=True))
        for lo in (
            LoThuoc.objects.filter(ma_lo_thuoc__startswith="MP-")
            .exclude(pk__in=da_dung)
            .order_by("pk")
        ):
            nam_sx = lo.ngay_het_han.replace(year=lo.ngay_het_han.year - 2)
            lo.ma_lo_thuoc = f"{nam_sx:%y%m}{lo.pk % 1000:03d}"
            lo.save(update_fields=["ma_lo_thuoc"])

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
                            "ma_lo_thuoc": f"{hom_nay:%y%m}{chi_nhanh.pk}{so_lo}{thuoc.pk % 100:02d}",
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
