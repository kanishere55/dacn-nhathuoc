"""Tính quyền hiệu lực và quản lý nhóm quyền, quyền riêng của tài khoản.

Quyền hiệu lực = quyền của nhóm (nhóm được gán hoặc nhóm mặc định của vai trò)
+ quyền riêng cho thêm - quyền riêng bị chặn. Quản trị chuỗi luôn có mọi quyền.
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from ung_dung.chung.permissions import kiem_tra_vai_tro

from .. import quyen as danh_muc_quyen
from ..models import NhomQuyen, QuyenCuaNhom, QuyenRiengTaiKhoan


def quyen_co_so(vai_tro, id_nhom_quyen=None):
    """Quyền của nhóm được gán, hoặc của nhóm mặc định theo vai trò khi chưa gán nhóm."""
    if vai_tro not in danh_muc_quyen.MAC_DINH:
        return set()
    nhom_id = id_nhom_quyen or (
        NhomQuyen.objects.filter(vai_tro_mac_dinh=vai_tro).values_list("pk", flat=True).first()
    )
    if nhom_id is None:
        return set(danh_muc_quyen.MAC_DINH[vai_tro])
    return set(
        QuyenCuaNhom.objects.filter(nhom_quyen_id=nhom_id).values_list("ma_quyen", flat=True)
    )


def bang_quyen_nhom():
    """{id nhóm: [mã quyền]} và {vai trò: [mã quyền mặc định]} để form chọn nhanh trên trình duyệt."""
    theo_nhom = {}
    for nhom_id, ma in QuyenCuaNhom.objects.values_list("nhom_quyen_id", "ma_quyen"):
        theo_nhom.setdefault(str(nhom_id), []).append(ma)
    return {
        "nhom": theo_nhom,
        "mac_dinh": {vai_tro: sorted(quyen_co_so(vai_tro)) for vai_tro in danh_muc_quyen.MAC_DINH},
    }


def tinh_quyen_hieu_luc(tai_khoan):
    if not tai_khoan.is_authenticated or not tai_khoan.is_active:
        return frozenset()
    if tai_khoan.vai_tro == danh_muc_quyen.QUAN_TRI:
        return danh_muc_quyen.MA_QUYEN
    if tai_khoan.vai_tro not in danh_muc_quyen.MAC_DINH:
        return frozenset()
    quyen = quyen_co_so(tai_khoan.vai_tro, tai_khoan.nhom_quyen_id)
    for ma_quyen, duoc_phep in QuyenRiengTaiKhoan.objects.filter(tai_khoan=tai_khoan).values_list(
        "ma_quyen", "duoc_phep"
    ):
        (quyen.add if duoc_phep else quyen.discard)(ma_quyen)
    return frozenset(quyen & danh_muc_quyen.QUYEN_GIAO_DUOC)


@transaction.atomic
def bao_dam_nhom_mac_dinh():
    """Tạo hai nhóm mặc định theo quyền khai báo trong mã nếu chưa có; nhóm và quyền cùng một giao dịch."""
    for vai_tro, (ma, ten) in danh_muc_quyen.TEN_NHOM_MAC_DINH.items():
        nhom, moi = NhomQuyen.objects.get_or_create(
            vai_tro_mac_dinh=vai_tro,
            defaults={
                "ma_nhom_quyen": ma,
                "ten_nhom_quyen": ten,
                "mo_ta": "Áp dụng khi tài khoản chưa được gán nhóm riêng.",
            },
        )
        if moi:
            QuyenCuaNhom.objects.bulk_create(
                QuyenCuaNhom(nhom_quyen=nhom, ma_quyen=ma_quyen)
                for ma_quyen in sorted(danh_muc_quyen.MAC_DINH[vai_tro])
            )


def _kiem_ma(cac_ma):
    khong_hop_le = set(cac_ma) - danh_muc_quyen.QUYEN_GIAO_DUOC
    if khong_hop_le:
        raise ValidationError(f"Quyền không hợp lệ hoặc không giao được: {sorted(khong_hop_le)}")


@transaction.atomic
def luu_nhom_quyen(nguoi, du_lieu, cac_ma_quyen, nhom=None):
    kiem_tra_vai_tro(nguoi, danh_muc_quyen.QUAN_TRI)
    _kiem_ma(cac_ma_quyen)
    nhom = NhomQuyen.objects.select_for_update().get(pk=nhom.pk) if nhom else NhomQuyen()
    nhom.ma_nhom_quyen = du_lieu["ma_nhom_quyen"]
    nhom.ten_nhom_quyen = du_lieu["ten_nhom_quyen"]
    nhom.mo_ta = du_lieu.get("mo_ta", "")
    nhom.full_clean()
    nhom.save()
    QuyenCuaNhom.objects.filter(nhom_quyen=nhom).exclude(ma_quyen__in=cac_ma_quyen).delete()
    da_co = set(QuyenCuaNhom.objects.filter(nhom_quyen=nhom).values_list("ma_quyen", flat=True))
    QuyenCuaNhom.objects.bulk_create(
        QuyenCuaNhom(nhom_quyen=nhom, ma_quyen=ma) for ma in sorted(set(cac_ma_quyen) - da_co)
    )
    return nhom


@transaction.atomic
def xoa_nhom_quyen(nguoi, nhom):
    kiem_tra_vai_tro(nguoi, danh_muc_quyen.QUAN_TRI)
    nhom = NhomQuyen.objects.select_for_update().get(pk=nhom.pk)
    if nhom.vai_tro_mac_dinh:
        raise ValidationError("Không xóa nhóm mặc định của vai trò; hãy sửa quyền của nhóm.")
    if nhom.cac_tai_khoan.exists():
        raise ValidationError(
            "Nhóm đang được gán cho tài khoản; hãy chuyển tài khoản sang nhóm khác."
        )
    QuyenCuaNhom.objects.filter(nhom_quyen=nhom).delete()
    nhom.delete()


def ghi_quyen_rieng(tai_khoan, che_do_theo_quyen):
    """Ghi lại toàn bộ quyền riêng của tài khoản; dùng chung cho form tài khoản và lệnh trực tiếp.

    `che_do_theo_quyen`: mã quyền -> True (cho thêm), False (chặn) hoặc None (theo nhóm).
    """
    _kiem_ma(che_do_theo_quyen)
    QuyenRiengTaiKhoan.objects.filter(tai_khoan=tai_khoan).delete()
    QuyenRiengTaiKhoan.objects.bulk_create(
        QuyenRiengTaiKhoan(tai_khoan=tai_khoan, ma_quyen=ma, duoc_phep=gia_tri)
        for ma, gia_tri in che_do_theo_quyen.items()
        if gia_tri is not None
    )


@transaction.atomic
def luu_quyen_rieng(nguoi, tai_khoan, che_do_theo_quyen):
    kiem_tra_vai_tro(nguoi, danh_muc_quyen.QUAN_TRI)
    ghi_quyen_rieng(tai_khoan, che_do_theo_quyen)
