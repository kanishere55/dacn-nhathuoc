"""Vẽ ảnh minh họa sản phẩm (hộp, hộp dẹt, chai) bằng Pillow và phông Be Vietnam Pro.

Dùng khi chưa có ảnh chụp sản phẩm được phép sử dụng: ảnh ghi đúng tên, hoạt chất,
hàm lượng, dạng bào chế, quy cách của thuốc trong CSDL và được gắn nhãn "Hình minh họa".
"""

from io import BytesIO
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageDraw, ImageFilter, ImageFont

THU_MUC_PHONG = Path(settings.BASE_DIR) / "static" / "vendor" / "be_vietnam_pro"
CO = 1200


def _phong(kieu, co):
    tep = {"thuong": "Regular", "vua": "SemiBold", "dam": "Bold"}[kieu]
    return ImageFont.truetype(str(THU_MUC_PHONG / f"BeVietnamPro-{tep}.ttf"), co)


def _hex(mau):
    mau = mau.lstrip("#")
    return tuple(int(mau[i : i + 2], 16) for i in (0, 2, 4))


def _tron(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b, strict=True))


def _toi(mau, he_so):
    return tuple(max(0, round(x * he_so)) for x in mau)


def _xuong_dong(ve, chu, phong, rong_toi_da, so_dong_toi_da=3):
    cac_tu, cac_dong, dong = chu.split(), [], ""
    for tu in cac_tu:
        thu = f"{dong} {tu}".strip()
        if ve.textlength(thu, font=phong) <= rong_toi_da:
            dong = thu
        else:
            if dong:
                cac_dong.append(dong)
            dong = tu
    if dong:
        cac_dong.append(dong)
    return cac_dong[:so_dong_toi_da]


def _vua_khung(ve, chu, kieu, co_lon, co_nho, rong, so_dong):
    """Cỡ chữ lớn nhất để chữ nằm gọn trong `so_dong` dòng."""
    for co in range(co_lon, co_nho - 1, -2):
        phong = _phong(kieu, co)
        cac_dong = _xuong_dong(ve, chu, phong, rong, so_dong + 1)
        if len(cac_dong) <= so_dong and all(ve.textlength(d, font=phong) <= rong for d in cac_dong):
            return phong, cac_dong
    phong = _phong(kieu, co_nho)
    return phong, _xuong_dong(ve, chu, phong, rong, so_dong)


def _nen(mau):
    nen = Image.new("RGB", (CO, CO), (255, 255, 255))
    ve = ImageDraw.Draw(nen)
    nhat = _tron(mau, (255, 255, 255), 0.9)
    for y in range(CO):
        ve.line([(0, y), (CO, y)], fill=_tron((252, 253, 252), nhat, y / CO))
    return nen


def _bong(nen, hop):
    x0, y0, x1, y1 = hop
    lop = Image.new("L", (CO, CO), 0)
    ImageDraw.Draw(lop).ellipse((x0, y1 - 26, x1, y1 + 30), fill=120)
    lop = lop.filter(ImageFilter.GaussianBlur(26))
    nen.paste((40, 60, 50), (0, 0), lop)


def _mat_truoc(sp, rong, cao, mau):
    """Mặt trước bao bì: dải màu thương hiệu, tên, hoạt chất, quy cách, nhãn kê đơn."""
    mat = Image.new("RGB", (rong, cao), (255, 255, 255))
    ve = ImageDraw.Draw(mat)
    don_vi = min(rong, cao * 0.74)  # cỡ chữ theo cạnh ngắn để hộp dẹt không tràn chữ
    le = round(rong * 0.08)
    cao_dai = round(cao * 0.2)
    ve.rectangle((0, 0, rong, cao_dai), fill=mau)
    ve.polygon([(0, cao_dai), (rong, cao_dai - round(cao * 0.05)), (rong, cao_dai)], fill=mau)
    phong_hang = _phong("vua", max(20, round(don_vi * 0.05)))
    ve.text(
        (le, round(cao_dai * 0.5)),
        sp["nha_san_xuat"].upper(),
        font=phong_hang,
        fill=(255, 255, 255),
        anchor="lm",
    )
    y = cao_dai + round(cao * 0.06)
    phong_ten, cac_dong = _vua_khung(
        ve, sp["ten_hien_thi"], "dam", round(don_vi * 0.13), round(don_vi * 0.07), rong - 2 * le, 2
    )
    for dong in cac_dong:
        ve.text((le, y), dong, font=phong_ten, fill=_toi(mau, 0.62))
        y += round(phong_ten.size * 1.12)
    y += round(cao * 0.015)
    phong_hc, dong_hc = _vua_khung(
        ve,
        sp["hoat_chat"],
        "vua",
        round(don_vi * 0.056),
        round(don_vi * 0.036),
        rong - 2 * le - round(don_vi * 0.2),
        2,
    )
    for dong in dong_hc:
        ve.text((le, y), dong, font=phong_hc, fill=(40, 52, 47))
        y += round(phong_hc.size * 1.25)
    y += round(cao * 0.02)
    phong_nho = _phong("thuong", round(don_vi * 0.044))
    for dong in _xuong_dong(
        ve, f"{sp['dang_bao_che']} · {sp['quy_cach']}", phong_nho, rong - 2 * le, 2
    ):
        ve.text((le, y), dong, font=phong_nho, fill=(90, 104, 97))
        y += round(phong_nho.size * 1.3)
    # Hình viên thuốc/giọt trang trí ở góc dưới phải.
    r = round(don_vi * 0.1)
    cx, cy = rong - le - r, cao - round(cao * 0.2)
    ve.ellipse((cx - r, cy - r, cx + r, cy + r), fill=_tron(mau, (255, 255, 255), 0.82))
    ve.rounded_rectangle(
        (cx - r * 0.75, cy - r * 0.32, cx + r * 0.75, cy + r * 0.32),
        radius=round(r * 0.32),
        fill=_tron(mau, (255, 255, 255), 0.25),
    )
    ve.line((cx, cy - r * 0.32, cx, cy + r * 0.32), fill=(255, 255, 255), width=4)
    # Nhãn kê đơn / không kê đơn.
    nhan = "Thuốc kê đơn" if sp["ke_don"] else "Không kê đơn"
    mau_nhan = (178, 34, 34) if sp["ke_don"] else _toi(mau, 0.75)
    phong_nhan = _phong("dam", round(don_vi * 0.042))
    rong_nhan = ve.textlength(nhan, font=phong_nhan) + le
    y_nhan = cao - round(cao * 0.1)
    ve.rounded_rectangle(
        (le, y_nhan - phong_nhan.size, le + rong_nhan, y_nhan + phong_nhan.size * 0.7),
        radius=10,
        outline=mau_nhan,
        width=4,
    )
    ve.text(
        (le + le / 2, y_nhan - phong_nhan.size * 0.15),
        nhan,
        font=phong_nhan,
        fill=mau_nhan,
        anchor="lm",
    )
    return mat


