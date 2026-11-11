from datetime import timedelta

from django.db.models import OuterRef, Subquery
from django.shortcuts import render
from django.utils import timezone

from ung_dung.ban_hang.selectors import lay_don
from ung_dung.ban_hang.services.giu_hang import don_giu_tren_lo_hong
from ung_dung.chung.permissions import co_quyen, thay_toan_chuoi, yeu_cau_quyen
from ung_dung.danh_muc.selectors import lay_chi_nhanh

from ..loc import loc_canh_bao, loc_ton_kho
from ..models import LichSuDieuKienLo
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
            "duoc_nhap": co_quyen(request.user, "phieu_nhap.tao"),
        },
    )


def huong_dan_theo_quyen(nguoi, ma, mac_dinh):
    """Câu hướng dẫn của thẻ cảnh báo chỉ nêu việc người xem làm được, hoặc ai sẽ làm."""
    if ma == "het_han" and not co_quyen(nguoi, "xuat_huy.tao"):
        return (
            "Không được bán. Tách khỏi kệ, để riêng ở khu chờ hủy và báo quản lý chi nhánh lập "
            "phiếu xuất hủy."
        )
    if ma == "khoa_ban":
        if co_quyen(nguoi, "lo_thuoc.sua") and thay_toan_chuoi(nguoi):
            return (
                "Lô bị khóa bán ở mọi chi nhánh. Xem lý do bên dưới; mở bán lại ở trang Lô thuốc "
                "khi đã kiểm tra xong, hoặc lập phiếu xuất hủy lý do thu hồi."
            )
        return (
            "Không bán, để riêng khỏi kệ. Quản trị chuỗi sẽ kết luận mở bán lại hay thu hồi; "
            "khi có thông báo thu hồi, quản lý chi nhánh lập phiếu xuất hủy lý do thu hồi."
        )
    if ma == "ton_thap":
        return (
            "Lượng còn bán được thấp hơn ngưỡng đã đặt cho thuốc. Nên nhập thêm, hoặc nhờ chi "
            "nhánh còn hàng lập phiếu điều chuyển sang."
        )
    return mac_dinh


def _ly_do_khoa(tap_hop):
    """Lý do khóa gần nhất của lô, để thẻ "Đang khóa bán" cho biết vì sao."""
    gan_nhat = LichSuDieuKienLo.objects.filter(
        lo_thuoc=OuterRef("lo_thuoc"), duoc_phep_ban=False
    ).order_by("-thoi_diem_tao", "-pk")
    return tap_hop.annotate(
        ly_do_khoa=Subquery(gan_nhat.values("ly_do")[:1]),
        so_van_ban_thu_hoi=Subquery(gan_nhat.values("so_van_ban_thu_hoi")[:1]),
        thoi_diem_khoa=Subquery(gan_nhat.values("thoi_diem_tao")[:1]),
    )


@yeu_cau_quyen("ton_kho.xem")
def canh_bao(request):
    """Hàng việc cảnh báo kho: mỗi thẻ một mức độ, có tìm, lọc chi nhánh/danh mục, phân trang."""
    nguoi = request.user
    loc = loc_canh_bao(request)
    gia_tri = {o.ten: o.gia_tri for o in loc.cac_o_chon}
    don_can_xu_ly = lay_don(nguoi).filter(pk__in=don_giu_tren_lo_hong().values("pk"))
    if not co_quyen(nguoi, "don_hang.xem"):
        don_can_xu_ly = don_can_xu_ly.none()
    chi_nhanh_dang_loc = gia_tri.get("chi_nhanh")
    if chi_nhanh_dang_loc:
        don_can_xu_ly = don_can_xu_ly.filter(chi_nhanh_id=chi_nhanh_dang_loc)
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
            "huong_dan": huong_dan_theo_quyen(nguoi, ma, huong_dan),
            "so": lo_theo_muc_canh_bao(so_du, ma).count(),
        }
        for ma, ten, huong_dan in MUC_CANH_BAO
    ]
    cac_the.append(
        {
            "ma": "ton_thap",
            "ten": "Tồn dưới ngưỡng",
            "huong_dan": huong_dan_theo_quyen(nguoi, "ton_thap", ""),
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
        tap_hop = lo_theo_muc_canh_bao(so_du, muc)
        if muc == "khoa_ban":
            tap_hop = _ly_do_khoa(tap_hop)
        trang = loc.trang(
            tap_hop.order_by(
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
            # Lập sẵn phiếu xuất hủy cho đúng chi nhánh đang lọc (không mặc định chi nhánh đầu).
            "chi_nhanh_dang_loc": gia_tri.get("chi_nhanh", ""),
            "duoc_nhap": co_quyen(nguoi, "phieu_nhap.tao"),
            "duoc_xem_lo": co_quyen(nguoi, "lo_thuoc.xem"),
            "so_don_can_xu_ly": don_can_xu_ly.count(),
            "don_can_xu_ly": list(don_can_xu_ly[:5]),
        },
    )
