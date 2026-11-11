import re

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ung_dung.chung.ten_csdl import MA_NGHIEP_VU
from ung_dung.chung.van_ban import cat_khoang_trang

from ..loi_dong import LoiDongPhieu
from ..models import ChiTietPhieuNhap, LichSuDieuKienLo, LoThuoc, PhieuNhap, TonKho
from ..quy_tac import chuan_hoa_ma_lo, loi_han_dung
from .chong_trung import chuan_hoa_khoa, phieu_da_luu
from .giao_dich import doi_ve_co_so, khoa_chi_nhanh, ma_chung_tu, thay_doi_ton


def _ly_do_khoa(lo):
    lan_cuoi = (
        LichSuDieuKienLo.objects.filter(lo_thuoc=lo, duoc_phep_ban=False)
        .order_by("-thoi_diem_tao", "-pk")
        .first()
    )
    return f" (lý do: {lan_cuoi.ly_do})" if lan_cuoi and lan_cuoi.ly_do else ""


def _kiem_dong(i, dong, hom_nay, han_trong_phieu):
    """Trả (ô sai, câu báo) nếu dòng không nhập được, hoặc (None, dữ liệu đã chuẩn hóa)."""
    thuoc = dong["thuoc"]
    ma_lo = chuan_hoa_ma_lo(dong["ma_lo_thuoc"])
    han = dong["ngay_het_han"]
    if not re.fullmatch(MA_NGHIEP_VU, ma_lo):
        return "ma_lo_thuoc", "Mã lô gồm tối đa 32 chữ in hoa, số, gạch ngang hoặc gạch dưới."
    if not thuoc.dang_hoat_dong:
        return "thuoc", f"Thuốc {thuoc.ten_thuoc} đã ngừng kinh doanh, không nhập thêm."
    loi = loi_han_dung(han, hom_nay)
    if loi:
        return "ngay_het_han", loi
    dong_truoc = han_trong_phieu.setdefault((thuoc.pk, ma_lo), (i, han))
    if dong_truoc[1] != han:
        return "ngay_het_han", (
            f"Lô {ma_lo} đã có ở dòng {dong_truoc[0] + 1} với hạn {dong_truoc[1]:%d/%m/%Y}; "
            "một lô chỉ có một hạn dùng."
        )
    lo = LoThuoc.objects.filter(thuoc=thuoc, ma_lo_thuoc=ma_lo).first()
    if lo and lo.ngay_het_han != han:
        goc = (
            ChiTietPhieuNhap.objects.filter(lo_thuoc=lo)
            .select_related("phieu_nhap")
            .order_by("phieu_nhap__thoi_diem_tao", "pk")
            .first()
        )
        theo = f" theo phiếu {goc.phieu_nhap.ma_phieu_nhap}" if goc else ""
        return "ngay_het_han", (
            f"Lô {ma_lo} của {thuoc.ten_thuoc} đã có hạn {lo.ngay_het_han:%d/%m/%Y}{theo}; "
            f"bạn nhập {han:%d/%m/%Y}. Một lô chỉ có một hạn: xem lại nhãn, nếu là lô khác "
            "thì ghi đúng mã lô in trên bao bì."
        )
    if lo and not lo.duoc_phep_ban:
        return "ma_lo_thuoc", (
            f"Lô {ma_lo} đang bị khóa bán{_ly_do_khoa(lo)}. Không nhập thêm hàng của lô này; "
            "báo quản trị chuỗi nếu cần kiểm tra lại."
        )
    quy_doi = dong.get("quy_doi_bao_goi")
    if quy_doi and quy_doi.thuoc_id != thuoc.pk:
        return "quy_doi_bao_goi", "Bao gói này không thuộc thuốc đã chọn; hãy chọn lại."
    try:
        luong = doi_ve_co_so(thuoc, dong["so_luong"], quy_doi)
    except ValidationError as loi_luong:
        return "so_luong", " ".join(loi_luong.messages)
    return None, (thuoc, ma_lo, han, luong, dong["don_gia"])


@transaction.atomic
def nhap_hang(
    nguoi,
    chi_nhanh,
    nha_cung_cap,
    cac_dong,
    ghi_chu="",
    *,
    so_hoa_don_nha_cung_cap="",
    khoa_yeu_cau=None,
):
    """Ghi phiếu nhập và cộng tồn từng lô; mọi dòng được kiểm trước khi ghi.

    Từ chối cả phiếu nếu có dòng sai và chỉ rõ dòng, ô cần sửa (LoiDongPhieu): hạn đã qua
    hoặc xa bất thường, lô đã có với hạn khác, lô đang khóa bán, bao gói không đúng thuốc.
    """
    khoa_chi_nhanh(nguoi, chi_nhanh, "phieu_nhap.tao")
    da_co = phieu_da_luu(PhieuNhap, khoa_yeu_cau, nguoi, chi_nhanh=chi_nhanh)
    if da_co:
        return da_co
    if not nha_cung_cap.dang_hoat_dong:
        raise ValidationError("Nhà cung cấp đã ngừng hoạt động; hãy chọn nhà cung cấp khác.")
    if not cac_dong:
        raise ValidationError("Phiếu nhập cần ít nhất một dòng hàng.")
    hom_nay = timezone.localdate()
    han_trong_phieu, cac_loi, hop_le = {}, [], []
    for i, dong in enumerate(cac_dong):
        o_sai, ket_qua = _kiem_dong(i, dong, hom_nay, han_trong_phieu)
        if o_sai:
            cac_loi.append((i, o_sai, ket_qua))
        else:
            hop_le.append(ket_qua)
    if cac_loi:
        raise LoiDongPhieu(cac_loi)
    phieu = PhieuNhap.objects.create(
        ma_phieu_nhap=ma_chung_tu("PN"),
        chi_nhanh=chi_nhanh,
        nha_cung_cap=nha_cung_cap,
        nguoi_lap=nguoi,
        ghi_chu=cat_khoang_trang(ghi_chu),
        so_hoa_don_nha_cung_cap=cat_khoang_trang(so_hoa_don_nha_cung_cap or ""),
        khoa_yeu_cau=chuan_hoa_khoa(khoa_yeu_cau),
    )
    for thuoc, ma_lo, han, luong, don_gia in hop_le:
        lo, _ = LoThuoc.objects.get_or_create(
            thuoc=thuoc, ma_lo_thuoc=ma_lo, defaults={"ngay_het_han": han}
        )
        lo.full_clean()
        chi_tiet = ChiTietPhieuNhap(phieu_nhap=phieu, lo_thuoc=lo, so_luong=luong, don_gia=don_gia)
        chi_tiet.full_clean()
        chi_tiet.save()
        ton, _ = TonKho.objects.get_or_create(chi_nhanh=chi_nhanh, lo_thuoc=lo)
        thay_doi_ton(ton, luong)
    return phieu
