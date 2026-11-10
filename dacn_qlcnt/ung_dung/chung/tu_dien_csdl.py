"""Từ vựng đã dùng trong schema, tên viết tắt và ngoại lệ định danh."""

# ATC, MAE, RMSE, SHA-256, SARIMAX, XGBoost và NaN giữ tên chuyên ngành.
# ct, pb và ncc chỉ được dùng qua các bí danh bảng đăng ký ở ten_csdl.py.
TU_VUNG = frozenset(
    """
    2000 am atc bam ban bao bay bo cac canh cap cat cau cay che chi chinh chon chot chu chuoi
    chuyen ct cung cuoc cuoi da dan dang danh dat dia dich diem dien dieu dinh doi don dong
    du dung duoc duong duy ghi gia giu goc goi gui ham han hang he het hinh hoat hoi hop huan
    huu huy id ke ket khac khach khau khi kho khoa khoan khoang khong kich kiem ky la lai lan
    lap le lieu lo luc luong luyen ly ma mae mat mo moc mot muc nan ncc ngau ngay nghiem ngoai
    nguon nguong nha nhan nhanh nhap nhat nhien nhom noi pb phai phan phep phieu qua quan quy
    quyet rmse rong rung sach san sarimax sat sau sha256 so tai tang tao te ten thai thieu
    thoai thoi thong thu thuc thuoc tiet tin tinh toi ton tra trang tri tro tru tu tuong tuyen
    vai vi vien vuot xac xgboost xuat yeu
    can chao cho co de email giao ho loai loi mac mung nguoi nhac otp phien quen sai su tieu van
    anh bat bieu byte cach cao chat chieu chong cong cua dau giam gio hien khop khuyen luu mai
    ngan nuoc pham phu ta tac thi tram y
    bai bi chua chuan den do hoan lich met moi niem phi phuong thanh that tien toan tong yet
    benh chung dich kham tat tham
    choi cod duyet momo quay sao xu
    banner doanh giay hieu hotline kinh lam lien mau nen nut thuong tom viec
    hong hu
    tuc viet
    hoa thue ty
    quyen rieng gioi
    """.split()
)

# Tên đăng nhập theo mục 5.1. Hai mã ATC nguồn độc lập với danh mục mô phỏng.
# Tên và mã ở chi tiết bán là bản chụp tại thời điểm lập phiếu.
DINH_DANH_CO_BOI_CANH = {
    ("tai_khoan", "ten_dang_nhap"),
    ("quan_sat_ban_hang", "ma_atc_nguon"),
    ("ket_qua_mo_hinh", "ma_atc_nguon"),
    ("chi_tiet_phieu_ban", "ma_thuoc_luc_ban"),
    ("chi_tiet_phieu_ban", "ten_thuoc_luc_ban"),
    # Người nhận có thể khác chủ tài khoản; tên đăng nhập chờ tạo khi đăng ký.
    ("dia_chi_giao_hang", "ten_nguoi_nhan"),
    ("don_hang", "ten_nguoi_nhan"),
    ("phien_xac_thuc", "ten_dang_nhap_dang_ky"),
    # Mã quyền là hằng số trong danh mục quyền của mã nguồn, không phải mã nghiệp vụ do người nhập.
    ("quyen_cua_nhom", "ma_quyen"),
    ("quyen_rieng_tai_khoan", "ma_quyen"),
    # Thông tin tài khoản nhận tiền hoàn do khách khai, không phải tên của bản ghi trả hàng.
    ("yeu_cau_tra_hang", "ten_ngan_hang"),
    ("yeu_cau_tra_hang", "ten_chu_tai_khoan"),
    # Mã do ngân hàng/cổng thanh toán cấp, chỉ duy nhất trong từng phương thức.
    ("giao_dich_thanh_toan", "ma_tham_chieu"),
    # Thông tin chép từ đơn thuốc của bác sĩ khi bán thuốc kê đơn.
    ("phieu_ban", "ma_don_thuoc"),
    ("phieu_ban", "ten_nguoi_ke_don"),
    # Tên chuỗi nhà thuốc trong bảng cấu hình một hàng.
    ("thong_tin_cua_hang", "ten_thuong_hieu"),
    # Thông tin doanh nghiệp người mua ghi trên hóa đơn điện tử.
    ("yeu_cau_xuat_hoa_don", "ten_cong_ty"),
    ("yeu_cau_xuat_hoa_don", "ma_so_thue"),
}

TEN_CAM = {"du_lieu", "thong_tin", "gia_tri", "noi_dung", "cot_moi"}
TIEN_TO_CAM = ("tbl_", "tb_", "bang_", "cot_")
TIEN_TO_BOOLEAN = ("la_", "co_", "dang_", "da_", "duoc_")
