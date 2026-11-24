# Hệ thống quản lý chuỗi nhà thuốc tích hợp WebGIS

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-6.1-092E20?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18%20%2B%20PostGIS-4169E1?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-channel%20layer-DC382D?logo=redis&logoColor=white)
![Leaflet](https://img.shields.io/badge/Leaflet-WebGIS-199900?logo=leaflet&logoColor=white)

Ứng dụng web quản lý chuỗi nhà thuốc gồm hai phần dùng chung một tầng nghiệp vụ:

- **Website khách hàng**: tra cứu thuốc, tìm nhà thuốc gần nhất còn đủ hàng trên bản đồ, đặt giữ thuốc rồi nhận và thanh toán tại quầy, trò chuyện với dược sĩ.
- **Khu quản lý** (`/quan-ly/`): bán tại quầy, quản lý kho theo lô, danh mục, báo cáo, bản đồ nhiệt tồn kho và dự báo nhu cầu thuốc.

## Cấu trúc repo

```text
.
├── dacn_qlcnt/                 # Mã nguồn (Django)
│   ├── cau_hinh/               # settings, urls, asgi/wsgi
│   ├── ung_dung/               # Các phân hệ nghiệp vụ
│   │   ├── chung/              # Thành phần dùng chung, kiểm tra quy ước CSDL và lưu trữ
│   │   ├── tai_khoan/          # Đăng ký, đăng nhập, OTP, vai trò và phân quyền
│   │   ├── danh_muc/           # Thuốc, danh mục, chi nhánh, nhà cung cấp, ảnh
│   │   ├── kho/                # Lô thuốc, chứng từ kho, tồn kho, cảnh báo
│   │   ├── ban_hang/           # Giỏ hàng, đặt giữ, bán tại quầy, phiếu bán
│   │   ├── webgis/             # Tìm nhà thuốc, lộ trình, bản đồ nhiệt
│   │   ├── tro_chuyen/         # Trò chuyện thời gian thực
│   │   ├── du_bao/             # Nạp dữ liệu và kết quả dự báo
│   │   ├── bao_cao/            # Báo cáo vận hành
│   │   ├── thong_bao/          # Email
│   │   └── noi_dung/           # Banner, trang thông tin, tin tức
│   ├── thuc_nghiem_du_bao/     # Mã thực nghiệm 5 mô hình dự báo
│   ├── templates/              # Template dùng chung
│   ├── static/                 # CSS và thư viện giao diện cục bộ
│   ├── cong_cu/                # Chạy kiểm thử trên PostgreSQL tạm, tải thư viện giao diện
│   ├── .env.example            # Mẫu cấu hình
│   ├── chay_web.bat            # Chạy nhanh trên Windows
│   ├── manage.py
│   ├── pyproject.toml
│   └── requirements.txt
├── csdl/                       # Cơ sở dữ liệu
│   ├── README.md               # Mô tả CSDL, quy ước và danh sách bảng
│   ├── tao_csdl.sql            # Tạo vai trò, CSDL và PostGIS
│   ├── cau_truc_csdl.sql       # Toàn bộ cấu trúc bảng, ràng buộc, chỉ mục, trigger
│   └── khoi_tao_csdl_windows.ps1
└── README.md
```

Mỗi phân hệ tách tầng rõ ràng: `models` (dữ liệu và ràng buộc), `selectors` (truy vấn chỉ đọc), `services` (nghiệp vụ ghi trong giao dịch), `views`, `forms`, `templates` và `tests`.

## Tính năng

### Website khách hàng

- Tra cứu thuốc theo danh mục; trang thuốc có hoạt chất, quy cách, công dụng, liều dùng, chống chỉ định và bộ ảnh trượt.
- Bản đồ WebGIS tìm nhà thuốc còn đủ toàn bộ thuốc trong giỏ, sắp theo quãng đường đi thực tế (OSRM) kèm thời gian di chuyển và chỉ đường. Vị trí lấy từ định vị, ô nhập địa chỉ hoặc chạm lên bản đồ.
- Đặt giữ thuốc tại một chi nhánh trong 24 giờ: đơn chỉ được xác nhận khi chi nhánh đủ hàng, hàng được giữ theo lô FEFO còn hạn; phiếu nhận hàng có mã đơn để đọc tại quầy.
- Theo dõi và hủy đơn, xem và tải phiếu bán hàng PDF sau khi nhận, yêu cầu hóa đơn công ty.
- Đánh giá thuốc và chi nhánh đã mua, hạng thành viên theo chi tiêu 12 tháng, tin tức.
- Trò chuyện thời gian thực với dược sĩ của từng chi nhánh, gắn thẻ sản phẩm hoặc đơn hàng và gửi ảnh.

### Khu quản lý

- Bốn vai trò: quản trị chuỗi, quản lý chi nhánh, nhân viên và khách hàng; phân quyền chi tiết theo nhóm quyền và phạm vi chi nhánh.
- Bán tại quầy dạng POS (xuất kho FEFO), giao đơn đặt giữ, ghi thông tin đơn thuốc khi bán thuốc kê đơn, in phiếu bán khổ A4 và tải PDF.
- Kho theo lô: phiếu nhập (nhập tay hoặc từ Excel có xem trước), trả nhà cung cấp, điều chuyển giữa chi nhánh, kiểm kê, xuất hủy hàng hết hạn hoặc hư hỏng, khóa bán lô; mọi chứng từ có trang chi tiết và PDF.
- Cảnh báo hạn dùng và tồn dưới ngưỡng; bản đồ nhiệt tồn kho toàn chuỗi.
- Danh mục thuốc với trình soạn thảo định dạng, chi nhánh, nhà cung cấp; nội dung website (banner, trang giới thiệu, tin tức).
- Báo cáo doanh thu theo chi nhánh và kỳ, biểu đồ, thuốc bán chạy, bảng nhập – xuất – tồn, xuất Excel.
- Dự báo tổng lượng bán 7 ngày tới của 8 nhóm ATC, so sánh 5 mô hình: Linear Regression, Decision Tree, Random Forest, XGBoost và SARIMAX.
- Email qua Gmail SMTP: mã OTP, thông báo đơn, nhật ký thư và gửi lại thư lỗi.

## Công nghệ

| Thành phần | Công nghệ |
| --- | --- |
| Backend | Python 3.12, Django 6.1, Django REST Framework, Django Channels |
| Cơ sở dữ liệu | PostgreSQL 18, PostGIS 3.6 (`GEOGRAPHY(Point, 4326)`, `ST_DWithin`, `ST_Distance`) |
| Thời gian thực | WebSocket qua Channels, Redis làm channel layer |
| Giao diện | Django templates, HTMX, Alpine.js, Tailwind CSS, Lucide, Chart.js, Quill, Splide |
| Bản đồ | Leaflet, Leaflet.heat, OpenStreetMap, OSRM, Nominatim |
| Dự báo | pandas, scikit-learn, XGBoost, statsmodels |
| Chứng từ | ReportLab (PDF), openpyxl (Excel) |

Thư viện giao diện được tải sẵn vào `dacn_qlcnt/static/vendor/` (khóa phiên bản và SHA-256 trong `cong_cu/tai_thu_vien.py`), web không gọi CDN khi chạy.

## Cơ sở dữ liệu

CSDL gồm 54 bảng nghiệp vụ, tên bảng và cột bằng tiếng Việt không dấu, có chú thích cho từng bảng và cột, ràng buộc đặt ngay trong CSDL (CHECK, khóa ngoại, trigger chặn sửa chứng từ). Toàn bộ dữ liệu, kể cả ảnh, phiên đăng nhập, tin nhắn và kết quả dự báo, được lưu trong PostgreSQL. Mô tả chi tiết, quy ước và danh sách bảng: [csdl/README.md](csdl/README.md).

## Cài đặt

### Yêu cầu

- Python 3.12
- PostgreSQL 18 có PostGIS
- Redis (cần cho trò chuyện; không có Redis web vẫn chạy)

### 1. Môi trường Python và giao diện

```powershell
git clone https://github.com/kanishere55/dacn-nhathuoc.git
cd dacn-nhathuoc\dacn_qlcnt
py -3.12 -m venv .venv
$python = '.\.venv\Scripts\python.exe'
& $python -m pip install -r requirements.txt

# Tải Tailwind CLI (kiểm SHA-256) rồi build CSS
& $python cong_cu\tai_thu_vien.py
& .\.venv\cong_cu\tailwindcss.exe -i static\css\giao_dien.css -o static\css\da_bien_dich.css --minify
```

Mọi lệnh `manage.py` bên dưới chạy trong thư mục `dacn_qlcnt`. Sau mỗi lần sửa template hoặc CSS, chạy lại lệnh build Tailwind.

### 2. Khởi tạo nhanh trên Windows

Với PostgreSQL 18 cài bằng bộ cài Windows, chạy:

```powershell
powershell -ExecutionPolicy Bypass -File ..\csdl\khoi_tao_csdl_windows.ps1
```

Script bật dịch vụ PostgreSQL, tạo vai trò và CSDL `dacn_nhathuoc_nop` kèm PostGIS, ghi mật khẩu ngẫu nhiên vào `dacn_qlcnt\.env`, bật Redis, chạy migration, tạo tài khoản quản trị, nạp dữ liệu mẫu rồi mở web tại <http://127.0.0.1:8001/>. Script chạy lại được và không xóa dữ liệu đang có. Những lần sau chỉ cần bấm đúp `dacn_qlcnt\chay_web.bat`.

### 3. Cài thủ công

Tạo vai trò, CSDL và PostGIS bằng [csdl/tao_csdl.sql](csdl/tao_csdl.sql):

```powershell
psql -U postgres -f ..\csdl\tao_csdl.sql
```

Sao chép `.env.example` thành `.env` rồi điền `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD` (trùng mật khẩu vừa đặt) và `REDIS_URL`. Trên Windows, nếu GeoDjango không tự tìm được thư viện, điền `GDAL_LIBRARY_PATH` và `GEOS_LIBRARY_PATH` trỏ tới DLL của bản PostGIS đang dùng.

Chạy Redis với cấu hình `bind 127.0.0.1`, `save ""`, `appendonly no` (cổng mặc định 6379), sau đó:

```powershell
& $python manage.py migrate
& $python manage.py createsuperuser
& $python manage.py tao_du_lieu_mo_phong --quan-tri TEN_QUAN_TRI --kem-tai-khoan
& $python manage.py nap_thuoc_thuc_te
& $python manage.py nap_anh_that
& $python manage.py tao_noi_dung_website
& $python manage.py nap_tin_tuc_mau
& $python manage.py runserver 127.0.0.1:8001
```

Mở [website khách hàng](http://127.0.0.1:8001/) hoặc [khu quản lý](http://127.0.0.1:8001/quan-ly/).

### Tài khoản mẫu

`tao_du_lieu_mo_phong` tạo ba chi nhánh, nhà cung cấp và tài khoản nhân sự. Chi nhánh đầu có `mp_quan_ly` và `mp_nhan_vien`, hai chi nhánh còn lại dùng hậu tố `_02`, `_03`. Cờ `--kem-tai-khoan` tạo thêm khách hàng `mp_khach` và hỏi một mật khẩu dùng chung cho các tài khoản này.

## Lệnh quản trị

| Lệnh | Chức năng |
| --- | --- |
| `tao_du_lieu_mo_phong` | Sinh chi nhánh, nhà cung cấp, tài khoản và tồn kho ban đầu |
| `nap_thuoc_thuc_te` | Nạp 7 danh mục, 22 thuốc thực tế và tồn kho chạy thử (`--ghi-de` để đưa về thông tin chuẩn) |
| `nap_anh_that` | Tải ảnh thuốc và chi nhánh có giấy phép mở, kiểm SHA-256, lưu `bytea` kèm tác giả và giấy phép |
| `tao_noi_dung_website` | Ghi thông tin cửa hàng, trang giới thiệu, hướng dẫn và banner trang chủ |
| `nap_tin_tuc_mau` | Nạp bài viết mẫu |
| `tao_lich_su_ban_mo_phong` | Sinh lịch sử bán 60 ngày qua nghiệp vụ thật để báo cáo có dữ liệu |
| `nap_pharma_sales`, `chay_du_bao` | Nạp Pharma Sales Data và chạy thực nghiệm dự báo |
| `xu_ly_don_qua_han` | Chuyển đơn đặt giữ quá 24 giờ chưa nhận sang hết hạn |
| `kiem_tra_email`, `gui_lai_email` | Kiểm tra cấu hình SMTP, gửi lại thư lỗi |
| `doi_chieu_ton_kho` | Đối chiếu tồn theo lô và chi nhánh với chứng từ |
| `kiem_tra_csdl`, `kiem_tra_luu_tru` | Kiểm tra quy ước đặt tên CSDL và quy định lưu trữ dữ liệu |

Đặt `xu_ly_don_qua_han` chạy định kỳ 5 phút bằng Task Scheduler, chạy lệnh dưới trong thư mục `dacn_qlcnt` (đường dẫn không chứa dấu cách):

```powershell
schtasks /Create /SC MINUTE /MO 5 /TN "DACN xu ly don qua han" /TR "cmd /c cd /d $PWD && .venv\Scripts\python.exe manage.py xu_ly_don_qua_han"
```

Tồn khả dụng luôn loại trừ phần giữ hàng đã hết hạn, kể cả khi lệnh chưa chạy.

### Dự báo nhu cầu

Tải tệp `salesdaily.csv` của bộ dữ liệu Pharma Sales Data (Kaggle), đặt ngoài thư mục mã nguồn, rồi chạy:

```powershell
& $python manage.py nap_pharma_sales <đường dẫn tới salesdaily.csv>
& $python manage.py chay_du_bao
```

Dữ liệu chia theo thời gian 60/20/20; mô hình được chọn theo MAE rồi RMSE trên tập xác thực, sau đó mới đánh giá trên tập kiểm thử. Chi tiết trong [thuc_nghiem_du_bao](dacn_qlcnt/thuc_nghiem_du_bao/README.md).

### Email

Điền khóa `EMAIL_*` trong `.env` với mật khẩu ứng dụng Gmail. Khi chưa cấu hình SMTP, thư được in ra console. Kiểm tra bằng `manage.py kiem_tra_email --gui-toi <địa chỉ email>`. Khu quản lý có trang **Email hệ thống** để xem thư đã gửi, kết quả SMTP và gửi lại thư lỗi; mã OTP được che trong nhật ký.

## Kiểm thử

Chạy trong thư mục `dacn_qlcnt`:

```powershell
& .\.venv\Scripts\ruff.exe format --check
& .\.venv\Scripts\ruff.exe check
$env:DACN_TEST_REDIS_URL = 'redis://127.0.0.1:6379/0'
& $python cong_cu\kiem_tra_pg_tam.py --pg-bin <thư mục bin của PostgreSQL>
```

`kiem_tra_pg_tam.py` dựng một cụm PostgreSQL/PostGIS trắng ở thư mục tạm rồi chạy `check`, `kiem_tra_luu_tru`, `makemigrations --check`, `migrate`, `kiem_tra_csdl`, toàn bộ test, đảo và áp lại migration. Thêm `--salesdaily <đường dẫn>` để chạy cả thực nghiệm dự báo, `--test <nhãn>` để chạy một phần. Bỏ `DACN_TEST_REDIS_URL` thì test trò chuyện dùng channel layer trong bộ nhớ.

## Nguồn dữ liệu và giấy phép

- Dữ liệu dự báo: Pharma Sales Data (Kaggle), không kèm trong repo.
- Ảnh thuốc và chi nhánh: Wikimedia Commons với giấy phép mở; tác giả và giấy phép được ghi công tại trang `/nguon-hinh-anh/` của website. Ảnh banner: StockSnap (CC0).
- Bản đồ: © OpenStreetMap contributors; định tuyến OSRM; tìm địa chỉ Nominatim.
- Thư viện giao diện giữ nguyên tệp giấy phép trong `dacn_qlcnt/static/vendor/`.
