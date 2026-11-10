"""Nội dung định dạng (soạn bằng trình soạn thảo) được làm sạch trước khi lưu và khi hiển thị."""

import html
import re

import nh3

THE_CHO_PHEP = {
    "p",
    "br",
    "strong",
    "em",
    "u",
    "s",
    "sub",
    "sup",
    "span",
    "h2",
    "h3",
    "h4",
    "ul",
    "ol",
    "li",
    "a",
    "blockquote",
    "img",
}
CAN_LE = {"ql-align-center", "ql-align-right", "ql-align-justify"}
THUT_LE = {f"ql-indent-{so}" for so in range(1, 9)}
CO_CHU = {"ql-size-small", "ql-size-large", "ql-size-huge"}
LOP_ANH = {
    "anh-nd-trai",
    "anh-nd-phai",
    "anh-nd-giua",
    "anh-nd-rong-25",
    "anh-nd-rong-50",
    "anh-nd-rong-75",
    "anh-nd-rong-100",
}
LOP_CHO_PHEP = {
    **{the: CAN_LE | THUT_LE for the in ("p", "h2", "h3", "h4", "li")},
    "span": CO_CHU,
    "img": LOP_ANH,
}
THUOC_TINH = {
    "a": {"href", "title"},
    "span": {"style"},
    "img": {"src", "alt"},
}
# Chỉ giữ màu chữ và màu nền trong thuộc tính style do trình soạn thảo sinh ra.
STYLE_CHO_PHEP = {"color", "background-color"}
MAU_HOP_LE = re.compile(
    r"^(#[0-9a-fA-F]{3,8}|rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)|[a-zA-Z]{3,20})$"
)
# Ảnh trong nội dung chỉ được lấy từ kho ảnh của hệ thống, không tải từ máy chủ khác.
DUONG_DAN_ANH = re.compile(r"^/anh/noi-dung/[0-9]{1,18}/$")


def _loc_thuoc_tinh(the, thuoc_tinh, gia_tri):
    if the == "img" and thuoc_tinh == "src":
        return gia_tri if DUONG_DAN_ANH.fullmatch(gia_tri) else None
    if the == "img" and thuoc_tinh == "alt":
        return gia_tri[:200]
    if the == "span" and thuoc_tinh == "style":
        return _loc_style(gia_tri)
    return gia_tri


def _loc_style(gia_tri):
    cac_khai_bao = []
    for khai_bao in gia_tri.split(";"):
        ten, _, noi_dung = khai_bao.partition(":")
        ten, noi_dung = ten.strip().lower(), noi_dung.strip()
        if ten in STYLE_CHO_PHEP and MAU_HOP_LE.fullmatch(noi_dung):
            cac_khai_bao.append(f"{ten}: {noi_dung}")
    return "; ".join(cac_khai_bao) or None


def lam_sach_html(noi_dung):
    """Giữ thẻ định dạng cơ bản, màu chữ, cỡ chữ, ảnh của hệ thống, liên kết http(s)/mailto/tel."""
    sach = nh3.clean(
        noi_dung or "",
        tags=THE_CHO_PHEP,
        attributes=THUOC_TINH,
        allowed_classes=LOP_CHO_PHEP,
        filter_style_properties=STYLE_CHO_PHEP,
        attribute_filter=_loc_thuoc_tinh,
        url_schemes={"http", "https", "mailto", "tel"},
        link_rel="noopener noreferrer nofollow",
    )
    sach = sach.replace(" ", " ").replace("&nbsp;", " ")
    # Ảnh bị bỏ nguồn (không thuộc kho ảnh của hệ thống) không còn ý nghĩa.
    sach = re.sub(r"<img(?![^>]*\ssrc=)[^>]*>", "", sach)
    # Đoạn rỗng do trình soạn thảo để lại không mang nội dung.
    sach = re.sub(r"(<p>(\s|<br>)*</p>\s*)+$", "", sach.strip())
    sach = re.sub(r"^(<p>(\s|<br>)*</p>\s*)+", "", sach)
    return sach.strip()


def la_html(noi_dung):
    return bool(re.search(r"<(p|ul|ol|h[2-4]|blockquote|br|img)\b", noi_dung or ""))


def van_ban_thanh_html(van_ban):
    """Văn bản thường (dữ liệu cũ) thành đoạn <p>; dòng đơn trong đoạn thành <br>."""
    cac_doan = [doan.strip() for doan in re.split(r"\n\s*\n", (van_ban or "").strip())]
    return "".join(
        "<p>" + "<br>".join(html.escape(dong.strip()) for dong in doan.splitlines()) + "</p>"
        for doan in cac_doan
        if doan
    )


def hien_thi(noi_dung):
    """HTML an toàn để chèn vào trang: làm sạch lại, chuyển văn bản cũ sang đoạn."""
    if not noi_dung:
        return ""
    return lam_sach_html(noi_dung if la_html(noi_dung) else van_ban_thanh_html(noi_dung))


def van_ban_thuan(noi_dung):
    """Chữ thuần của nội dung định dạng, dùng làm mô tả ngắn hoặc kiểm tra rỗng."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", noi_dung or ""))).strip()
