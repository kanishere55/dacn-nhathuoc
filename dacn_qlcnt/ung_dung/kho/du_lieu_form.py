"""Dữ liệu nhúng vào form phiếu kho (json_script) để trình duyệt gợi ý ngay khi chọn.

Chỉ phục vụ hiển thị: lọc bao gói theo thuốc, tính thành tiền, báo tồn còn dùng được.
Mọi con số vẫn được service tính lại và kiểm khi lưu.
"""

from django.db.models import Sum

from ung_dung.danh_muc.models import QuyDoiBaoGoi, Thuoc

from .selectors import lay_so_du, lay_ton_kha_dung
from .services.phieu_tra_nha_cung_cap import luong_con_tra


def du_lieu_thuoc():
    """{id thuốc: {đơn vị cơ sở, các bao gói (id, tên, hệ số)}} của thuốc đang kinh doanh."""
    ket_qua = {
        str(thuoc.pk): {"don_vi": thuoc.don_vi_tinh.ten_don_vi_tinh.lower(), "bao_goi": []}
        for thuoc in Thuoc.objects.filter(dang_hoat_dong=True).select_related("don_vi_tinh")
    }
    for quy_doi in QuyDoiBaoGoi.objects.filter(thuoc__dang_hoat_dong=True).order_by("he_so", "pk"):
        ket_qua[str(quy_doi.thuoc_id)]["bao_goi"].append(
            {"id": quy_doi.pk, "ten": quy_doi.ten_quy_doi_bao_goi, "he_so": quy_doi.he_so}
        )
    return ket_qua


def ton_ban_duoc_theo_thuoc(cac_chi_nhanh):
    """{id chi nhánh: {id thuốc: lượng còn bán/chuyển được}} (đã trừ phần giữ, lô hết hạn/khóa)."""
    ket_qua = {}
    for chi_nhanh_id, thuoc_id, tong in (
        lay_ton_kha_dung()
        .filter(chi_nhanh__in=cac_chi_nhanh, kha_dung__gt=0)
        .order_by()
        .values_list("chi_nhanh_id", "lo_thuoc__thuoc_id")
        .annotate(tong=Sum("kha_dung"))
    ):
        ket_qua.setdefault(str(chi_nhanh_id), {})[str(thuoc_id)] = tong
    return ket_qua


def ton_theo_lo(cac_chi_nhanh):
    """{id chi nhánh: {id lô: [trong kho, đang giữ, đơn vị]}} của các lô còn hàng."""
    ket_qua = {}
    for ton in lay_so_du().filter(chi_nhanh__in=cac_chi_nhanh, so_luong__gt=0):
        ket_qua.setdefault(str(ton.chi_nhanh_id), {})[str(ton.lo_thuoc_id)] = [
            ton.so_luong,
            ton.dang_giu,
            ton.lo_thuoc.thuoc.don_vi_tinh.ten_don_vi_tinh.lower(),
        ]
    return ket_qua


def lo_cua_phieu_nhap(phieu_nhap):
    """Các lô của phiếu nhập kèm đã nhập, đã trả, tồn, đang giữ và còn trả được."""
    so_du = {ton.lo_thuoc_id: ton for ton in lay_so_du(chi_nhanh=phieu_nhap.chi_nhanh)}
    cac_lo = []
    da_xet = set()
    for chi_tiet in phieu_nhap.chitietphieunhap_set.select_related(
        "lo_thuoc__thuoc__don_vi_tinh"
    ).order_by("lo_thuoc__thuoc__ten_thuoc", "lo_thuoc__ngay_het_han", "pk"):
        lo = chi_tiet.lo_thuoc
        if lo.pk in da_xet:
            continue
        da_xet.add(lo.pk)
        da_nhap, da_tra = luong_con_tra(phieu_nhap, lo)
        ton = so_du.get(lo.pk)
        trong_kho, dang_giu = (ton.so_luong, ton.dang_giu) if ton else (0, 0)
        cac_lo.append(
            {
                "id": lo.pk,
                "nhan": f"{lo.thuoc.ten_thuoc} · lô {lo.ma_lo_thuoc} · HSD {lo.ngay_het_han:%d/%m/%Y}",
                "don_vi": lo.thuoc.don_vi_tinh.ten_don_vi_tinh.lower(),
                "da_nhap": da_nhap,
                "da_tra": da_tra,
                "trong_kho": trong_kho,
                "dang_giu": dang_giu,
                "con_tra_duoc": max(0, min(da_nhap - da_tra, trong_kho - dang_giu)),
            }
        )
    return cac_lo
