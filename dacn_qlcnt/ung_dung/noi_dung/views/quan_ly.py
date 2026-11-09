"""Quản trị chuỗi soạn banner, thông tin cửa hàng, trang chính sách và tin tức."""

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ung_dung.chung.permissions import yeu_cau_vai_tro

from ..forms import BannerForm, ThongTinCuaHangForm, TinTucForm, TrangNoiDungForm
from ..models import BannerTrangChu, ThongTinCuaHang, TinTuc, TrangNoiDung

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
        # db_default chỉ chạy lúc thêm hàng; mỗi lần lưu phải ghi lại thời điểm.
        form.instance.thoi_diem_cap_nhat = timezone.now()
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
        form.instance.thoi_diem_cap_nhat = timezone.now()
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


@yeu_cau_vai_tro(QUAN_TRI)
def tin_tuc_danh_sach(request):
    return render(
        request,
        "noi_dung/quan_ly/tin_tuc_danh_sach.html",
        {
            "cac_tin": TinTuc.objects.defer("noi_dung_tin_tuc").select_related("nguoi_viet"),
            "bay_gio": timezone.now(),
        },
    )


@yeu_cau_vai_tro(QUAN_TRI)
def tin_tuc_sua(request, ma=None):
    tin = get_object_or_404(TinTuc, pk=ma) if ma else None
    form = TinTucForm(request.POST or None, instance=tin)
    if request.method == "POST" and form.is_valid():
        doi_tuong = form.save(commit=False)
        bay_gio = timezone.now()
        if not doi_tuong.pk:
            doi_tuong.nguoi_viet = request.user
        if not form.cleaned_data.get("thoi_diem_dang"):
            doi_tuong.thoi_diem_dang = tin.thoi_diem_dang if tin else bay_gio
        doi_tuong.thoi_diem_cap_nhat = bay_gio
        doi_tuong.save()
        messages.success(request, f"Đã lưu tin “{doi_tuong.tieu_de}”.")
        return redirect("noi_dung:tin_tuc_danh_sach")
    return render(
        request,
        "noi_dung/quan_ly/form.html",
        {
            "form": form,
            "tieu_de": "Sửa tin tức" if tin else "Viết tin tức",
            "url_quay_lai": "noi_dung:tin_tuc_danh_sach",
            "url_xem": tin and f"/tin-tuc/{tin.duong_dan_tin_tuc}/",
        },
    )
