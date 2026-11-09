"""Sinh chuỗi VietQR theo chuẩn EMVCo QR của NAPAS (chuyển nhanh tới tài khoản).

Cấu trúc: 00 phiên bản, 01 kiểu QR (12 = động, có số tiền), 38 thông tin tài khoản
(GUID A000000727, BIN ngân hàng, số tài khoản, dịch vụ QRIBFTTA), 53 mã tiền 704,
54 số tiền, 58 quốc gia VN, 62.08 nội dung chuyển khoản, 63 CRC16-CCITT.
"""

import io
import re

import segno


def _truong(ma, gia_tri):
    return f"{ma}{len(gia_tri):02d}{gia_tri}"


def crc16_ccitt(du_lieu):
    crc = 0xFFFF
    for byte in du_lieu.encode("ascii"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def tao_chuoi(bin_ngan_hang, so_tai_khoan, so_tien, noi_dung):
    if not re.fullmatch(r"\d{6}", bin_ngan_hang) or not re.fullmatch(
        r"[0-9A-Za-z]{4,19}", so_tai_khoan
    ):
        raise ValueError("Cấu hình ngân hàng VietQR không hợp lệ.")
    noi_dung = re.sub(r"[^0-9A-Za-z ]", "", noi_dung)[:25]
    tai_khoan = _truong("00", bin_ngan_hang) + _truong("01", so_tai_khoan)
    nguoi_nhan = _truong("00", "A000000727") + _truong("01", tai_khoan) + _truong("02", "QRIBFTTA")
    chuoi = (
        _truong("00", "01")
        + _truong("01", "12")
        + _truong("38", nguoi_nhan)
        + _truong("53", "704")
        + _truong("54", str(int(so_tien)))
        + _truong("58", "VN")
        + _truong("62", _truong("08", noi_dung))
        + "6304"
    )
    return chuoi + crc16_ccitt(chuoi)


def ve_svg(chuoi):
    return segno.make(chuoi, error="m").svg_inline(scale=6, border=2, dark="#0f2f25")


def ve_png(chuoi):
    """PNG có lề trắng rộng để ứng dụng ngân hàng nhận diện tốt khi quét từ ảnh."""
    dem = io.BytesIO()
    segno.make(chuoi, error="m").save(dem, kind="png", scale=10, border=4, dark="#0f2f25")
    return dem.getvalue()
