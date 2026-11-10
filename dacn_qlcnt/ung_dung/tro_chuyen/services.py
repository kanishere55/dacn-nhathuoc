"""Nghiệp vụ trò chuyện: một cuộc trò chuyện cho mỗi khách với mỗi chi nhánh (kiểu Shopee).

Dù khách hỏi tư vấn, hỏi về một sản phẩm hay về một đơn hàng, mọi tin đều nằm chung một hộp
thoại giữ toàn bộ lịch sử. Hỏi từ trang thuốc hoặc trang đơn thì tin đầu tiên gắn thẻ sản phẩm
hoặc thẻ đơn hàng ("Bạn đang hỏi về…"), nhắn thẳng thì không có thẻ.

Cuộc trò chuyện chỉ được tạo cùng tin đầu tiên trong một giao dịch: bấm nút mà chưa gửi gì thì
không có gì ở cả hai phía. Khách bị giới hạn tốc độ gửi để chống spam hộp thư.
"""

from datetime import timedelta
from uuid import UUID, uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from ung_dung.chung.van_ban import cat_khoang_trang

from .models import SO_ANH_TOI_DA, AnhTinNhan, CuocTroChuyen, TinNhan
from .permissions import duoc_phu_trach_chi_nhanh, kiem_tra_phong

# Khách gửi quá số tin này trong một phút thì phải chờ; đủ cho người gõ thật, chặn gửi dồn.
GIOI_HAN_TIN_MOT_PHUT = 8
# Một khách mở tối đa từng này cuộc trò chuyện mới mỗi ngày (mỗi chi nhánh một cuộc).
GIOI_HAN_PHONG_MOT_NGAY = 10
SO_KY_TU_TOI_DA = 2000


def _la_khach(nguoi):
    return nguoi.is_authenticated and nguoi.is_active and nguoi.vai_tro == "khach_hang"


def _lay_hoac_tao(khach_id, chi_nhanh_id):
    """Trả (cuộc trò chuyện, mới tạo). Hai yêu cầu cùng lúc: bản sau vướng ràng buộc duy nhất
    (khách, chi nhánh) thì đọc lại bản đã có."""
    try:
        with transaction.atomic():
            return CuocTroChuyen.objects.get_or_create(
                khach_hang_id=khach_id, chi_nhanh_id=chi_nhanh_id
            )
    except IntegrityError:
        return CuocTroChuyen.objects.get(khach_hang_id=khach_id, chi_nhanh_id=chi_nhanh_id), False


def kiem_tra_nhan_ve_don(nguoi, don):
    """Ai được nhắn về đơn: khách chủ đơn, hoặc nhân sự phụ trách chi nhánh của đơn."""
    if _la_khach(nguoi):
        if don.khach_hang_id != nguoi.pk:
            raise PermissionDenied("Đơn không thuộc tài khoản của bạn.")
    elif not duoc_phu_trach_chi_nhanh(nguoi, don.chi_nhanh_id):
        raise PermissionDenied("Bạn không phụ trách chi nhánh của đơn này.")


def mo_phong(nguoi, chi_nhanh):
    """Cuộc trò chuyện của khách với chi nhánh (tạo nếu chưa có). Dùng cho kiểm thử, dữ liệu mẫu;
    giao diện luôn đi qua bat_dau_tro_chuyen để không sinh cuộc trò chuyện rỗng."""
    if not _la_khach(nguoi):
        raise PermissionDenied("Chỉ khách hàng được mở cuộc trò chuyện tư vấn.")
    return _lay_hoac_tao(nguoi.pk, chi_nhanh.pk)[0]


def ben_cua(nguoi, phong):
    return "khach" if nguoi.pk == phong.khach_hang_id else "nha_thuoc"


def _day_moc_da_doc(phong, ben, tin_id):
    """Chỉ cho mốc đã đọc tiến lên; trả về True khi mốc thực sự thay đổi."""
    cot = "tin_khach_da_doc" if ben == "khach" else "tin_nha_thuoc_da_doc"
    hien_tai = getattr(phong, f"{cot}_id")
    if hien_tai is not None and hien_tai >= tin_id:
        return False
    setattr(phong, f"{cot}_id", tin_id)
    phong.save(update_fields=[cot])
    return True


@transaction.atomic
def danh_dau_da_doc(nguoi, phong, id_tin):
    """Người xem đã thấy tới tin `id_tin`. Trả về (bên, id) khi mốc đổi, None khi không đổi."""
    kiem_tra_phong(nguoi, phong)
    if isinstance(id_tin, bool) or not isinstance(id_tin, int):
        raise ValidationError("Mã tin không hợp lệ.")
    phong = CuocTroChuyen.objects.select_for_update().get(pk=phong.pk)
    if not TinNhan.objects.filter(pk=id_tin, cuoc_tro_chuyen=phong).exists():
        raise ValidationError("Tin không thuộc cuộc trò chuyện này.")
    ben = ben_cua(nguoi, phong)
    return (ben, id_tin) if _day_moc_da_doc(phong, ben, id_tin) else None


