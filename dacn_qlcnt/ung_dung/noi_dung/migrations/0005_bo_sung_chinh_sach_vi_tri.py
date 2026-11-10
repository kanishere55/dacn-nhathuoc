from django.db import migrations
from django.utils import timezone

TIEU_DE = "<h2>Vị trí và dịch vụ bản đồ</h2>"
THONG_BAO = (
    TIEU_DE + "<p>Khi tính quãng đường và phí giao hàng, website gửi tọa độ điểm giao và chi nhánh "
    "đến dịch vụ định tuyến OSRM. Khi bạn yêu cầu chỉ đường, OSRM nhận tọa độ điểm xuất phát và "
    "điểm đến. Máy chủ định tuyến có thể lưu yêu cầu trong nhật ký vận hành.</p>"
)
CHIA_SE_CU = (
    "<p>Chúng tôi không bán dữ liệu. Thông tin chỉ chuyển cho đơn vị giao hàng và cổng thanh toán "
    "ở mức cần thiết để hoàn tất đơn, hoặc khi cơ quan nhà nước có thẩm quyền yêu cầu.</p>"
)
CHIA_SE_MOI = CHIA_SE_CU.replace("chỉ chuyển", "được chuyển") + THONG_BAO


def _chinh_sach(apps, schema_editor):
    TrangNoiDung = apps.get_model("noi_dung", "TrangNoiDung")
    return TrangNoiDung.objects.using(schema_editor.connection.alias).filter(
        duong_dan_trang="chinh-sach-bao-mat"
    )


def them_thong_bao(apps, schema_editor):
    chinh_sach = _chinh_sach(apps, schema_editor)
    for trang in chinh_sach:
        noi_dung = trang.noi_dung_trang
        if TIEU_DE in noi_dung:
            continue
        moi = (
            noi_dung.replace(CHIA_SE_CU, CHIA_SE_MOI, 1)
            if CHIA_SE_CU in noi_dung
            else noi_dung + THONG_BAO
        )
        chinh_sach.filter(pk=trang.pk).update(noi_dung_trang=moi, thoi_diem_cap_nhat=timezone.now())


def go_thong_bao(apps, schema_editor):
    chinh_sach = _chinh_sach(apps, schema_editor)
    for trang in chinh_sach:
        noi_dung = trang.noi_dung_trang
        cu = noi_dung.replace(CHIA_SE_MOI, CHIA_SE_CU, 1)
        if cu == noi_dung:
            cu = noi_dung.removesuffix(THONG_BAO)
        if cu != noi_dung:
            chinh_sach.filter(pk=trang.pk).update(
                noi_dung_trang=cu, thoi_diem_cap_nhat=timezone.now()
            )


class Migration(migrations.Migration):
    dependencies = [("noi_dung", "0004_chuan_hoa_ten_csdl")]
    operations = [migrations.RunPython(them_thong_bao, go_thong_bao)]
