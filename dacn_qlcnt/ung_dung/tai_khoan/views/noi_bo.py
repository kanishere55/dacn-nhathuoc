from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render

from ung_dung.chung.loc_danh_sach import BoLoc, OChon
from ung_dung.chung.permissions import yeu_cau_quyen
from ung_dung.danh_muc.models import ChiNhanh

from ..forms import TaiKhoanForm
from ..models import TaiKhoan
from ..selectors import lay_tai_khoan
from ..services.quyen import bang_quyen_nhom, bao_dam_nhom_mac_dinh
from ..services.tai_khoan import luu_tai_khoan


@yeu_cau_quyen("tai_khoan.xem")
def danh_sach(request):
    loc = BoLoc(
        request,
        cac_cot_tim=("ten_dang_nhap", "ho_ten", "email", "so_dien_thoai"),
        nhan_tim="Tên đăng nhập, họ tên, email, số điện thoại",
        cac_o_chon=[
            OChon("vai_tro", "Vai trò", TaiKhoan.VaiTro.choices, "vai_tro"),
            OChon(
                "chi_nhanh",
                "Chi nhánh",
                [(cn.pk, cn.ten_chi_nhanh) for cn in ChiNhanh.objects.order_by("ma_chi_nhanh")],
                "chi_nhanh_id",
            ),
            OChon(
                "trang_thai",
                "Trạng thái",
                [("hoat_dong", "Đang hoạt động"), ("khoa", "Đã khóa")],
                ham_loc=lambda tap_hop, gia_tri: tap_hop.filter(
                    dang_hoat_dong=gia_tri == "hoat_dong"
                ),
            ),
        ],
    )
    cac_tai_khoan = lay_tai_khoan(request.user).select_related("nhom_quyen", "chi_nhanh")
    return render(request, "tai_khoan/danh_sach.html", loc.ngu_canh(cac_tai_khoan))


@yeu_cau_quyen("tai_khoan.sua")
def chinh_sua(request, ma=None):
    doi_tuong = get_object_or_404(lay_tai_khoan(request.user), pk=ma) if ma else None
    bao_dam_nhom_mac_dinh()
    form = TaiKhoanForm(request.POST or None, instance=doi_tuong)
    if request.method == "POST" and form.is_valid():
        try:
            luu_tai_khoan(
                request.user,
                {**form.cleaned_data, "quyen_rieng": form.quyen_rieng()},
                doi_tuong,
            )
        except ValidationError as loi:
            form.add_error(None, loi)
        except IntegrityError:
            form.add_error(None, "Tài khoản trùng hoặc dữ liệu đã thay đổi.")
        else:
            return redirect("tai_khoan:danh_sach")
    return render(
        request,
        "tai_khoan/form.html",
        {
            "bang_quyen_nhom": bang_quyen_nhom(),
            "form": form,
            "tieu_de": f"Sửa tài khoản {doi_tuong}" if doi_tuong else "Tạo tài khoản",
        },
    )
