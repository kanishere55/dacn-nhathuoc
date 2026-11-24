-- Tạo vai trò, CSDL và PostGIS cho hệ thống. Chạy bằng tài khoản quản trị postgres:
--   psql -U postgres -f csdl/tao_csdl.sql
-- Mật khẩu nhập ở lệnh \password phải trùng POSTGRES_PASSWORD trong dacn_qlcnt/.env.
-- Sau đó tạo bảng bằng `python manage.py migrate` trong thư mục dacn_qlcnt.

CREATE ROLE dacn_ung_dung LOGIN;
\password dacn_ung_dung

CREATE DATABASE dacn_nhathuoc_nop OWNER dacn_ung_dung
    ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C' TEMPLATE template0;

\connect dacn_nhathuoc_nop
CREATE EXTENSION IF NOT EXISTS postgis;
