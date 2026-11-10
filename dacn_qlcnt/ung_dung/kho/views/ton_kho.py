from datetime import timedelta

from django.shortcuts import render
from django.utils import timezone

from ung_dung.chung.permissions import co_quyen, yeu_cau_quyen
from ung_dung.danh_muc.selectors import lay_chi_nhanh

from ..loc import loc_canh_bao, loc_ton_kho
from ..selectors import (
    MUC_CANH_BAO,
    lay_bang_ton,
    lay_canh_bao_ton_thap,
    lay_so_du,
    lo_theo_muc_canh_bao,
)


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
    """Hàng việc cảnh báo kho: mỗi thẻ một mức độ, có tìm, lọc chi nhánh/danh mục, phân trang."""
    nguoi = request.user
    loc = loc_canh_bao(request)
    gia_tri = {o.ten: o.gia_tri for o in loc.cac_o_chon}
    so_du = loc.ap_dung(lay_so_du(nguoi=nguoi))
    ton_thap = [
        {
            "chi_nhanh": chi_nhanh,
            "thuoc": thuoc,
            "ty_le": min(100, round(thuoc.kha_dung / thuoc.nguong_canh_bao * 100)),
        }
        for chi_nhanh, thuoc in lay_canh_bao_ton_thap(
            nguoi,
            chi_nhanh_id=gia_tri.get("chi_nhanh", ""),
            danh_muc_id=gia_tri.get("danh_muc", ""),
            tim=loc.tim,
        )
    ]
    cac_the = [
        {
            "ma": ma,
            "ten": ten,
            "huong_dan": huong_dan,
            "so": lo_theo_muc_canh_bao(so_du, ma).count(),
        }
        for ma, ten, huong_dan in MUC_CANH_BAO
    ]
    cac_the.append(
        {
            "ma": "ton_thap",
            "ten": "Tồn dưới ngưỡng",
            "huong_dan": (
                "Lượng còn bán được thấp hơn ngưỡng đã đặt cho thuốc. "
                "Nên nhập thêm hoặc xin điều chuyển từ chi nhánh khác."
            ),
            "so": len(ton_thap),
        }
    )
    # Mặc định mở mức gấp nhất đang có việc.
    muc = request.GET.get("muc", "")
    if muc not in {the["ma"] for the in cac_the}:
        muc = next((the["ma"] for the in cac_the if the["so"]), "het_han")
    the_dang_mo = next(the for the in cac_the if the["ma"] == muc)
    if muc == "ton_thap":
        trang = loc.trang(ton_thap)
    else:
        trang = loc.trang(
            lo_theo_muc_canh_bao(so_du, muc).order_by(
                "lo_thuoc__ngay_het_han", "chi_nhanh__ten_chi_nhanh", "lo_thuoc__thuoc__ten_thuoc"
            )
        )
        hom_nay = timezone.localdate()
        for dong in trang:
            dong.so_ngay_con = (dong.lo_thuoc.ngay_het_han - hom_nay).days
            dong.so_ngay_qua = -dong.so_ngay_con
    return render(
        request,
        "kho/canh_bao.html",
        {
            "loc": loc,
            "trang": trang,
            "muc": muc,
            "cac_the": cac_the,
            "the_dang_mo": the_dang_mo,
            "tong_canh_bao": sum(the["so"] for the in cac_the),
            "nhieu_chi_nhanh": lay_chi_nhanh(nguoi).count() > 1,
            "duoc_xuat_huy": co_quyen(nguoi, "xuat_huy.tao"),
            "duoc_nhap": co_quyen(nguoi, "phieu_nhap.tao"),
            "duoc_xem_lo": co_quyen(nguoi, "lo_thuoc.xem"),
        },
    )
