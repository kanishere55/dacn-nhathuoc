# Thực nghiệm dự báo

Mã thuần Python cho phần so sánh năm mô hình dự báo tổng lượng bán bảy ngày tiếp theo của tám nhóm ATC trong Pharma Sales Data. Phân hệ `ung_dung/du_bao` gọi các hàm ở đây, đọc dữ liệu đã nạp trong PostgreSQL và ghi kết quả, cấu hình trở lại PostgreSQL. Không có notebook, CSV hay mô hình lưu ra đĩa trong project; tệp nguồn `salesdaily.csv` để ngoài project.

- `du_lieu.py`: tạo đặc trưng (lượng bán ngày gốc, ngày trước, tuần trước, trung bình 7 và 28 ngày, thứ, tháng), nhãn tổng bảy ngày tới và chia ba tập theo thời gian 60/20/20.
- `mo_hinh.py`: tham số của Linear Regression, Decision Tree, Random Forest, XGBoost và bốn cấu hình SARIMAX. Cấu hình thứ tư dùng biến ngoại sinh là các số hạng Fourier theo ngày trong năm để mô tả mùa vụ theo năm.
- `danh_gia.py`: chọn cấu hình SARIMAX và mô hình tốt nhất của từng nhóm theo MAE rồi RMSE trên tập xác thực, sau đó mới tính sai số trên tập kiểm thử.

Chạy: `python manage.py nap_pharma_sales <đường dẫn salesdaily.csv>` rồi `python manage.py chay_du_bao`.
