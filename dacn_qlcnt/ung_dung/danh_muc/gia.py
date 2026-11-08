"""Quy tắc giá bán lẻ: giá niêm yết trừ khuyến mãi phần trăm, làm tròn tới đồng."""

from decimal import ROUND_HALF_UP, Decimal


def tinh_don_gia(gia_ban, phan_tram_giam=0):
    gia_ban = Decimal(gia_ban)
    if not phan_tram_giam:
        return gia_ban
    giam = gia_ban * Decimal(phan_tram_giam) / Decimal(100)
    return (gia_ban - giam).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
