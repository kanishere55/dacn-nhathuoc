"""Bộ lọc và phân trang dùng chung cho các trang danh sách của khu quản lý.

View khai báo ô tìm kiếm và các ô chọn (danh mục thả xuống), bộ lọc đọc tham số trên URL,
chỉ nhận giá trị nằm trong danh sách lựa chọn rồi áp lên queryset. Template vẽ thanh lọc
và thanh phân trang bằng `components/_thanh_loc.html` và `components/_phan_trang.html`.
"""

from dataclasses import dataclass, field
from datetime import timedelta

from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

SO_DONG_MOI_TRANG = (10, 25, 50, 100)


@dataclass
class OChon:
    """Một ô chọn thả xuống: `ten` là tham số URL, `cot` là trường ORM cần lọc bằng bằng."""

    ten: str
    nhan: str
    lua_chon: list
    cot: str = ""
    gia_tri: str = ""
    # Hàm tùy biến (queryset, giá trị) -> queryset khi một cột bằng chưa đủ.
    ham_loc: object = None


@dataclass
class BoLoc:
    request: object
    cac_o_chon: list = field(default_factory=list)
    cac_cot_tim: tuple = ()
    nhan_tim: str = "Tìm kiếm"
    mac_dinh_moi_trang: int = 25
    tim: str = ""
    moi_trang: int = 25

    def __post_init__(self):
        tham_so = self.request.GET
        self.tim = tham_so.get("tim", "").strip()[:80]
        so = tham_so.get("moi_trang", "")
        # Giới hạn độ dài trước khi đổi số: chuỗi hàng nghìn chữ số làm int() ném lỗi.
        self.moi_trang = (
            int(so)
            if so.isascii() and so.isdecimal() and len(so) <= 4 and int(so) in SO_DONG_MOI_TRANG
            else self.mac_dinh_moi_trang
        )
        for o in self.cac_o_chon:
            gia_tri = tham_so.get(o.ten, "")
            o.gia_tri = gia_tri if gia_tri in {str(ma) for ma, _ in o.lua_chon} else ""

    def ap_dung(self, tap_hop):
        if self.tim and self.cac_cot_tim:
            dieu_kien = Q()
            for cot in self.cac_cot_tim:
                dieu_kien |= Q(**{f"{cot}__icontains": self.tim})
            tap_hop = tap_hop.filter(dieu_kien)
        for o in self.cac_o_chon:
            if not o.gia_tri:
                continue
            if o.ham_loc:
                tap_hop = o.ham_loc(tap_hop, o.gia_tri)
            else:
                tap_hop = tap_hop.filter(**{o.cot: o.gia_tri})
        return tap_hop

    def trang(self, tap_hop):
        return Paginator(tap_hop, self.moi_trang).get_page(self.request.GET.get("page"))

    @property
    def cac_moi_trang(self):
        return SO_DONG_MOI_TRANG

    @property
    def dang_loc(self):
        return bool(self.tim or any(o.gia_tri for o in self.cac_o_chon))

    def ngu_canh(self, tap_hop):
        """Áp bộ lọc, phân trang rồi trả các biến template dùng chung."""
        trang = self.trang(self.ap_dung(tap_hop))
        return {"loc": self, "trang": trang}


KHOANG_THOI_GIAN = [
    ("hom_nay", "Hôm nay"),
    ("7_ngay", "7 ngày gần đây"),
    ("30_ngay", "30 ngày gần đây"),
    ("thang_nay", "Tháng này"),
    ("nam_nay", "Năm nay"),
]


def o_khoang_thoi_gian(cot, nhan="Thời gian", ten="thoi_gian"):
    """Ô chọn khoảng thời gian tính đến hôm nay trên cột ngày hoặc ngày giờ `cot`."""

    def loc(tap_hop, gia_tri):
        hom_nay = timezone.localdate()
        tu_ngay = {
            "hom_nay": hom_nay,
            "7_ngay": hom_nay - timedelta(days=6),
            "30_ngay": hom_nay - timedelta(days=29),
            "thang_nay": hom_nay.replace(day=1),
            "nam_nay": hom_nay.replace(month=1, day=1),
        }[gia_tri]
        return tap_hop.filter(**{f"{cot}__date__gte": tu_ngay})

    return OChon(ten, nhan, KHOANG_THOI_GIAN, ham_loc=loc)
