from datetime import timedelta

from django.shortcuts import render
from django.utils import timezone

from ung_dung.chung.permissions import co_quyen, yeu_cau_quyen
from ung_dung.danh_muc.selectors import lay_chi_nhanh

from ..loc import loc_ton_kho
from ..selectors import lay_bang_ton, lay_canh_bao_ton_thap, phan_loai_canh_bao


@yeu_cau_quyen("ton_kho.xem")
def danh_sach(request):
    hom_nay = timezone.localdate()
    return render(
        request,
        "kho/ton_kho.html",
        {
            **loc_ton_kho(request).ngu_canh(lay_bang_ton(request.user)),
            "hom_nay": hom_nay,
            "moc_canh_bao": hom_nay + timedelta(days=30),
            "nhieu_chi_nhanh": lay_chi_nhanh(request.user).count() > 1,
        },
    )


@yeu_cau_quyen("ton_kho.xem")
def canh_bao(request):
    nguoi = request.user
    cac_muc = phan_loai_canh_bao(nguoi)
    ton_thap = [
        {
            "chi_nhanh": chi_nhanh,
            "thuoc": thuoc,
            "ty_le": min(100, round(thuoc.kha_dung / thuoc.nguong_canh_bao * 100)),
        }
        for chi_nhanh, thuoc in lay_canh_bao_ton_thap(nguoi)
    ]
    return render(
        request,
        "kho/canh_bao.html",
        {
            "cac_muc": cac_muc,
            "ton_thap": ton_thap,
            "tong_canh_bao": sum(len(m["cac_dong"]) for m in cac_muc) + len(ton_thap),
            "nhieu_chi_nhanh": lay_chi_nhanh(nguoi).count() > 1,
            "duoc_xuat_huy": co_quyen(nguoi, "xuat_huy.tao"),
            "duoc_nhap": co_quyen(nguoi, "phieu_nhap.tao"),
            "duoc_xem_lo": co_quyen(nguoi, "lo_thuoc.xem"),
        },
    )
