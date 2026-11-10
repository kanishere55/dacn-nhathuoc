from django.db import migrations

TIEU_DE_MUC = (
    ("cong_dung", "Công dụng"),
    ("cach_dung", "Liều dùng và cách dùng"),
    ("chong_chi_dinh", "Chống chỉ định"),
    ("tac_dung_phu", "Tác dụng không mong muốn"),
    ("luu_y", "Thận trọng, lưu ý"),
    ("bao_quan", "Bảo quản"),
)


def gop_noi_dung(apps, schema_editor):
    """Gộp sáu ô nội dung cũ của thuốc thành một khung, mỗi mục có tiêu đề riêng."""
    from ung_dung.chung.noi_dung_phong_phu import hien_thi

    Thuoc = apps.get_model("danh_muc", "Thuoc")
    for thuoc in Thuoc.objects.all().only("pk", *(ten for ten, _ in TIEU_DE_MUC)):
        cac_phan = []
        for ten, tieu_de in TIEU_DE_MUC:
            noi_dung = hien_thi(getattr(thuoc, ten))
            if noi_dung:
                cac_phan.append(f"<h3>{tieu_de}</h3>{noi_dung}")
        Thuoc.objects.filter(pk=thuoc.pk).update(noi_dung_chi_tiet="".join(cac_phan))


def tach_lai(apps, schema_editor):
    """Lùi migration: tách khung nội dung về sáu ô theo các tiêu đề <h3> do chính migration này sinh.

    Phần đứng trước tiêu đề đầu tiên, hoặc đoạn có tiêu đề lạ do quản trị tự viết, được nối vào ô
    công dụng để không mất chữ. Ô bảo quản trước đây là văn bản một dòng nên được bỏ thẻ HTML.
    """
    import re

    Thuoc = apps.get_model("danh_muc", "Thuoc")
    theo_tieu_de = {tieu_de: ten for ten, tieu_de in TIEU_DE_MUC}
    for thuoc in Thuoc.objects.exclude(noi_dung_chi_tiet=""):
        cac_o = {ten: "" for ten, _ in TIEU_DE_MUC}
        phan = re.split(r"(?=<h3>)", thuoc.noi_dung_chi_tiet)
        for doan in phan:
            khop = re.match(r"<h3>(.*?)</h3>(.*)", doan, re.S)
            ten = theo_tieu_de.get(khop.group(1)) if khop else None
            if ten:
                cac_o[ten] += khop.group(2)
            else:
                cac_o["cong_dung"] += doan
        cac_o["bao_quan"] = re.sub(r"<[^>]+>", " ", cac_o["bao_quan"]).strip()
        cac_o["bao_quan"] = " ".join(cac_o["bao_quan"].split())
        Thuoc.objects.filter(pk=thuoc.pk).update(**cac_o)


class Migration(migrations.Migration):
    dependencies = [("danh_muc", "0010_noi_dung_mot_khung_va_nguon_anh")]
    operations = [migrations.RunPython(gop_noi_dung, tach_lai)]
