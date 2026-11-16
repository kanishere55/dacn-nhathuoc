"""Luồng đặt giữ qua giao diện: giỏ → chọn chi nhánh → giữ hàng → nhân viên giao tại quầy."""

from datetime import timedelta

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ung_dung.kho.tests.du_lieu import tao_du_lieu, tao_ton

from ..models import DonHang, LichSuDonHang, PhieuBan


class DatHangWebTests(TestCase):
    def setUp(self):
        self.d = tao_du_lieu()
        tao_ton(self.d, ngay=60, luong=30)
        self.client.force_login(self.d.khach)

    def them_gio(self, so_luong=2):
        return self.client.post(
            reverse("ban_hang:gio_hang_them", args=[self.d.thuoc.ma_thuoc]),
            {"so_luong": so_luong},
        )

    def dat_giu(self, **them):
        return self.client.post(reverse("ban_hang:dat_hang"), {"chi_nhanh": self.d.cn.pk, **them})

    def test_gio_hang_them_sua_xoa(self):
        self.them_gio(2)
        self.them_gio(3)
        phan_hoi = self.client.get(reverse("ban_hang:gio_hang"))
        self.assertContains(phan_hoi, self.d.thuoc.ten_thuoc)
        self.assertContains(phan_hoi, "10.000 đ")
        self.assertNotContains(phan_hoi, "Phí giao hàng")
        self.client.post(reverse("ban_hang:gio_hang_sua", args=[self.d.thuoc.pk]), {"so_luong": 1})
        self.assertContains(self.client.get(reverse("ban_hang:gio_hang")), "2.000 đ")
        self.client.post(reverse("ban_hang:gio_hang_sua", args=[self.d.thuoc.pk]), {"so_luong": 0})
        self.assertNotContains(self.client.get(reverse("ban_hang:gio_hang")), "2.000 đ")

    def test_cap_nhat_lua_chon_chi_tra_khoi_va_khong_tao_don(self):
        self.them_gio()
        url = reverse("ban_hang:dat_hang")
        lua_chon = {"chi_nhanh": self.d.cn.pk}
        phan_hoi = self.client.get(url, lua_chon, headers={"HX-Request": "true"})
        self.assertEqual(phan_hoi.headers["X-Khoi-Dat-Hang"], "lua-chon")
        self.assertIn("HX-Request", phan_hoi.headers["Vary"])
        self.assertContains(phan_hoi, 'id="lua-chon-dat-hang"')
        self.assertContains(phan_hoi, "Chọn nhà thuốc nhận hàng")
        self.assertNotContains(phan_hoi, 'id="form-dat-hang"')
        self.assertNotContains(phan_hoi, "giao hàng")

        phan_hoi = self.client.post(url, {**lua_chon, "cap_nhat": "1", "ghi_chu_khach": "Lời nhắn"})
        self.assertContains(phan_hoi, 'id="form-dat-hang"')
        self.assertContains(phan_hoi, 'value="Lời nhắn"')
        self.assertFalse(DonHang.objects.exists())

    def test_dat_giu_tao_don_giu_24_gio_va_trang_nhan_hang(self):
        self.d.khach.email = "khach@example.com"
        self.d.khach.save()
        self.them_gio(2)
        with self.captureOnCommitCallbacks(execute=True):
            phan_hoi = self.dat_giu(ghi_chu_khach="Khoảng 18 giờ tôi ghé")
        don = DonHang.objects.get()
        self.assertRedirects(phan_hoi, reverse("ban_hang:khach_don_hang_chi_tiet", args=[don.pk]))
        self.assertEqual((don.trang_thai, don.chi_nhanh), ("dang_giu", self.d.cn))
        self.assertAlmostEqual(
            (don.thoi_diem_het_giu - don.thoi_diem_tao).total_seconds(), 24 * 3600, delta=5
        )
        self.assertEqual(don.tong_thanh_toan, 4000)
        self.assertEqual(don.ghi_chu_khach, "Khoảng 18 giờ tôi ghé")
        self.assertFalse(self.client.session.get("gio_hang"))
        self.assertEqual(mail.outbox[-1].to, ["khach@example.com"])
        self.assertIn(don.ma_don_hang, mail.outbox[-1].subject)
        trang = self.client.get(reverse("ban_hang:khach_don_hang_chi_tiet", args=[don.pk]))
        self.assertContains(trang, "ĐỌC MÃ NÀY TẠI QUẦY")
        self.assertContains(trang, don.ma_don_hang)
        self.assertContains(trang, "Trả tại quầy khi nhận hàng")

    def test_vi_tri_khach_sap_chi_nhanh_gan_truoc(self):
        tao_ton(self.d, "LO2", ngay=60, luong=30, chi_nhanh=self.d.cn2)
        self.them_gio(1)
        # Đứng sát chi nhánh hai: chi nhánh hai lên đầu và được chọn sẵn.
        phan_hoi = self.client.get(
            reverse("ban_hang:dat_hang"),
            {"vi_do": 10.7801, "kinh_do": 106.7101},
            headers={"HX-Request": "true"},
        )
        noi_dung = phan_hoi.content.decode()
        self.assertLess(noi_dung.index("Chi nhánh hai"), noi_dung.index("Chi nhánh một"))
        self.assertContains(phan_hoi, "Gần bạn nhất")
        self.assertContains(phan_hoi, "Cách bạn")
        self.assertContains(phan_hoi, f'value="{self.d.cn2.pk}" data-tai-lai checked')

    def test_vi_tri_go_dia_chi_giu_lai_khi_doi_chi_nhanh(self):
        tao_ton(self.d, "LO2", ngay=60, luong=30, chi_nhanh=self.d.cn2)
        self.them_gio(1)
        # Khách gõ địa chỉ rồi đổi sang chi nhánh xa hơn: vị trí và nhãn địa chỉ vẫn còn trong form.
        phan_hoi = self.client.get(
            reverse("ban_hang:dat_hang"),
            {
                "chi_nhanh": self.d.cn.pk,
                "vi_do": 10.7801,
                "kinh_do": 106.7101,
                "nhan_vi_tri": "Chợ Bến Thành",
            },
            headers={"HX-Request": "true"},
        )
        self.assertContains(phan_hoi, "Đã sắp theo khoảng cách từ <strong>Chợ Bến Thành</strong>")
        self.assertContains(phan_hoi, 'name="vi_do" value="10.780100"')
        self.assertContains(phan_hoi, 'name="nhan_vi_tri" value="Chợ Bến Thành"')
        self.assertContains(phan_hoi, f'value="{self.d.cn.pk}" data-tai-lai checked')
        self.assertContains(phan_hoi, "data-mo-ban-do-dat-hang open")

    def test_chi_nhanh_khong_du_hang_khong_hien(self):
        self.them_gio(1)
        phan_hoi = self.client.get(reverse("ban_hang:dat_hang"))
        self.assertContains(phan_hoi, "Chi nhánh một")
        self.assertNotContains(phan_hoi, "Chi nhánh hai")

    def test_thuoc_ke_don_ghi_don_thuoc_khi_giao_tai_quay(self):
        self.d.thuoc.la_thuoc_ke_don = True
        self.d.thuoc.save()
        self.them_gio(1)
        self.assertContains(self.client.get(reverse("ban_hang:dat_hang")), "mang theo đơn thuốc")
        self.dat_giu()
        don = DonHang.objects.get()
        self.assertEqual(don.trang_thai, "dang_giu")

        self.client.force_login(self.d.ql)
        url = reverse("ban_hang:don_hang_xu_ly", args=[don.pk, "nhan_tai_quay"])
        trang = self.client.get(reverse("ban_hang:don_hang_chi_tiet", args=[don.pk]))
        self.assertContains(trang, "Bác sĩ kê đơn")
        self.client.post(url, {"da_kiem_tra_don_thuoc": "on"})
        self.assertFalse(PhieuBan.objects.exists())
        self.client.post(
            url,
            {
                "da_kiem_tra_don_thuoc": "on",
                "ten_nguoi_ke_don": "BS. Lê Minh",
                "noi_kham_benh": "Bệnh viện Nhân dân 115",
                "ho_ten_nguoi_benh": "Nguyễn Văn An",
                "ngay_ke_don": timezone.localdate().isoformat(),
                "phuong_thuc_thanh_toan": "chuyen_khoan",
            },
        )
        phieu = PhieuBan.objects.get()
        don.refresh_from_db()
        self.assertEqual(don.trang_thai, "hoan_thanh")
        self.assertEqual(phieu.noi_kham_benh, "Bệnh viện Nhân dân 115")
        self.assertEqual(phieu.phuong_thuc_thanh_toan, "chuyen_khoan")

    def test_chi_nhanh_khong_hop_le_khong_tu_doi_khi_dat(self):
        self.them_gio(1)
        phan_hoi = self.client.post(reverse("ban_hang:dat_hang"), {"chi_nhanh": 999999999})
        self.assertContains(phan_hoi, "Chi nhánh đã chọn không còn đủ hàng")
        self.assertFalse(DonHang.objects.exists())

    def test_tong_tien_doi_phai_xac_nhan_lai(self):
        self.them_gio(1)
        lua_chon = {"chi_nhanh": self.d.cn.pk}
        url = reverse("ban_hang:dat_hang")
        self.assertContains(self.client.get(url, lua_chon), 'name="tong_da_xem" value="2000"')
        self.d.thuoc.gia_ban = 2500
        self.d.thuoc.save(update_fields=["gia_ban"])
        phan_hoi = self.client.post(url, {**lua_chon, "tong_da_xem": 2000})
        self.assertContains(phan_hoi, "Tổng tiền vừa thay đổi")
        self.assertContains(phan_hoi, 'name="tong_da_xem" value="2500"')
        self.assertFalse(DonHang.objects.exists())
        self.assertTrue(self.client.session.get("gio_hang"))
        self.assertEqual(self.client.post(url, {**lua_chon, "tong_da_xem": 2500}).status_code, 302)
        self.assertEqual(DonHang.objects.get().tong_thanh_toan, 2500)

    def test_khach_huy_don_dang_giu_va_lich_su(self):
        self.them_gio(1)
        self.dat_giu()
        don = DonHang.objects.get()
        self.client.force_login(self.d.khac)
        self.client.post(reverse("ban_hang:khach_don_hang_huy", args=[don.pk]))
        don.refresh_from_db()
        self.assertEqual(don.trang_thai, "dang_giu")
        self.client.force_login(self.d.khach)
        self.client.post(reverse("ban_hang:khach_don_hang_huy", args=[don.pk]))
        don.refresh_from_db()
        self.assertEqual(don.trang_thai, "da_huy")
        self.assertEqual(
            list(
                LichSuDonHang.objects.filter(don_hang=don).values_list("den_trang_thai", flat=True)
            ),
            ["dang_giu", "da_huy"],
        )

    def test_nhan_vien_giao_don_tai_quay_va_khoa_chi_nhanh_khac(self):
        self.them_gio(2)
        self.dat_giu()
        don = DonHang.objects.get()
        # Nhân viên chi nhánh khác không thấy và không xử lý được đơn.
        self.client.force_login(self.d.ql2)
        self.assertEqual(
            self.client.get(reverse("ban_hang:don_hang_chi_tiet", args=[don.pk])).status_code, 404
        )
        self.client.force_login(self.d.nv)
        danh_sach = self.client.get(reverse("ban_hang:don_hang_danh_sach"), {"q": don.ma_don_hang})
        self.assertContains(danh_sach, don.ma_don_hang)
        trang = self.client.get(reverse("ban_hang:don_hang_chi_tiet", args=[don.pk]))
        self.assertContains(trang, "Giao thuốc và thu tiền")
        self.client.post(
            reverse("ban_hang:don_hang_xu_ly", args=[don.pk, "nhan_tai_quay"]),
            {"phuong_thuc_thanh_toan": "tien_mat"},
        )
        don.refresh_from_db()
        self.assertEqual(don.trang_thai, "hoan_thanh")
        phieu = PhieuBan.objects.get(don_hang=don)
        self.assertEqual((phieu.phuong_thuc_thanh_toan, phieu.nguoi_lap), ("tien_mat", self.d.nv))
        # Giao xong thì không còn nút giao lần nữa.
        trang = self.client.get(reverse("ban_hang:don_hang_chi_tiet", args=[don.pk]))
        self.assertNotContains(trang, "Giao thuốc và thu tiền")
        self.client.force_login(self.d.khach)
        trang = self.client.get(reverse("ban_hang:khach_don_hang_chi_tiet", args=[don.pk]))
        self.assertContains(trang, "Xem phiếu bán hàng")
        self.assertContains(trang, "Đã thanh toán tại quầy")

    def test_qua_han_giu_khong_giao_duoc_va_chuyen_het_han(self):
        from ..services.don_hang import xu_ly_qua_han

        self.them_gio(1)
        self.dat_giu()
        don = DonHang.objects.get()
        DonHang.objects.filter(pk=don.pk).update(
            thoi_diem_tao=timezone.now() - timedelta(hours=25),
            thoi_diem_het_giu=timezone.now() - timedelta(minutes=1),
        )
        self.client.force_login(self.d.nv)
        trang = self.client.get(reverse("ban_hang:don_hang_chi_tiet", args=[don.pk]))
        self.assertContains(trang, "lập phiếu bán tại quầy")
        self.assertNotContains(trang, "Giao thuốc và thu tiền")
        self.client.post(reverse("ban_hang:don_hang_xu_ly", args=[don.pk, "nhan_tai_quay"]))
        self.assertFalse(PhieuBan.objects.exists())
        self.assertEqual(xu_ly_qua_han(), 1)
        don.refresh_from_db()
        self.assertEqual(don.trang_thai, "het_han")


