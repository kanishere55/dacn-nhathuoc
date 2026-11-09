"""Quản trị chuỗi soạn banner, thông tin cửa hàng và trang chính sách."""

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ung_dung.chung.permissions import yeu_cau_vai_tro

from ..forms import BannerForm, ThongTinCuaHangForm, TrangNoiDungForm
from ..models import BannerTrangChu, ThongTinCuaHang, TrangNoiDung

QUAN_TRI = "quan_tri_chuoi"


@yeu_cau_vai_tro(QUAN_TRI)
def banner_danh_sach(request):
    return render(
        request,
        "noi_dung/quan_ly/banner_danh_sach.html",
        {"cac_banner": BannerTrangChu.objects.defer("noi_dung_anh")},
    )


@yeu_cau_vai_tro(QUAN_TRI)
def banner_sua(request, ma=None):
    banner = get_object_or_404(BannerTrangChu, pk=ma) if ma else None
    form = BannerForm(request.POST or None, request.FILES or None, instance=banner)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            doi_tuong = form.save(commit=False)
            if form.cleaned_data.get("anh"):
                doi_tuong.gan_du_lieu(form.cleaned_data["anh"])
            doi_tuong.save()
        messages.success(request, f"Đã lưu banner “{doi_tuong.tieu_de}”.")
        return redirect("noi_dung:banner_danh_sach")
    return render(
        request,
        "noi_dung/quan_ly/form.html",
        {
            "form": form,
            "tieu_de": "Sửa banner" if banner else "Thêm banner",
            "banner": banner,
            "url_quay_lai": "noi_dung:banner_danh_sach",
            "co_tep": True,
        },
    )


@require_POST
@yeu_cau_vai_tro(QUAN_TRI)
def banner_xoa(request, ma):
    banner = get_object_or_404(BannerTrangChu.objects.defer("noi_dung_anh"), pk=ma)
    banner.delete()
    messages.success(request, f"Đã xóa banner “{banner.tieu_de}”.")
    return redirect("noi_dung:banner_danh_sach")


@yeu_cau_vai_tro(QUAN_TRI)
def thong_tin(request):
    form = ThongTinCuaHangForm(
        request.POST or None, instance=ThongTinCuaHang.objects.filter(pk=1).first()
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Đã lưu thông tin cửa hàng.")
        return redirect("noi_dung:thong_tin")
    return render(
        request,
        "noi_dung/quan_ly/form.html",
        {"form": form, "tieu_de": "Thông tin cửa hàng", "url_quay_lai": None},
    )


@yeu_cau_vai_tro(QUAN_TRI)
def trang_danh_sach(request):
    return render(
        request,
        "noi_dung/quan_ly/trang_danh_sach.html",
        {"cac_trang": TrangNoiDung.objects.defer("noi_dung_trang")},
    )


@yeu_cau_vai_tro(QUAN_TRI)
def trang_sua(request, ma=None):
    trang_nd = get_object_or_404(TrangNoiDung, pk=ma) if ma else None
    form = TrangNoiDungForm(request.POST or None, instance=trang_nd)
    if request.method == "POST" and form.is_valid():
        doi_tuong = form.save()
        messages.success(request, f"Đã lưu trang “{doi_tuong.tieu_de}”.")
        return redirect("noi_dung:trang_danh_sach")
    return render(
        request,
        "noi_dung/quan_ly/form.html",
        {
            "form": form,
            "tieu_de": "Sửa trang" if trang_nd else "Thêm trang",
            "url_quay_lai": "noi_dung:trang_danh_sach",
            "url_xem": trang_nd and f"/trang/{trang_nd.duong_dan_trang}/",
        },
    )