def _ve_hop(nen, sp, mau, rong, cao):
    sau = round(rong * 0.2)
    x0 = (CO - rong - sau) // 2
    y0 = (CO - cao) // 2 + sau // 3
    _bong(nen, (x0 - 10, y0, x0 + rong + sau + 10, y0 + cao))
    ve = ImageDraw.Draw(nen)
    lech = round(sau * 0.55)
    # Mặt trên và mặt bên tạo chiều sâu.
    ve.polygon(
        [(x0, y0), (x0 + sau, y0 - lech), (x0 + rong + sau, y0 - lech), (x0 + rong, y0)],
        fill=_tron(mau, (255, 255, 255), 0.55),
    )
    ve.polygon(
        [
            (x0 + rong, y0),
            (x0 + rong + sau, y0 - lech),
            (x0 + rong + sau, y0 + cao - lech),
            (x0 + rong, y0 + cao),
        ],
        fill=_toi(mau, 0.78),
    )
    nen.paste(_mat_truoc(sp, rong, cao, mau), (x0, y0))
    ve.line((x0, y0, x0 + rong, y0), fill=_toi(mau, 0.9), width=2)


def _ve_chai(nen, sp, mau):
    rong, cao = 470, 760
    x0, y0 = (CO - rong) // 2, (CO - cao) // 2 + 60
    _bong(nen, (x0, y0, x0 + rong, y0 + cao))
    ve = ImageDraw.Draw(nen)
    than = Image.new("RGBA", (rong, cao), (0, 0, 0, 0))
    ve_than = ImageDraw.Draw(than)
    ve_than.rounded_rectangle(
        (0, 120, rong, cao), radius=70, fill=_tron(mau, (255, 255, 255), 0.12)
    )
    ve_than.rounded_rectangle(
        (rong * 0.22, 40, rong * 0.78, 160), radius=30, fill=_tron(mau, (255, 255, 255), 0.12)
    )
    nen.paste(than, (x0, y0), than)
    ve.rounded_rectangle(
        (x0 + rong * 0.2, y0 - 70, x0 + rong * 0.8, y0 + 60), radius=22, fill=_toi(mau, 0.55)
    )
    nhan = _mat_truoc(sp, rong - 70, 470, mau)
    nen.paste(nhan, (x0 + 35, y0 + 200))


def ve_anh_san_pham(sp):
    """`sp`: ten_hien_thi, hoat_chat, dang_bao_che, quy_cach, nha_san_xuat, ke_don, mau, hinh."""
    mau = _hex(sp["mau"])
    nen = _nen(mau)
    if sp["hinh"] == "chai":
        _ve_chai(nen, sp, mau)
    elif sp["hinh"] == "hop_det":
        _ve_hop(nen, sp, mau, 760, 540)
    else:
        _ve_hop(nen, sp, mau, 560, 760)
    ve = ImageDraw.Draw(nen)
    ve.text(
        (CO - 40, CO - 36),
        "Hình minh họa",
        font=_phong("thuong", 26),
        fill=(150, 160, 155),
        anchor="rs",
    )
    dem = BytesIO()
    nen.save(dem, "PNG")
    return dem.getvalue()
