# Cơ sở dữ liệu

Hệ thống dùng **PostgreSQL 18** với **PostGIS 3.6**, gồm 54 bảng nghiệp vụ và 6 bảng hệ thống của Django (`auth_*`, `django_*`). Toàn bộ dữ liệu, kể cả ảnh (`bytea`), phiên đăng nhập, tin nhắn và kết quả dự báo, được lưu trong CSDL; thư mục mã nguồn không chứa tệp dữ liệu.

## Tệp trong thư mục

| Tệp | Nội dung |
| --- | --- |
| [`tao_csdl.sql`](tao_csdl.sql) | Tạo vai trò `dacn_ung_dung`, CSDL `dacn_nhathuoc_nop` và extension PostGIS |
| [`cau_truc_csdl.sql`](cau_truc_csdl.sql) | Toàn bộ cấu trúc: bảng, khóa, ràng buộc, chỉ mục, hàm, trigger và chú thích (không có dữ liệu) |
| [`khoi_tao_csdl_windows.ps1`](khoi_tao_csdl_windows.ps1) | Khởi tạo trọn gói trên Windows: CSDL, `.env`, Redis, migrate, dữ liệu mẫu, chạy web |

## Khởi tạo

Cấu trúc bảng do migration Django trong `dacn_qlcnt/ung_dung/*/migrations/` tạo ra; `cau_truc_csdl.sql` là bản xuất của kết quả đó để tra cứu.

**Trên Windows** (PostgreSQL 18 cài bằng bộ cài chính thức, đã tạo `dacn_qlcnt\.venv` theo [README](../README.md)), chạy từ thư mục gốc của repo:

```powershell
powershell -ExecutionPolicy Bypass -File csdl\khoi_tao_csdl_windows.ps1
```

Script cần quyền Administrator, hỏi mật khẩu tài khoản `postgres`, chỉ tạo phần còn thiếu và không xóa dữ liệu đang có.

**Thủ công:**

```powershell
psql -U postgres -f csdl\tao_csdl.sql
cd dacn_qlcnt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py kiem_tra_csdl
```

`kiem_tra_csdl` đối chiếu CSDL đang dùng với quy ước bên dưới và phải báo 0 lỗi, 0 cảnh báo.

## Quy ước thiết kế

- Tên bảng, cột, ràng buộc, chỉ mục bằng tiếng Việt không dấu, dạng `snake_case`; mỗi bảng và cột nghiệp vụ có chú thích tiếng Việt (`COMMENT ON`).
- Khóa chính đặt theo tên bảng (`id_thuoc`, `id_phieu_nhap`...), không dùng tên chung `id`.
- Ràng buộc nằm ngay trong CSDL: 511 `CHECK`, 84 khóa ngoại, 53 `UNIQUE`, 75 chỉ mục. Lượng hàng là số nguyên theo đơn vị cơ sở, tiền là VND nguyên.
- Chứng từ kho đã xác nhận không sửa, không xóa: trigger gọi hàm `chan_sua_chung_tu_kho` chặn ở mức CSDL. Thuốc đã có lô không đổi được đơn vị cơ sở, lô đã có tồn không đổi được mã.
- Vị trí chi nhánh lưu bằng `GEOGRAPHY(Point, 4326)`; tìm nhà thuốc gần dùng `ST_DWithin`, `ST_Distance`.

## Danh sách bảng

### Tài khoản và phân quyền (`tai_khoan`, 5 bảng)

| Bảng | Mô tả |
| --- | --- |
| `tai_khoan` | Mỗi hàng là một tài khoản xác thực có một vai trò nghiệp vụ. |
| `nhom_quyen` | Mỗi hàng là một nhóm quyền có thể gán cho nhiều tài khoản nội bộ. |
| `quyen_cua_nhom` | Mỗi hàng là một quyền mà một nhóm quyền được thực hiện. |
| `quyen_rieng_tai_khoan` | Mỗi hàng là một quyền được cho thêm hoặc chặn riêng cho một tài khoản. |
| `phien_xac_thuc` | Mỗi hàng là một phiên gửi mã OTP qua email cho một mục đích. |