def _kiem_toc_do(nguoi):
    """Chống spam: chỉ áp cho khách, nhân sự trả lời không bị giới hạn."""
    if not _la_khach(nguoi):
        return
    mot_phut_truoc = timezone.now() - timedelta(minutes=1)
    da_gui = TinNhan.objects.filter(nguoi_gui=nguoi, thoi_diem_tao__gte=mot_phut_truoc).count()
    if da_gui >= GIOI_HAN_TIN_MOT_PHUT:
        raise ValidationError("Bạn gửi hơi nhanh. Vui lòng chờ khoảng một phút rồi gửi tiếp.")


def _kiem_so_phong_moi(nguoi):
    if not _la_khach(nguoi):
        return
    dau_ngay = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    da_mo = CuocTroChuyen.objects.filter(khach_hang=nguoi, thoi_diem_tao__gte=dau_ngay).count()
    if da_mo > GIOI_HAN_PHONG_MOT_NGAY:
        raise ValidationError(
            "Hôm nay bạn đã nhắn với nhiều nhà thuốc. Hãy nhắn tiếp trong cuộc trò chuyện đang có."
        )


def kiem_tra_the(phong, *, thuoc=None, don=None):
    """Thẻ gắn vào tin: thuốc đang bán, hoặc đơn của đúng khách tại đúng chi nhánh."""
    if thuoc is not None and don is not None:
        raise ValidationError("Một tin chỉ gắn thẻ sản phẩm hoặc thẻ đơn hàng.")
    if thuoc is not None and not thuoc.dang_hoat_dong:
        raise ValidationError("Sản phẩm này đã ngừng kinh doanh.")
    if don is not None and (
        don.khach_hang_id != phong.khach_hang_id or don.chi_nhanh_id != phong.chi_nhanh_id
    ):
        raise ValidationError("Đơn hàng không thuộc cuộc trò chuyện này.")


def _chuan_hoa_noi_dung(noi_dung, co_anh):
    if noi_dung is None:
        noi_dung = ""
    if not isinstance(noi_dung, str):
        raise ValidationError("Tin nhắn phải là văn bản.")
    noi_dung = cat_khoang_trang(noi_dung)
    if "\x00" in noi_dung:
        raise ValidationError("Tin nhắn chứa ký tự không hợp lệ.")
    if len(noi_dung) > SO_KY_TU_TOI_DA:
        raise ValidationError(
            f"Tin nhắn dài {len(noi_dung)} ký tự, tối đa {SO_KY_TU_TOI_DA} ký tự. "
            "Hãy chia thành nhiều tin."
        )
    if not noi_dung and not co_anh:
        raise ValidationError("Hãy nhập nội dung tin nhắn hoặc chọn ảnh.")
    return noi_dung


@transaction.atomic
def ghi_tin_nhan(nguoi, phong, ma, noi_dung, *, cac_anh=(), thuoc=None, don=None):
    """Ghi một tin (chữ và/hoặc tối đa 5 ảnh, có thể kèm thẻ). Trả (tin, mới tạo).

    `ma` là UUID trình duyệt tạo: gửi lại cùng mã sau khi mất mạng trả về tin cũ, không ghi trùng.
    """
    kiem_tra_phong(nguoi, phong)
    try:
        ma = str(UUID(ma))
    except (ValueError, TypeError, AttributeError) as loi:
        raise ValidationError("Mã tin nhắn không hợp lệ.") from loi
    cac_anh = list(cac_anh)
    if len(cac_anh) > SO_ANH_TOI_DA:
        raise ValidationError(f"Mỗi tin gửi tối đa {SO_ANH_TOI_DA} ảnh.")
    noi_dung = _chuan_hoa_noi_dung(noi_dung, bool(cac_anh))
    kiem_tra_the(phong, thuoc=thuoc, don=don)
    tin_cu = TinNhan.objects.filter(nguoi_gui=nguoi, ma_tin_nhan=ma).first()
    if tin_cu is not None:
        if tin_cu.cuoc_tro_chuyen_id != phong.pk or tin_cu.noi_dung_tin_nhan != noi_dung:
            raise ValidationError("Mã đã được dùng cho tin nhắn khác.")
        return tin_cu, False
    # Gửi lại cùng mã sau khi mất mạng không tính là tin mới nên không bị giới hạn.
    _kiem_toc_do(nguoi)
    # Xử lý ảnh trước khi ghi: tệp lỗi thì không có tin nào được tạo.
    du_lieu_anh = []
    for thu_tu, tep in enumerate(cac_anh):
        anh = AnhTinNhan(thu_tu=thu_tu)
        try:
            anh.gan_du_lieu(tep)
        except ValidationError as loi:
            ten = getattr(tep, "name", "") or f"thứ {thu_tu + 1}"
            raise ValidationError(f"Ảnh {ten}: {loi.messages[0]}") from loi
        du_lieu_anh.append(anh)
    try:
        with transaction.atomic():
            tin = TinNhan.objects.create(
                nguoi_gui=nguoi,
                ma_tin_nhan=ma,
                cuoc_tro_chuyen=phong,
                noi_dung_tin_nhan=noi_dung,
                so_anh=len(du_lieu_anh),
                thuoc=thuoc,
                don_hang=don,
            )
    except IntegrityError:
        # Hai kết nối gửi cùng mã gần như đồng thời: bản sau đọc lại tin của bản trước.
        tin_cu = TinNhan.objects.filter(nguoi_gui=nguoi, ma_tin_nhan=ma).first()
        if tin_cu is None:
            raise
        return tin_cu, False
    for anh in du_lieu_anh:
        anh.tin_nhan = tin
    AnhTinNhan.objects.bulk_create(du_lieu_anh)
    khoa = CuocTroChuyen.objects.select_for_update().get(pk=phong.pk)
    ben = ben_cua(nguoi, khoa)
    khoa.tin_cuoi = tin
    cac_cot = ["tin_cuoi"]
    if ben == "khach" and khoa.da_xong:
        # Khách hỏi tiếp sau khi nhà thuốc đã đóng: mở lại để không bị bỏ sót.
        khoa.trang_thai_xu_ly = "dang_mo"
        khoa.thoi_diem_xong = None
        khoa.nguoi_danh_dau_xong = None
        cac_cot += ["trang_thai_xu_ly", "thoi_diem_xong", "nguoi_danh_dau_xong"]
    khoa.save(update_fields=cac_cot)
    phong.tin_cuoi_id = tin.pk
    phong.trang_thai_xu_ly = khoa.trang_thai_xu_ly
    # Người vừa trả lời chắc chắn đã xem mọi tin trước đó của cuộc trò chuyện.
    _day_moc_da_doc(khoa, ben, tin.pk)
    return tin, True