class HoaDonTests(TestCase):
    def setUp(self):
        self.d = tao_du_lieu()
        self.d.khach.email = "khach@example.com"
        self.d.khach.save()
        tao_ton(self.d, "L01", ngay=40, luong=3)
        tao_ton(self.d, "L02", ngay=200, luong=30)

    def test_hoa_don_don_dat_giu_giao_tai_quay(self):
        from ..hoa_don import du_lieu_hoa_don, ve_pdf
        from ..services.dat_hang import dat_giu
        from ..services.phieu_ban import ban_tai_quay

        don = dat_giu(self.d.khach, self.d.cn, [{"thuoc": self.d.thuoc, "so_luong": 5}])
        self.client.force_login(self.d.khach)
        url = reverse("ban_hang:khach_hoa_don_in", args=[don.pk])
        self.assertEqual(self.client.get(url).status_code, 404)  # chưa nhận hàng
        mail.outbox.clear()
        with self.captureOnCommitCallbacks(execute=True):
            phieu = ban_tai_quay(
                self.d.nv, self.d.cn, [], don_hang=don, phuong_thuc_thanh_toan="chuyen_khoan"
            )
        hd = du_lieu_hoa_don(phieu)
        self.assertEqual(
            [(lo["ma"], lo["so_luong"]) for lo in hd["cac_dong"][0]["cac_lo"]],
            [("L01", 3), ("L02", 2)],
        )
        self.assertEqual(hd["tong"]["tong"], 10000)
        self.assertEqual(hd["bang_chu"], "Mười nghìn đồng")
        self.assertEqual(hd["da_thu"]["phuong_thuc"], "Chuyển khoản")
        self.assertTrue(ve_pdf(hd).startswith(b"%PDF"))
        self.assertEqual(mail.outbox[-1].attachments[0][2], "application/pdf")

        phan_hoi = self.client.get(url)
        self.assertContains(phan_hoi, "Mười nghìn đồng")
        self.assertContains(phan_hoi, "Lô L01")
        self.assertContains(phan_hoi, "Đã thu tại quầy")
        pdf = self.client.get(reverse("ban_hang:khach_hoa_don_pdf", args=[don.pk]) + "?tai=1")
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertIn("attachment", pdf["Content-Disposition"])
        self.client.force_login(self.d.khac)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_hoa_don_ban_tai_quay_cho_nhan_vien(self):
        from ..services.phieu_ban import ban_tai_quay

        phieu = ban_tai_quay(self.d.nv, self.d.cn, [{"thuoc": self.d.thuoc, "so_luong": 2}])
        self.client.force_login(self.d.nv)
        for ten in ("ban_hang:phieu_ban_chi_tiet", "ban_hang:phieu_ban_in"):
            phan_hoi = self.client.get(reverse(ten, args=[phieu.pk]))
            self.assertContains(phan_hoi, "Khách mua tại quầy")
            self.assertContains(phan_hoi, "Bốn nghìn đồng")
        self.client.force_login(self.d.ql2)
        self.assertEqual(
            self.client.get(reverse("ban_hang:phieu_ban_pdf", args=[phieu.pk])).status_code, 404
        )


