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
    "h2",
    "h3",
    "h4",
    "ul",
    "ol",
    "li",
    "a",
    "blockquote",
}
CAN_LE = {"ql-align-center", "ql-align-right", "ql-align-justify"}
LOP_CHO_PHEP = {the: CAN_LE for the in ("p", "h2", "h3", "h4", "li")}


def lam_sach_html(noi_dung):
    """Chỉ giữ thẻ định dạng cơ bản, liên kết http(s)/mailto/tel và lớp căn lề của trình soạn."""
    sach = nh3.clean(
        noi_dung or "",
        tags=THE_CHO_PHEP,
        attributes={"a": {"href", "title"}},
        allowed_classes=LOP_CHO_PHEP,
        url_schemes={"http", "https", "mailto", "tel"},
        link_rel="noopener noreferrer nofollow",
    )
    sach = sach.replace(" ", " ").replace("&nbsp;", " ")
    # Đoạn rỗng do trình soạn thảo để lại không mang nội dung.
    sach = re.sub(r"(<p>(\s|<br>)*</p>\s*)+$", "", sach.strip())
    sach = re.sub(r"^(<p>(\s|<br>)*</p>\s*)+", "", sach)
    return sach.strip()


def la_html(noi_dung):
    return bool(re.search(r"<(p|ul|ol|h[2-4]|blockquote|br)\b", noi_dung or ""))


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