### Danh mục (`danh_muc`, 14 bảng)

| Bảng | Mô tả |
| --- | --- |
| `chi_nhanh` | Mỗi hàng là một chi nhánh trong chuỗi mô phỏng. |
| `nhan_vien` | Mỗi hàng là hồ sơ nhân viên, phạm vi làm việc lấy từ tài khoản. |
| `nha_cung_cap` | Mỗi hàng là một đối tác cung cấp thuốc. |
| `thuoc` | Mỗi hàng là một sản phẩm thuốc dùng chung toàn chuỗi. |
| `nhom_atc` | Mỗi hàng là một mã phân nhóm ATC, không biểu thị khả năng thay thế thuốc. |
| `don_vi_tinh` | Mỗi hàng là một đơn vị cơ sở có cùng nghĩa trong hệ thống. |
| `quy_doi_bao_goi` | Mỗi hàng là một bao gói quy đổi của riêng một thuốc. |
| `danh_muc_san_pham` | Mỗi hàng là một nhóm sản phẩm khách dùng để duyệt website. |
| `khuyen_mai` | Mỗi hàng là một đợt giảm giá theo phần trăm cho một thuốc; service không cho hai đợt đang hoạt động của cùng thuốc trùng ngày. |
| `anh_thuoc` | Mỗi hàng là một ảnh sản phẩm của thuốc, lưu bytea. |
| `anh_chi_nhanh` | Mỗi hàng là một ảnh mặt tiền hoặc bên trong nhà thuốc, lưu bytea. |
| `anh_noi_dung` | Mỗi hàng là một ảnh chèn trong nội dung soạn thảo (mô tả thuốc, giới thiệu chi nhánh), lưu bytea. |
| `danh_gia_thuoc` | Mỗi hàng là đánh giá của một khách cho một thuốc đã mua. |
| `danh_gia_chi_nhanh` | Mỗi hàng là đánh giá của một khách cho một chi nhánh đã mua hàng. |

### Kho (`kho`, 13 bảng)

| Bảng | Mô tả |
| --- | --- |
| `lo_thuoc` | Mỗi hàng là một lô của một thuốc, dùng chung giữa các chi nhánh. |
| `ton_kho` | Mỗi hàng là số dư vật lý của một lô tại một chi nhánh. |
| `lich_su_dieu_kien_lo` | Mỗi hàng là một lần khóa hoặc mở bán một lô; chỉ thêm, không sửa hoặc xóa. |
| `phieu_nhap` | Mỗi hàng là một chứng từ đã xác nhận, không sửa hoặc xóa. |
| `chi_tiet_phieu_nhap` | Mỗi hàng là lượng nhập của một lô trong phiếu nhập. |
| `phieu_tra_nha_cung_cap` | Mỗi hàng là một chứng từ đã xác nhận, không sửa hoặc xóa. |
| `chi_tiet_phieu_tra_nha_cung_cap` | Mỗi hàng là lượng trả của một lô đã nhập trong phiếu gốc. |
| `phieu_dieu_chuyen` | Mỗi hàng là một chứng từ đã xác nhận, không sửa hoặc xóa. |
| `chi_tiet_phieu_dieu_chuyen` | Mỗi hàng là lượng một lô đã chuyển giữa hai chi nhánh. |
| `phieu_kiem_ke` | Mỗi hàng là một chứng từ đã xác nhận, không sửa hoặc xóa. |
| `chi_tiet_phieu_kiem_ke` | Mỗi hàng là kết quả đếm một lô và số dư được đối chiếu trong giao dịch. |
| `phieu_xuat_huy` | Mỗi hàng là một chứng từ xuất hủy đã xác nhận, không sửa hoặc xóa. |
| `chi_tiet_phieu_xuat_huy` | Mỗi hàng là lượng một lô bị hủy trong phiếu xuất hủy. |

### Bán hàng và đặt giữ (`ban_hang`, 8 bảng)

