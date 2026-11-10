"""Kiểm duyệt đánh giá thuốc và chi nhánh: ẩn nhận xét vi phạm, không xóa."""

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from ung_dung.chung.loc_danh_sach import BoLoc, OChon, o_khoang_thoi_gian
from ung_dung.chung.permissions import yeu_cau_quyen

from ..selectors import lay_danh_gia
from ..services.danh_gia import doi_hien_thi_danh_gia

LOAI = {
    "thuoc": ("thuoc", "danh_muc:danh_gia_doi_hien_thi"),
    "chi_nhanh": ("chi_nhanh", "danh_muc:danh_gia_chi_nhanh_doi_hien_thi"),
}


@yeu_cau_quyen("danh_gia.xem")
def danh_sach(request):
    loai = request.GET.get("loai") if request.GET.get("loai") in LOAI else "thuoc"
    doi_tuong, url_doi = LOAI[loai]
    loc = BoLoc(
        request,
        cac_cot_tim=(
            f"{doi_tuong}__ten_{doi_tuong}",
            "khach_hang__ten_dang_nhap",
            "khach_hang__ho_ten",
            "noi_dung_danh_gia",
        ),
        nhan_tim="Tên thuốc hoặc chi nhánh, khách, nội dung",
        cac_o_chon=[
            OChon("so_sao", "Số sao", [(so, f"{so} sao") for so in range(5, 0, -1)], "so_sao"),
            OChon(
                "hien_thi",
                "Hiển thị",
                [("co", "Đang hiện"), ("khong", "Đã ẩn")],
                ham_loc=lambda tap_hop, gia_tri: tap_hop.filter(dang_hien_thi=gia_tri == "co"),
            ),
            o_khoang_thoi_gian("thoi_diem_tao", "Gửi trong"),
        ],
        mac_dinh_moi_trang=30,
    )
    return render(
        request,
        "danh_muc/danh_gia_danh_sach.html",
        {
            **loc.ngu_canh(lay_danh_gia(request.user, loai)),
            "loai": loai,
            "url_doi_hien_thi": url_doi,
        },
    )


def _doi(request, loai, ma):
    try:
        doi_hien_thi_danh_gia(request.user, loai, ma)
    except ObjectDoesNotExist as loi:
        raise Http404(str(loi)) from loi
    tiep = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(tiep, allowed_hosts={request.get_host()}):
        return redirect(tiep)
    return redirect("danh_muc:danh_gia_danh_sach")


@require_POST
@yeu_cau_quyen("danh_gia.kiem_duyet")
def doi_hien_thi(request, ma):
    return _doi(request, "thuoc", ma)


@require_POST
@yeu_cau_quyen("danh_gia.kiem_duyet")
def doi_hien_thi_chi_nhanh(request, ma):
    return _doi(request, "chi_nhanh", ma)