class HangThanhVienTests(TestCase):
    def test_hang_theo_chi_tieu_va_uu_dai_chi_cho_thuoc_khong_ke_don(self):
        from ..services.dat_hang import dat_giu
        from ..thanh_vien import hang_cua

        d = tao_du_lieu()
        tao_ton(d, luong=500)
        self.assertEqual(hang_cua(d.khach)["ten"], "Thành viên")
        cu = dat_giu(d.khach, d.cn, [{"thuoc": d.thuoc, "so_luong": 1}])
        DonHang.objects.filter(pk=cu.pk).update(
            trang_thai="hoan_thanh", tien_hang=3_200_000, tong_thanh_toan=3_200_000
        )
        cu.cac_dong.update(gia_niem_yet=3_200_000, don_gia=3_200_000)
        hang = hang_cua(d.khach)
        self.assertEqual((hang["ten"], hang["phan_tram"], hang["hang_sau"]), ("Bạc", 3, "Vàng"))
        don = dat_giu(d.khach, d.cn, [{"thuoc": d.thuoc, "so_luong": 100}])
        self.assertEqual(
            (don.tien_hang, don.giam_gia_thanh_vien, don.tong_thanh_toan), (200000, 6000, 194000)
        )
        self.client.force_login(d.khach)
        self.assertContains(self.client.get(reverse("tai_khoan:cua_toi")), "Bạc")
        d.thuoc.la_thuoc_ke_don = True
        d.thuoc.save()
        don_ke_don = dat_giu(d.khach, d.cn, [{"thuoc": d.thuoc, "so_luong": 10}])
        self.assertEqual(hang_cua(d.khach)["ten"], "Thành viên")
        self.assertEqual(don_ke_don.giam_gia_thanh_vien, 0)
        self.assertTrue(LichSuDonHang.objects.exists())