@transaction.atomic
def gui_tin_http(nguoi, phong, noi_dung, *, ma=None, cac_anh=(), thuoc=None, don=None):
    """Tin gửi qua HTTP (form tin đầu, tin kèm ảnh); vẫn báo phía bên kia tức thời qua Redis."""
    from .phat_tin_hieu import phat_sau_khi_luu

    tin, da_tao = ghi_tin_nhan(
        nguoi, phong, ma or str(uuid4()), noi_dung, cac_anh=cac_anh, thuoc=thuoc, don=don
    )
    if da_tao:
        phat_sau_khi_luu(nguoi, phong, tin)
    return tin


def bat_dau_tro_chuyen(nguoi, chi_nhanh, noi_dung, *, cac_anh=(), thuoc=None):
    """Khách nhắn một nhà thuốc (có thể kèm thẻ sản phẩm). Đã có cuộc trò chuyện với nhà thuốc
    đó thì tin nối tiếp vào lịch sử cũ; chưa có thì tạo cùng tin đầu trong một giao dịch."""
    if not _la_khach(nguoi):
        raise PermissionDenied("Chỉ khách hàng được bắt đầu trò chuyện với nhà thuốc.")
    if not chi_nhanh.dang_hoat_dong:
        raise ValidationError("Chi nhánh đã ngừng hoạt động.")
    with transaction.atomic():
        phong, moi_tao = _lay_hoac_tao(nguoi.pk, chi_nhanh.pk)
        if moi_tao:
            _kiem_so_phong_moi(nguoi)
        gui_tin_http(nguoi, phong, noi_dung, cac_anh=cac_anh, thuoc=thuoc)
    return phong


def bat_dau_ve_don(nguoi, don, noi_dung, *, cac_anh=()):
    """Khách hoặc nhân sự nhắn về một đơn: tin gắn thẻ đơn, vào cuộc trò chuyện chung của khách
    với chi nhánh của đơn (tạo cùng tin nếu chưa có)."""
    kiem_tra_nhan_ve_don(nguoi, don)
    with transaction.atomic():
        phong, moi_tao = _lay_hoac_tao(don.khach_hang_id, don.chi_nhanh_id)
        if moi_tao:
            _kiem_so_phong_moi(nguoi)
        gui_tin_http(nguoi, phong, noi_dung, cac_anh=cac_anh, don=don)
    return phong


def _dat_trang_thai(nguoi, phong, xong):
    kiem_tra_phong(nguoi, phong)
    if ben_cua(nguoi, phong) != "nha_thuoc":
        raise PermissionDenied("Chỉ nhà thuốc đổi trạng thái xử lý cuộc trò chuyện.")
    khoa = CuocTroChuyen.objects.select_for_update().get(pk=phong.pk)
    if khoa.da_xong != xong:
        khoa.trang_thai_xu_ly = "da_xong" if xong else "dang_mo"
        khoa.thoi_diem_xong = timezone.now() if xong else None
        khoa.nguoi_danh_dau_xong = nguoi if xong else None
        khoa.save(update_fields=["trang_thai_xu_ly", "thoi_diem_xong", "nguoi_danh_dau_xong"])
    return khoa


@transaction.atomic
def danh_dau_xong(nguoi, phong):
    """Nhân sự đóng cuộc trò chuyện đã giải quyết: rời hàng chờ, khách nhắn lại thì mở lại."""
    return _dat_trang_thai(nguoi, phong, True)


@transaction.atomic
def mo_lai(nguoi, phong):
    return _dat_trang_thai(nguoi, phong, False)