| Bảng | Mô tả |
| --- | --- |
| `don_hang` | Mỗi hàng là một đơn đặt giữ của khách ở một chi nhánh; khách nhận và trả tiền tại quầy. |
| `chi_tiet_don_hang` | Mỗi hàng là một thuốc trong đơn, kèm giá chụp lúc đặt. |
| `phan_bo_don_hang` | Mỗi hàng là lượng một dòng đơn giữ trên hàng tồn của một lô theo FEFO; chỉ tính khi đơn ở trạng thái giữ và chưa quá hạn. |
| `lich_su_don_hang` | Mỗi hàng là một lần đơn đổi trạng thái; không sửa, không xóa. |
| `phieu_ban` | Mỗi hàng là một lần bán tại quầy kèm xuất kho: bán trực tiếp hoặc giao đơn đặt giữ cho khách đến nhận. |
| `chi_tiet_phieu_ban` | Mỗi hàng là một thuốc đã bán với giá và tên chụp tại quầy. |
| `phan_bo_phieu_ban` | Mỗi hàng là lượng thực xuất của một dòng bán từ một lô. |
| `yeu_cau_xuat_hoa_don` | Mỗi hàng là yêu cầu hóa đơn doanh nghiệp cho một đơn; hóa đơn điện tử phát hành ngoài hệ thống. |

### Trò chuyện (`tro_chuyen`, 3 bảng)

| Bảng | Mô tả |
| --- | --- |
| `cuoc_tro_chuyen` | Mỗi hàng là cuộc trò chuyện duy nhất của một khách với một chi nhánh, giữ toàn bộ lịch sử hỏi tư vấn, sản phẩm và đơn hàng. |
| `tin_nhan` | Mỗi hàng là tin đã được ghi bền vững trước khi phát Redis. |
| `anh_tin_nhan` | Mỗi hàng là một ảnh gửi kèm tin nhắn trò chuyện, lưu bytea. |

### Dự báo (`du_bao`, 6 bảng)

| Bảng | Mô tả |
| --- | --- |
| `nguon_du_lieu` | Mỗi hàng là một phiên bản dữ liệu Pharma Sales công khai đã nạp vào DB. |
| `quan_sat_ban_hang` | Mỗi hàng là một quan sát ngày/ATC của dữ liệu công khai, không thuộc chi nhánh mô phỏng. |
| `lan_thuc_nghiem` | Mỗi hàng là lần thực nghiệm với dữ liệu và các mốc chia theo thời gian. |
| `ket_qua_mo_hinh` | Mỗi hàng là sai số của một trong năm mô hình theo nhóm ATC. |
| `du_bao_bay_ngay` | Mỗi hàng là tổng lượng dự báo bảy ngày sau một ngày gốc, có đối chiếu khi đã có nhãn. |
| `kich_ban_thieu_hang` | Mỗi hàng là kịch bản minh họa riêng theo đơn vị dữ liệu công khai; không tác động kho mô phỏng. |

### Nội dung website (`noi_dung`, 4 bảng)

| Bảng | Mô tả |
| --- | --- |
| `thong_tin_cua_hang` | Một hàng duy nhất chứa thông tin liên hệ chung của chuỗi nhà thuốc. |
| `trang_noi_dung` | Mỗi hàng là một trang thông tin: giới thiệu, chính sách, hướng dẫn. |
| `banner_trang_chu` | Mỗi hàng là một banner trong băng chuyền đầu trang chủ, ảnh lưu bytea. |
| `tin_tuc` | Mỗi hàng là một bài tin tức, khuyến cáo sức khỏe của chuỗi nhà thuốc. |

### Thông báo (`thong_bao`, 1 bảng)

| Bảng | Mô tả |
| --- | --- |
| `nhat_ky_email` | Mỗi hàng là một email hệ thống đã tạo, kèm kết quả gửi. |

## Xuất lại cấu trúc

Sau khi đổi model và chạy migration, xuất lại `cau_truc_csdl.sql` từ thư mục gốc của repo:

```powershell
pg_dump -h 127.0.0.1 -U dacn_ung_dung -d dacn_nhathuoc_nop --schema-only --no-owner --no-privileges -f csdl\cau_truc_csdl.sql
```

Sau khi xuất, xóa hai dòng `\restrict` và `\unrestrict` mà pg_dump 18 thêm vào đầu và cuối tệp.
