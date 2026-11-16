from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ung_dung.chung.permissions import co_quyen, yeu_cau_quyen
from ung_dung.kho.forms import DongThuocFormSet
from ung_dung.kho.views.chung_tu import hien_danh_sach

from ..forms import PhieuBanForm
from ..hoa_don import du_lieu_hoa_don, ten_tep_pdf, ve_pdf
from ..models import PhieuBan
from ..selectors import du_lieu_quay_ban, lay_phieu_ban, lay_phieu_ban_danh_sach
from ..services.phieu_ban import ban_tai_quay


@yeu_cau_quyen("phieu_ban.xem")
def danh_sach(request):
    return hien_danh_sach(
        request,
        PhieuBan,
        lay_phieu_ban_danh_sach(request.user),
        tieu_de="Phiếu đã bán",
        url_tao="ban_hang:phieu_ban_tao" if co_quyen(request.user, "phieu_ban.tao") else None,
        url_chi_tiet="ban_hang:phieu_ban_chi_tiet",
        cac_cot=(
            ("Số mặt hàng", "so_mat_hang", "so"),
            ("Tổng tiền", "tong_tien", "tien"),
            ("Khách trả bằng", "cach_tra", "chu"),
        ),
        nhan_tao="Bán hàng",
        mo_ta="Phiếu bán trực tiếp tại quầy và phiếu bán khi khách đến nhận đơn đặt giữ.",
    )


@yeu_cau_quyen("phieu_ban.tao")
def tao(request):
    form = PhieuBanForm(request.POST or None, nguoi=request.user)
    cac_dong = DongThuocFormSet(request.POST or None)
    if request.method == "POST" and form.is_valid() and cac_dong.is_valid():
        try:
            phieu = ban_tai_quay(
                request.user,
                form.cleaned_data["chi_nhanh"],
                [d for d in cac_dong.cleaned_data if d and not d.get("DELETE")],
                khoa_yeu_cau=form.cleaned_data["khoa_yeu_cau"],
                don_thuoc=form.don_thuoc(),
                phuong_thuc_thanh_toan=form.cleaned_data["phuong_thuc_thanh_toan"],
            )
        except ValidationError as loi:
            form.add_error(None, loi)
        else:
            return redirect("ban_hang:phieu_ban_chi_tiet", ma=phieu.pk)
    return render(
        request,
        "ban_hang/phieu_ban_form.html",
        {
            "form": form,
            "cac_dong": cac_dong,
            "tieu_de": "Bán tại quầy",
            "du_lieu_quay": du_lieu_quay_ban(form.fields["chi_nhanh"].queryset),
            "dong_ban_dau": _dong_da_nhap(cac_dong) if request.method == "POST" else [],
            "loi_dong": _loi_cac_dong(cac_dong) if request.method == "POST" else [],
        },
    )


def _dong_da_nhap(cac_dong):
    """Các dòng người bán đã nhập, để màn hình dựng lại phiếu khi server báo lỗi."""
    du_lieu = cac_dong.data
    ket_qua = []
    for i in range(min(cac_dong.total_form_count(), 50)):
        ma = du_lieu.get(f"form-{i}-thuoc", "")
        if not ma.isdecimal() or du_lieu.get(f"form-{i}-DELETE"):
            continue
        so_luong = du_lieu.get(f"form-{i}-so_luong", "")
        bao_goi = du_lieu.get(f"form-{i}-quy_doi_bao_goi", "")
        ket_qua.append(
            {
                "thuoc": int(ma),
                "so_luong": int(so_luong) if so_luong.isdecimal() else 1,
                "bao_goi": int(bao_goi) if bao_goi.isdecimal() else None,
            }
        )
    return ket_qua


def _loi_cac_dong(cac_dong):
    loi = list(cac_dong.non_form_errors())
    for i, dong in enumerate(cac_dong.forms, start=1):
        for cac_thong_bao in dong.errors.values():
            loi.extend(f"Dòng {i}: {thong_bao}" for thong_bao in cac_thong_bao)
    return loi


@yeu_cau_quyen("phieu_ban.xem")
def chi_tiet(request, ma):
    phieu = get_object_or_404(lay_phieu_ban(request.user), pk=ma)
    return render(request, "ban_hang/phieu_ban.html", {"hd": du_lieu_hoa_don(phieu)})


@yeu_cau_quyen("phieu_ban.xem")
def hoa_don_in(request, ma):
    phieu = get_object_or_404(lay_phieu_ban(request.user), pk=ma)
    return render(
        request,
        "ban_hang/hoa_don/in.html",
        {
            "hd": du_lieu_hoa_don(phieu),
            "url_quay_lai": reverse("ban_hang:phieu_ban_chi_tiet", args=[phieu.pk]),
            "url_pdf": reverse("ban_hang:phieu_ban_pdf", args=[phieu.pk]),
        },
    )


@yeu_cau_quyen("phieu_ban.xem")
def hoa_don_pdf(request, ma):
    phieu = get_object_or_404(lay_phieu_ban(request.user), pk=ma)
    return tra_pdf(phieu, tai_ve="tai" in request.GET)


def tra_pdf(phieu, *, tai_ve):
    phan_hoi = HttpResponse(ve_pdf(du_lieu_hoa_don(phieu)), content_type="application/pdf")
    kieu = "attachment" if tai_ve else "inline"
    phan_hoi["Content-Disposition"] = f'{kieu}; filename="{ten_tep_pdf(phieu)}"'
    phan_hoi["Cache-Control"] = "private, no-store"
    return phan_hoi
