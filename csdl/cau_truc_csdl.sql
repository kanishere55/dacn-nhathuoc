-- Cấu trúc CSDL hệ thống quản lý chuỗi nhà thuốc (PostgreSQL 18, PostGIS 3.6).
-- Xuất bằng pg_dump --schema-only --no-owner --no-privileges từ CSDL đã chạy đủ migration của dacn_qlcnt.
-- Không chứa dữ liệu. Tệp dùng để tra cứu cấu trúc; CSDL thật được tạo bằng `python manage.py migrate`.
--
-- PostgreSQL database dump
--


-- Dumped from database version 18.1
-- Dumped by pg_dump version 18.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';


--
-- Name: chan_doi_don_vi_thuoc_da_co_lo(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.chan_doi_don_vi_thuoc_da_co_lo() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.id_don_vi_tinh IS DISTINCT FROM OLD.id_don_vi_tinh
       AND EXISTS (SELECT 1 FROM lo_thuoc WHERE id_thuoc = OLD.id_thuoc) THEN
        RAISE EXCEPTION 'Không đổi đơn vị cơ sở của thuốc % vì thuốc đã có lô trong kho.', OLD.ma_thuoc
            USING ERRCODE = 'restrict_violation',
                  HINT = 'Tạo thuốc mới với đơn vị đúng và cho thuốc cũ ngừng hoạt động.';
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: FUNCTION chan_doi_don_vi_thuoc_da_co_lo(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.chan_doi_don_vi_thuoc_da_co_lo() IS 'Q02: đơn vị cơ sở cố định sau khi thuốc có lô, để số lượng trên chứng từ cũ giữ đúng nghĩa.';


--
-- Name: chan_doi_ma_lo_da_co_ton(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.chan_doi_ma_lo_da_co_ton() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF (NEW.id_thuoc, NEW.ma_lo_thuoc) IS DISTINCT FROM (OLD.id_thuoc, OLD.ma_lo_thuoc)
       AND EXISTS (SELECT 1 FROM ton_kho WHERE id_lo_thuoc = OLD.id_lo_thuoc) THEN
        RAISE EXCEPTION 'Không đổi thuốc hoặc mã của lô % vì lô đã có trong kho và trên chứng từ.', OLD.ma_lo_thuoc
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: FUNCTION chan_doi_ma_lo_da_co_ton(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.chan_doi_ma_lo_da_co_ton() IS 'Q01: lô định danh bằng thuốc và mã lô in trên bao bì; lô đã nhập kho thì không đổi định danh.';


--
-- Name: chan_sua_chung_tu_kho(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.chan_sua_chung_tu_kho() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    khoa text;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        khoa := ' ' || TG_TABLE_NAME || ':' || (to_jsonb(OLD) ->> ('id_' || TG_TABLE_NAME)) || ' ';
        IF (to_jsonb(NEW) - 'thoi_diem_tao') = (to_jsonb(OLD) - 'thoi_diem_tao')
           AND position(khoa IN coalesce(current_setting('dacn.chung_tu_moi', true), '')) > 0 THEN
            RETURN NEW;
        END IF;
    END IF;
    RAISE EXCEPTION 'Chứng từ kho đã xác nhận không được sửa hoặc xóa (bảng %).', TG_TABLE_NAME
        USING ERRCODE = 'restrict_violation',
              HINT = 'Sai sót được điều chỉnh bằng chứng từ mới: kiểm kê, trả nhà cung cấp hoặc xuất hủy.';
END;
$$;


--
-- Name: FUNCTION chan_sua_chung_tu_kho(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.chan_sua_chung_tu_kho() IS 'Từ chối UPDATE/DELETE chứng từ kho đã xác nhận (Q06, Q12); chỉ cho chỉnh thoi_diem_tao của phiếu tạo trong cùng giao dịch.';


--
-- Name: da_cat_khoang_trang(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.da_cat_khoang_trang(van_ban text) RETURNS boolean
    LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
    AS $$
    SELECT CASE WHEN char_length(van_ban) = 0 THEN TRUE ELSE
        ascii(left(van_ban, 1)) <> ALL (
            ARRAY[9, 10, 11, 12, 13, 32, 133, 160, 5760,
                  8192, 8193, 8194, 8195, 8196, 8197, 8198, 8199, 8200, 8201, 8202,
                  8232, 8233, 8239, 8287, 12288, 8203, 65279]
        )
        AND ascii(right(van_ban, 1)) <> ALL (
            ARRAY[9, 10, 11, 12, 13, 32, 133, 160, 5760,
                  8192, 8193, 8194, 8195, 8196, 8197, 8198, 8199, 8200, 8201, 8202,
                  8232, 8233, 8239, 8287, 12288, 8203, 65279]
        )
    END;
$$;


--
-- Name: FUNCTION da_cat_khoang_trang(van_ban text); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.da_cat_khoang_trang(van_ban text) IS 'Đúng khi đầu và cuối không thuộc 27 ký tự khoảng trắng ở mục 7.1; chuỗi rỗng hợp lệ với riêng quy tắc cắt khoảng trắng, cột bắt buộc thêm khong_rong. Yêu cầu database UTF8 để ascii trả mã Unicode. NULL trả NULL. Sửa hàm không tự kiểm lại dữ liệu cũ; phải kiểm tra và xác thực lại CHECK trong migration mới.';


--
-- Name: ghi_nhan_chung_tu_moi(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.ghi_nhan_chung_tu_moi() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Đánh dấu phiếu vừa tạo trong giao dịch hiện tại; set_config(..., true) chỉ sống tới
    -- cuối giao dịch và được hoàn lại nếu savepoint chứa lệnh INSERT bị hủy.
    PERFORM set_config(
        'dacn.chung_tu_moi',
        coalesce(current_setting('dacn.chung_tu_moi', true), '')
            || ' ' || TG_TABLE_NAME || ':' || (to_jsonb(NEW) ->> ('id_' || TG_TABLE_NAME)) || ' ',
        true
    );
    RETURN NULL;
END;
$$;


--
-- Name: FUNCTION ghi_nhan_chung_tu_moi(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.ghi_nhan_chung_tu_moi() IS 'Ghi nhận phiếu kho tạo trong giao dịch hiện tại để chan_sua_chung_tu_kho cho phép chỉnh thời điểm trước khi commit.';


--
-- Name: khong_rong(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.khong_rong(van_ban text) RETURNS boolean
    LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
    AS $$
    SELECT char_length(translate(
        van_ban,
        U&'\0009\000A\000B\000C\000D\0020\0085\00A0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000\200B\FEFF',
        ''
    )) > 0;
$$;


--
-- Name: FUNCTION khong_rong(van_ban text); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.khong_rong(van_ban text) IS 'Đúng khi có ký tự ngoài 27 ký tự khoảng trắng của quy ước project mục 7.1; không phụ thuộc locale. NULL trả NULL, cột bắt buộc vẫn cần NOT NULL. Sửa hàm không tự kiểm lại dữ liệu cũ; phải kiểm tra và xác thực lại CHECK trong migration mới.';


--
-- Name: la_mot_dong(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.la_mot_dong(van_ban text) RETURNS boolean
    LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
    AS $$
    SELECT char_length(translate(
        van_ban,
        U&'\0001\0002\0003\0004\0005\0006\0007\0008\0009\000A\000B\000C\000D\000E\000F\0010\0011\0012\0013\0014\0015\0016\0017\0018\0019\001A\001B\001C\001D\001E\001F\007F\0080\0081\0082\0083\0084\0085\0086\0087\0088\0089\008A\008B\008C\008D\008E\008F\0090\0091\0092\0093\0094\0095\0096\0097\0098\0099\009A\009B\009C\009D\009E\009F\2028\2029',
        ''
    )) = char_length(van_ban);
$$;


--
-- Name: FUNCTION la_mot_dong(van_ban text); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.la_mot_dong(van_ban text) IS 'Đúng khi không chứa U+0001 đến U+001F, U+007F đến U+009F, U+2028 hoặc U+2029. Không dùng lớp ký tự phụ thuộc locale. PostgreSQL text không chứa được U+0000. NULL trả NULL. Sửa hàm không tự kiểm lại dữ liệu cũ; phải kiểm tra và xác thực lại CHECK trong migration mới.';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: anh_chi_nhanh; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.anh_chi_nhanh (
    noi_dung_anh bytea NOT NULL,
    kich_thuoc_byte integer NOT NULL,
    chieu_rong smallint NOT NULL,
    chieu_cao smallint NOT NULL,
    bam_sha256 text NOT NULL,
    thu_tu smallint DEFAULT 0 NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_anh_chi_nhanh bigint NOT NULL,
    id_chi_nhanh bigint NOT NULL,
    nguon_anh text DEFAULT ''::text NOT NULL,
    CONSTRAINT kiem_tra__anh_chi_nhanh__bam_sha256_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(bam_sha256)),
    CONSTRAINT kiem_tra__anh_chi_nhanh__bam_sha256_dung_dinh_dang CHECK ((bam_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT kiem_tra__anh_chi_nhanh__bam_sha256_khong_rong CHECK (public.khong_rong(bam_sha256)),
    CONSTRAINT kiem_tra__anh_chi_nhanh__bam_sha256_mot_dong CHECK (public.la_mot_dong(bam_sha256)),
    CONSTRAINT kiem_tra__anh_chi_nhanh__kich_thuoc_anh_hop_le CHECK (((chieu_rong >= 1) AND (chieu_rong <= 1600) AND (chieu_cao >= 1) AND (chieu_cao <= 1600))),
    CONSTRAINT kiem_tra__anh_chi_nhanh__kich_thuoc_byte_khop CHECK (((kich_thuoc_byte = octet_length(noi_dung_anh)) AND (kich_thuoc_byte >= 1) AND (kich_thuoc_byte <= 3145728))),
    CONSTRAINT kiem_tra__anh_chi_nhanh__nguon_anh_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(nguon_anh)),
    CONSTRAINT kiem_tra__anh_chi_nhanh__nguon_anh_mot_dong CHECK (public.la_mot_dong(nguon_anh)),
    CONSTRAINT kiem_tra__anh_chi_nhanh__thu_tu_khong_am CHECK ((thu_tu >= 0))
);


--
-- Name: TABLE anh_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.anh_chi_nhanh IS 'Mỗi hàng là một ảnh mặt tiền hoặc bên trong nhà thuốc, lưu bytea.';


--
-- Name: COLUMN anh_chi_nhanh.noi_dung_anh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_chi_nhanh.noi_dung_anh IS 'Dữ liệu ảnh WebP đã chuẩn hóa, không còn metadata của tệp gốc.';


--
-- Name: COLUMN anh_chi_nhanh.kich_thuoc_byte; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_chi_nhanh.kich_thuoc_byte IS 'Số byte của noi_dung_anh, tối đa 3 MiB.';


--
-- Name: COLUMN anh_chi_nhanh.chieu_rong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_chi_nhanh.chieu_rong IS 'Chiều rộng ảnh theo điểm ảnh, 1 đến 1600.';


--
-- Name: COLUMN anh_chi_nhanh.chieu_cao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_chi_nhanh.chieu_cao IS 'Chiều cao ảnh theo điểm ảnh, 1 đến 1600.';


--
-- Name: COLUMN anh_chi_nhanh.bam_sha256; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_chi_nhanh.bam_sha256 IS 'SHA-256 hệ thập lục phân của noi_dung_anh; dùng làm ETag khi phục vụ.';


--
-- Name: COLUMN anh_chi_nhanh.thu_tu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_chi_nhanh.thu_tu IS 'Thứ tự hiển thị trong bộ ảnh, số nhỏ đứng trước; ảnh đầu là ảnh đại diện.';


--
-- Name: COLUMN anh_chi_nhanh.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_chi_nhanh.thoi_diem_tao IS 'Thời điểm tải ảnh lên.';


--
-- Name: COLUMN anh_chi_nhanh.id_anh_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_chi_nhanh.id_anh_chi_nhanh IS 'Định danh nội bộ PostgreSQL cấp, dùng trên đường dẫn ảnh.';


--
-- Name: COLUMN anh_chi_nhanh.id_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_chi_nhanh.id_chi_nhanh IS 'Chi nhánh sở hữu ảnh.';


--
-- Name: COLUMN anh_chi_nhanh.nguon_anh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_chi_nhanh.nguon_anh IS 'Nguồn, tác giả và giấy phép của ảnh (ví dụ ảnh Wikimedia Commons); một dòng, rỗng với ảnh tự chụp hoặc tự tải lên.';


--
-- Name: CONSTRAINT kiem_tra__anh_chi_nhanh__bam_sha256_da_cat_khoang_trang ON anh_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_chi_nhanh__bam_sha256_da_cat_khoang_trang ON public.anh_chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(bam_sha256))';


--
-- Name: CONSTRAINT kiem_tra__anh_chi_nhanh__bam_sha256_dung_dinh_dang ON anh_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_chi_nhanh__bam_sha256_dung_dinh_dang ON public.anh_chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((bam_sha256 ~ ''^[0-9a-f]{64}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__anh_chi_nhanh__bam_sha256_khong_rong ON anh_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_chi_nhanh__bam_sha256_khong_rong ON public.anh_chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(bam_sha256))';


--
-- Name: CONSTRAINT kiem_tra__anh_chi_nhanh__bam_sha256_mot_dong ON anh_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_chi_nhanh__bam_sha256_mot_dong ON public.anh_chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(bam_sha256))';


--
-- Name: CONSTRAINT kiem_tra__anh_chi_nhanh__kich_thuoc_anh_hop_le ON anh_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_chi_nhanh__kich_thuoc_anh_hop_le ON public.anh_chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((chieu_rong >= 1) AND (chieu_rong <= 1600) AND (chieu_cao >= 1) AND (chieu_cao <= 1600)))';


--
-- Name: CONSTRAINT kiem_tra__anh_chi_nhanh__kich_thuoc_byte_khop ON anh_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_chi_nhanh__kich_thuoc_byte_khop ON public.anh_chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((kich_thuoc_byte = octet_length(noi_dung_anh)) AND (kich_thuoc_byte >= 1) AND (kich_thuoc_byte <= 3145728)))';


--
-- Name: CONSTRAINT kiem_tra__anh_chi_nhanh__nguon_anh_da_cat_khoang_trang ON anh_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_chi_nhanh__nguon_anh_da_cat_khoang_trang ON public.anh_chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(nguon_anh))';


--
-- Name: CONSTRAINT kiem_tra__anh_chi_nhanh__nguon_anh_mot_dong ON anh_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_chi_nhanh__nguon_anh_mot_dong ON public.anh_chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(nguon_anh))';


--
-- Name: CONSTRAINT kiem_tra__anh_chi_nhanh__thu_tu_khong_am ON anh_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_chi_nhanh__thu_tu_khong_am ON public.anh_chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((thu_tu >= 0))';


--
-- Name: anh_chi_nhanh_id_anh_chi_nhanh_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.anh_chi_nhanh ALTER COLUMN id_anh_chi_nhanh ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.anh_chi_nhanh_id_anh_chi_nhanh_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: anh_noi_dung; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.anh_noi_dung (
    noi_dung_anh bytea NOT NULL,
    kich_thuoc_byte integer NOT NULL,
    chieu_rong smallint NOT NULL,
    chieu_cao smallint NOT NULL,
    bam_sha256 text NOT NULL,
    thu_tu smallint DEFAULT 0 NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_anh_noi_dung bigint NOT NULL,
    id_tai_khoan bigint NOT NULL,
    CONSTRAINT kiem_tra__anh_noi_dung__bam_sha256_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(bam_sha256)),
    CONSTRAINT kiem_tra__anh_noi_dung__bam_sha256_dung_dinh_dang CHECK ((bam_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT kiem_tra__anh_noi_dung__bam_sha256_khong_rong CHECK (public.khong_rong(bam_sha256)),
    CONSTRAINT kiem_tra__anh_noi_dung__bam_sha256_mot_dong CHECK (public.la_mot_dong(bam_sha256)),
    CONSTRAINT kiem_tra__anh_noi_dung__kich_thuoc_anh_hop_le CHECK (((chieu_rong >= 1) AND (chieu_rong <= 1600) AND (chieu_cao >= 1) AND (chieu_cao <= 1600))),
    CONSTRAINT kiem_tra__anh_noi_dung__kich_thuoc_byte_khop CHECK (((kich_thuoc_byte = octet_length(noi_dung_anh)) AND (kich_thuoc_byte >= 1) AND (kich_thuoc_byte <= 3145728))),
    CONSTRAINT kiem_tra__anh_noi_dung__thu_tu_khong_am CHECK ((thu_tu >= 0))
);


--
-- Name: TABLE anh_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.anh_noi_dung IS 'Mỗi hàng là một ảnh chèn trong nội dung soạn thảo (mô tả thuốc, giới thiệu chi nhánh), lưu bytea.';


--
-- Name: COLUMN anh_noi_dung.noi_dung_anh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_noi_dung.noi_dung_anh IS 'Dữ liệu ảnh WebP đã chuẩn hóa, không còn metadata của tệp gốc.';


--
-- Name: COLUMN anh_noi_dung.kich_thuoc_byte; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_noi_dung.kich_thuoc_byte IS 'Số byte của noi_dung_anh, tối đa 3 MiB.';


--
-- Name: COLUMN anh_noi_dung.chieu_rong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_noi_dung.chieu_rong IS 'Chiều rộng ảnh theo điểm ảnh, 1 đến 1600.';


--
-- Name: COLUMN anh_noi_dung.chieu_cao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_noi_dung.chieu_cao IS 'Chiều cao ảnh theo điểm ảnh, 1 đến 1600.';


--
-- Name: COLUMN anh_noi_dung.bam_sha256; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_noi_dung.bam_sha256 IS 'SHA-256 hệ thập lục phân của noi_dung_anh; dùng làm ETag khi phục vụ.';


--
-- Name: COLUMN anh_noi_dung.thu_tu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_noi_dung.thu_tu IS 'Thứ tự hiển thị trong bộ ảnh, số nhỏ đứng trước; ảnh đầu là ảnh đại diện.';


--
-- Name: COLUMN anh_noi_dung.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_noi_dung.thoi_diem_tao IS 'Thời điểm tải ảnh lên.';


--
-- Name: COLUMN anh_noi_dung.id_anh_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_noi_dung.id_anh_noi_dung IS 'Định danh nội bộ PostgreSQL cấp, dùng trên đường dẫn ảnh.';


--
-- Name: COLUMN anh_noi_dung.id_tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_noi_dung.id_tai_khoan IS 'Tài khoản nội bộ đã tải ảnh lên khi soạn nội dung.';


--
-- Name: CONSTRAINT kiem_tra__anh_noi_dung__bam_sha256_da_cat_khoang_trang ON anh_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_noi_dung__bam_sha256_da_cat_khoang_trang ON public.anh_noi_dung IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(bam_sha256))';


--
-- Name: CONSTRAINT kiem_tra__anh_noi_dung__bam_sha256_dung_dinh_dang ON anh_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_noi_dung__bam_sha256_dung_dinh_dang ON public.anh_noi_dung IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((bam_sha256 ~ ''^[0-9a-f]{64}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__anh_noi_dung__bam_sha256_khong_rong ON anh_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_noi_dung__bam_sha256_khong_rong ON public.anh_noi_dung IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(bam_sha256))';


--
-- Name: CONSTRAINT kiem_tra__anh_noi_dung__bam_sha256_mot_dong ON anh_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_noi_dung__bam_sha256_mot_dong ON public.anh_noi_dung IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(bam_sha256))';


--
-- Name: CONSTRAINT kiem_tra__anh_noi_dung__kich_thuoc_anh_hop_le ON anh_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_noi_dung__kich_thuoc_anh_hop_le ON public.anh_noi_dung IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((chieu_rong >= 1) AND (chieu_rong <= 1600) AND (chieu_cao >= 1) AND (chieu_cao <= 1600)))';


--
-- Name: CONSTRAINT kiem_tra__anh_noi_dung__kich_thuoc_byte_khop ON anh_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_noi_dung__kich_thuoc_byte_khop ON public.anh_noi_dung IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((kich_thuoc_byte = octet_length(noi_dung_anh)) AND (kich_thuoc_byte >= 1) AND (kich_thuoc_byte <= 3145728)))';


--
-- Name: CONSTRAINT kiem_tra__anh_noi_dung__thu_tu_khong_am ON anh_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_noi_dung__thu_tu_khong_am ON public.anh_noi_dung IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((thu_tu >= 0))';


--
-- Name: anh_noi_dung_id_anh_noi_dung_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.anh_noi_dung ALTER COLUMN id_anh_noi_dung ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.anh_noi_dung_id_anh_noi_dung_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: anh_thuoc; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.anh_thuoc (
    noi_dung_anh bytea NOT NULL,
    kich_thuoc_byte integer NOT NULL,
    chieu_rong smallint NOT NULL,
    chieu_cao smallint NOT NULL,
    bam_sha256 text NOT NULL,
    thu_tu smallint DEFAULT 0 NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_anh_thuoc bigint NOT NULL,
    id_thuoc bigint NOT NULL,
    nguon_anh text DEFAULT ''::text NOT NULL,
    CONSTRAINT kiem_tra__anh_thuoc__bam_sha256_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(bam_sha256)),
    CONSTRAINT kiem_tra__anh_thuoc__bam_sha256_dung_dinh_dang CHECK ((bam_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT kiem_tra__anh_thuoc__bam_sha256_khong_rong CHECK (public.khong_rong(bam_sha256)),
    CONSTRAINT kiem_tra__anh_thuoc__bam_sha256_mot_dong CHECK (public.la_mot_dong(bam_sha256)),
    CONSTRAINT kiem_tra__anh_thuoc__kich_thuoc_anh_hop_le CHECK (((chieu_rong >= 1) AND (chieu_rong <= 1600) AND (chieu_cao >= 1) AND (chieu_cao <= 1600))),
    CONSTRAINT kiem_tra__anh_thuoc__kich_thuoc_byte_khop CHECK (((kich_thuoc_byte = octet_length(noi_dung_anh)) AND (kich_thuoc_byte >= 1) AND (kich_thuoc_byte <= 3145728))),
    CONSTRAINT kiem_tra__anh_thuoc__nguon_anh_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(nguon_anh)),
    CONSTRAINT kiem_tra__anh_thuoc__nguon_anh_mot_dong CHECK (public.la_mot_dong(nguon_anh)),
    CONSTRAINT kiem_tra__anh_thuoc__thu_tu_khong_am CHECK ((thu_tu >= 0))
);


--
-- Name: TABLE anh_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.anh_thuoc IS 'Mỗi hàng là một ảnh sản phẩm của thuốc, lưu bytea.';


--
-- Name: COLUMN anh_thuoc.noi_dung_anh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_thuoc.noi_dung_anh IS 'Dữ liệu ảnh WebP đã chuẩn hóa, không còn metadata của tệp gốc.';


--
-- Name: COLUMN anh_thuoc.kich_thuoc_byte; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_thuoc.kich_thuoc_byte IS 'Số byte của noi_dung_anh, tối đa 3 MiB.';


--
-- Name: COLUMN anh_thuoc.chieu_rong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_thuoc.chieu_rong IS 'Chiều rộng ảnh theo điểm ảnh, 1 đến 1600.';


--
-- Name: COLUMN anh_thuoc.chieu_cao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_thuoc.chieu_cao IS 'Chiều cao ảnh theo điểm ảnh, 1 đến 1600.';


--
-- Name: COLUMN anh_thuoc.bam_sha256; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_thuoc.bam_sha256 IS 'SHA-256 hệ thập lục phân của noi_dung_anh; dùng làm ETag khi phục vụ.';


--
-- Name: COLUMN anh_thuoc.thu_tu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_thuoc.thu_tu IS 'Thứ tự hiển thị trong bộ ảnh, số nhỏ đứng trước; ảnh đầu là ảnh đại diện.';


--
-- Name: COLUMN anh_thuoc.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_thuoc.thoi_diem_tao IS 'Thời điểm tải ảnh lên.';


--
-- Name: COLUMN anh_thuoc.id_anh_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_thuoc.id_anh_thuoc IS 'Định danh nội bộ PostgreSQL cấp, dùng trên đường dẫn ảnh.';


--
-- Name: COLUMN anh_thuoc.id_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_thuoc.id_thuoc IS 'Thuốc sở hữu ảnh.';


--
-- Name: COLUMN anh_thuoc.nguon_anh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_thuoc.nguon_anh IS 'Nguồn, tác giả và giấy phép của ảnh (ví dụ ảnh Wikimedia Commons); một dòng, rỗng với ảnh tự chụp hoặc tự tải lên.';


--
-- Name: CONSTRAINT kiem_tra__anh_thuoc__bam_sha256_da_cat_khoang_trang ON anh_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_thuoc__bam_sha256_da_cat_khoang_trang ON public.anh_thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(bam_sha256))';


--
-- Name: CONSTRAINT kiem_tra__anh_thuoc__bam_sha256_dung_dinh_dang ON anh_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_thuoc__bam_sha256_dung_dinh_dang ON public.anh_thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((bam_sha256 ~ ''^[0-9a-f]{64}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__anh_thuoc__bam_sha256_khong_rong ON anh_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_thuoc__bam_sha256_khong_rong ON public.anh_thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(bam_sha256))';


--
-- Name: CONSTRAINT kiem_tra__anh_thuoc__bam_sha256_mot_dong ON anh_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_thuoc__bam_sha256_mot_dong ON public.anh_thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(bam_sha256))';


--
-- Name: CONSTRAINT kiem_tra__anh_thuoc__kich_thuoc_anh_hop_le ON anh_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_thuoc__kich_thuoc_anh_hop_le ON public.anh_thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((chieu_rong >= 1) AND (chieu_rong <= 1600) AND (chieu_cao >= 1) AND (chieu_cao <= 1600)))';


--
-- Name: CONSTRAINT kiem_tra__anh_thuoc__kich_thuoc_byte_khop ON anh_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_thuoc__kich_thuoc_byte_khop ON public.anh_thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((kich_thuoc_byte = octet_length(noi_dung_anh)) AND (kich_thuoc_byte >= 1) AND (kich_thuoc_byte <= 3145728)))';


--
-- Name: CONSTRAINT kiem_tra__anh_thuoc__nguon_anh_da_cat_khoang_trang ON anh_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_thuoc__nguon_anh_da_cat_khoang_trang ON public.anh_thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(nguon_anh))';


--
-- Name: CONSTRAINT kiem_tra__anh_thuoc__nguon_anh_mot_dong ON anh_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_thuoc__nguon_anh_mot_dong ON public.anh_thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(nguon_anh))';


--
-- Name: CONSTRAINT kiem_tra__anh_thuoc__thu_tu_khong_am ON anh_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_thuoc__thu_tu_khong_am ON public.anh_thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((thu_tu >= 0))';


--
-- Name: anh_thuoc_id_anh_thuoc_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.anh_thuoc ALTER COLUMN id_anh_thuoc ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.anh_thuoc_id_anh_thuoc_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: anh_tin_nhan; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.anh_tin_nhan (
    noi_dung_anh bytea NOT NULL,
    kich_thuoc_byte integer NOT NULL,
    chieu_rong smallint NOT NULL,
    chieu_cao smallint NOT NULL,
    bam_sha256 text NOT NULL,
    thu_tu smallint DEFAULT 0 NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_anh_tin_nhan bigint NOT NULL,
    id_tin_nhan bigint NOT NULL,
    CONSTRAINT kiem_tra__anh_tin_nhan__bam_sha256_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(bam_sha256)),
    CONSTRAINT kiem_tra__anh_tin_nhan__bam_sha256_dung_dinh_dang CHECK ((bam_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT kiem_tra__anh_tin_nhan__bam_sha256_khong_rong CHECK (public.khong_rong(bam_sha256)),
    CONSTRAINT kiem_tra__anh_tin_nhan__bam_sha256_mot_dong CHECK (public.la_mot_dong(bam_sha256)),
    CONSTRAINT kiem_tra__anh_tin_nhan__kich_thuoc_anh_hop_le CHECK (((chieu_rong >= 1) AND (chieu_rong <= 1600) AND (chieu_cao >= 1) AND (chieu_cao <= 1600))),
    CONSTRAINT kiem_tra__anh_tin_nhan__kich_thuoc_byte_khop CHECK (((kich_thuoc_byte = octet_length(noi_dung_anh)) AND (kich_thuoc_byte >= 1) AND (kich_thuoc_byte <= 3145728))),
    CONSTRAINT kiem_tra__anh_tin_nhan__thu_tu_khong_am CHECK ((thu_tu >= 0)),
    CONSTRAINT kiem_tra__anh_tin_nhan__thu_tu_toi_da CHECK ((thu_tu < 5))
);


--
-- Name: TABLE anh_tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.anh_tin_nhan IS 'Mỗi hàng là một ảnh gửi kèm tin nhắn trò chuyện, lưu bytea.';


--
-- Name: COLUMN anh_tin_nhan.noi_dung_anh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_tin_nhan.noi_dung_anh IS 'Dữ liệu ảnh WebP đã chuẩn hóa, không còn metadata của tệp gốc.';


--
-- Name: COLUMN anh_tin_nhan.kich_thuoc_byte; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_tin_nhan.kich_thuoc_byte IS 'Số byte của noi_dung_anh, tối đa 3 MiB.';


--
-- Name: COLUMN anh_tin_nhan.chieu_rong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_tin_nhan.chieu_rong IS 'Chiều rộng ảnh theo điểm ảnh, 1 đến 1600.';


--
-- Name: COLUMN anh_tin_nhan.chieu_cao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_tin_nhan.chieu_cao IS 'Chiều cao ảnh theo điểm ảnh, 1 đến 1600.';


--
-- Name: COLUMN anh_tin_nhan.bam_sha256; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_tin_nhan.bam_sha256 IS 'SHA-256 hệ thập lục phân của noi_dung_anh; dùng làm ETag khi phục vụ.';


--
-- Name: COLUMN anh_tin_nhan.thu_tu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_tin_nhan.thu_tu IS 'Thứ tự hiển thị trong bộ ảnh, số nhỏ đứng trước; ảnh đầu là ảnh đại diện.';


--
-- Name: COLUMN anh_tin_nhan.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_tin_nhan.thoi_diem_tao IS 'Thời điểm tải ảnh lên.';


--
-- Name: COLUMN anh_tin_nhan.id_anh_tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_tin_nhan.id_anh_tin_nhan IS 'Định danh nội bộ PostgreSQL cấp, dùng trên đường dẫn ảnh riêng tư.';


--
-- Name: COLUMN anh_tin_nhan.id_tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.anh_tin_nhan.id_tin_nhan IS 'Tin sở hữu ảnh; chỉ khách và nhân sự phụ trách cuộc trò chuyện xem được.';


--
-- Name: CONSTRAINT kiem_tra__anh_tin_nhan__bam_sha256_da_cat_khoang_trang ON anh_tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_tin_nhan__bam_sha256_da_cat_khoang_trang ON public.anh_tin_nhan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(bam_sha256))';


--
-- Name: CONSTRAINT kiem_tra__anh_tin_nhan__bam_sha256_dung_dinh_dang ON anh_tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_tin_nhan__bam_sha256_dung_dinh_dang ON public.anh_tin_nhan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((bam_sha256 ~ ''^[0-9a-f]{64}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__anh_tin_nhan__bam_sha256_khong_rong ON anh_tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_tin_nhan__bam_sha256_khong_rong ON public.anh_tin_nhan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(bam_sha256))';


--
-- Name: CONSTRAINT kiem_tra__anh_tin_nhan__bam_sha256_mot_dong ON anh_tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_tin_nhan__bam_sha256_mot_dong ON public.anh_tin_nhan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(bam_sha256))';


--
-- Name: CONSTRAINT kiem_tra__anh_tin_nhan__kich_thuoc_anh_hop_le ON anh_tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_tin_nhan__kich_thuoc_anh_hop_le ON public.anh_tin_nhan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((chieu_rong >= 1) AND (chieu_rong <= 1600) AND (chieu_cao >= 1) AND (chieu_cao <= 1600)))';


--
-- Name: CONSTRAINT kiem_tra__anh_tin_nhan__kich_thuoc_byte_khop ON anh_tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_tin_nhan__kich_thuoc_byte_khop ON public.anh_tin_nhan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((kich_thuoc_byte = octet_length(noi_dung_anh)) AND (kich_thuoc_byte >= 1) AND (kich_thuoc_byte <= 3145728)))';


--
-- Name: CONSTRAINT kiem_tra__anh_tin_nhan__thu_tu_khong_am ON anh_tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_tin_nhan__thu_tu_khong_am ON public.anh_tin_nhan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((thu_tu >= 0))';


--
-- Name: CONSTRAINT kiem_tra__anh_tin_nhan__thu_tu_toi_da ON anh_tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__anh_tin_nhan__thu_tu_toi_da ON public.anh_tin_nhan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((thu_tu < 5))';


--
-- Name: anh_tin_nhan_id_anh_tin_nhan_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.anh_tin_nhan ALTER COLUMN id_anh_tin_nhan ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.anh_tin_nhan_id_anh_tin_nhan_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);


--
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.auth_group ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_group_permissions (
    id bigint NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.auth_group_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


--
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.auth_permission ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_permission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: banner_trang_chu; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.banner_trang_chu (
    noi_dung_anh bytea NOT NULL,
    kich_thuoc_byte integer NOT NULL,
    chieu_rong smallint NOT NULL,
    chieu_cao smallint NOT NULL,
    bam_sha256 text NOT NULL,
    thu_tu smallint DEFAULT 0 NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_banner_trang_chu bigint NOT NULL,
    tieu_de text NOT NULL,
    mo_ta text DEFAULT ''::text NOT NULL,
    nhan_nut text NOT NULL,
    duong_dan text NOT NULL,
    mau_nen text DEFAULT '#e7f4ee'::text NOT NULL,
    nguon_anh text DEFAULT ''::text NOT NULL,
    dang_hien_thi boolean DEFAULT true NOT NULL,
    ngay_bat_dau date,
    ngay_ket_thuc date,
    CONSTRAINT kiem_tra__banner__bam_sha256_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(bam_sha256)),
    CONSTRAINT kiem_tra__banner__bam_sha256_dung_dinh_dang CHECK ((bam_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT kiem_tra__banner__bam_sha256_khong_rong CHECK (public.khong_rong(bam_sha256)),
    CONSTRAINT kiem_tra__banner__bam_sha256_mot_dong CHECK (public.la_mot_dong(bam_sha256)),
    CONSTRAINT kiem_tra__banner__duong_dan_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(duong_dan)),
    CONSTRAINT kiem_tra__banner__duong_dan_dung_dinh_dang CHECK ((duong_dan ~ '^/[A-Za-z0-9/_.?=&%-]*$'::text)),
    CONSTRAINT kiem_tra__banner__duong_dan_khong_rong CHECK (public.khong_rong(duong_dan)),
    CONSTRAINT kiem_tra__banner__duong_dan_mot_dong CHECK (public.la_mot_dong(duong_dan)),
    CONSTRAINT kiem_tra__banner__ket_thuc_sau_bat_dau CHECK (((ngay_bat_dau IS NULL) OR (ngay_ket_thuc IS NULL) OR (ngay_ket_thuc >= ngay_bat_dau))),
    CONSTRAINT kiem_tra__banner__kich_thuoc_anh_hop_le CHECK (((chieu_rong >= 1) AND (chieu_rong <= 1600) AND (chieu_cao >= 1) AND (chieu_cao <= 1600))),
    CONSTRAINT kiem_tra__banner__kich_thuoc_byte_khop CHECK (((kich_thuoc_byte = octet_length(noi_dung_anh)) AND (kich_thuoc_byte >= 1) AND (kich_thuoc_byte <= 3145728))),
    CONSTRAINT kiem_tra__banner__mau_nen_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(mau_nen)),
    CONSTRAINT kiem_tra__banner__mau_nen_dung_dinh_dang CHECK ((mau_nen ~ '^#[0-9a-f]{6}$'::text)),
    CONSTRAINT kiem_tra__banner__mau_nen_khong_rong CHECK (public.khong_rong(mau_nen)),
    CONSTRAINT kiem_tra__banner__mau_nen_mot_dong CHECK (public.la_mot_dong(mau_nen)),
    CONSTRAINT kiem_tra__banner__mo_ta_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(mo_ta)),
    CONSTRAINT kiem_tra__banner__mo_ta_mot_dong CHECK (public.la_mot_dong(mo_ta)),
    CONSTRAINT kiem_tra__banner__nguon_anh_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(nguon_anh)),
    CONSTRAINT kiem_tra__banner__nguon_anh_mot_dong CHECK (public.la_mot_dong(nguon_anh)),
    CONSTRAINT kiem_tra__banner__nhan_nut_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(nhan_nut)),
    CONSTRAINT kiem_tra__banner__nhan_nut_khong_rong CHECK (public.khong_rong(nhan_nut)),
    CONSTRAINT kiem_tra__banner__nhan_nut_mot_dong CHECK (public.la_mot_dong(nhan_nut)),
    CONSTRAINT kiem_tra__banner__thu_tu_khong_am CHECK ((thu_tu >= 0)),
    CONSTRAINT kiem_tra__banner__tieu_de_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(tieu_de)),
    CONSTRAINT kiem_tra__banner__tieu_de_khong_rong CHECK (public.khong_rong(tieu_de)),
    CONSTRAINT kiem_tra__banner__tieu_de_mot_dong CHECK (public.la_mot_dong(tieu_de))
);


--
-- Name: TABLE banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.banner_trang_chu IS 'Mỗi hàng là một banner trong băng chuyền đầu trang chủ, ảnh lưu bytea.';


--
-- Name: COLUMN banner_trang_chu.noi_dung_anh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.banner_trang_chu.noi_dung_anh IS 'Dữ liệu ảnh WebP đã chuẩn hóa, không còn metadata của tệp gốc.';


--
-- Name: COLUMN banner_trang_chu.kich_thuoc_byte; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.banner_trang_chu.kich_thuoc_byte IS 'Số byte của noi_dung_anh, tối đa 3 MiB.';


--
-- Name: COLUMN banner_trang_chu.chieu_rong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.banner_trang_chu.chieu_rong IS 'Chiều rộng ảnh theo điểm ảnh, 1 đến 1600.';


--
-- Name: COLUMN banner_trang_chu.chieu_cao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.banner_trang_chu.chieu_cao IS 'Chiều cao ảnh theo điểm ảnh, 1 đến 1600.';


--
-- Name: COLUMN banner_trang_chu.bam_sha256; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.banner_trang_chu.bam_sha256 IS 'SHA-256 hệ thập lục phân của noi_dung_anh; dùng làm ETag khi phục vụ.';


--
-- Name: COLUMN banner_trang_chu.thu_tu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.banner_trang_chu.thu_tu IS 'Thứ tự hiển thị trong bộ ảnh, số nhỏ đứng trước; ảnh đầu là ảnh đại diện.';


--
-- Name: COLUMN banner_trang_chu.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.banner_trang_chu.thoi_diem_tao IS 'Thời điểm tải ảnh lên.';


--
-- Name: COLUMN banner_trang_chu.id_banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.banner_trang_chu.id_banner_trang_chu IS 'Định danh nội bộ PostgreSQL cấp, dùng trên đường dẫn ảnh banner.';


--
-- Name: COLUMN banner_trang_chu.tieu_de; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.banner_trang_chu.tieu_de IS 'Tiêu đề lớn của banner; một dòng.';


--
-- Name: COLUMN banner_trang_chu.mo_ta; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.banner_trang_chu.mo_ta IS 'Câu mô tả ngắn dưới tiêu đề; một dòng, rỗng khi không cần.';


--
-- Name: COLUMN banner_trang_chu.nhan_nut; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.banner_trang_chu.nhan_nut IS 'Chữ trên nút hành động của banner; một dòng.';


--
-- Name: COLUMN banner_trang_chu.duong_dan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.banner_trang_chu.duong_dan IS 'Đường dẫn nội bộ bắt đầu bằng / mà nút banner mở; không nhận liên kết ngoài.';


--
-- Name: COLUMN banner_trang_chu.mau_nen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.banner_trang_chu.mau_nen IS 'Màu nền khối hero khi banner hiện, dạng #rrggbb chữ thường.';


--
-- Name: COLUMN banner_trang_chu.nguon_anh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.banner_trang_chu.nguon_anh IS 'Nguồn và giấy phép của ảnh (ví dụ StockSnap, CC0); rỗng khi ảnh tự tạo.';


--
-- Name: COLUMN banner_trang_chu.dang_hien_thi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.banner_trang_chu.dang_hien_thi IS 'Quản trị tắt để ẩn banner mà không xóa.';


--
-- Name: COLUMN banner_trang_chu.ngay_bat_dau; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.banner_trang_chu.ngay_bat_dau IS 'Ngày bắt đầu hiện; NULL là hiện ngay.';


--
-- Name: COLUMN banner_trang_chu.ngay_ket_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.banner_trang_chu.ngay_ket_thuc IS 'Ngày cuối cùng hiện; NULL là không hẹn ngày kết thúc.';


--
-- Name: CONSTRAINT kiem_tra__banner__bam_sha256_da_cat_khoang_trang ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__bam_sha256_da_cat_khoang_trang ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(bam_sha256))';


--
-- Name: CONSTRAINT kiem_tra__banner__bam_sha256_dung_dinh_dang ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__bam_sha256_dung_dinh_dang ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((bam_sha256 ~ ''^[0-9a-f]{64}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__banner__bam_sha256_khong_rong ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__bam_sha256_khong_rong ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(bam_sha256))';


--
-- Name: CONSTRAINT kiem_tra__banner__bam_sha256_mot_dong ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__bam_sha256_mot_dong ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(bam_sha256))';


--
-- Name: CONSTRAINT kiem_tra__banner__duong_dan_da_cat_khoang_trang ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__duong_dan_da_cat_khoang_trang ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(duong_dan))';


--
-- Name: CONSTRAINT kiem_tra__banner__duong_dan_dung_dinh_dang ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__duong_dan_dung_dinh_dang ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((duong_dan ~ ''^/[A-Za-z0-9/_.?=&%-]*$''::text))';


--
-- Name: CONSTRAINT kiem_tra__banner__duong_dan_khong_rong ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__duong_dan_khong_rong ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(duong_dan))';


--
-- Name: CONSTRAINT kiem_tra__banner__duong_dan_mot_dong ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__duong_dan_mot_dong ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(duong_dan))';


--
-- Name: CONSTRAINT kiem_tra__banner__ket_thuc_sau_bat_dau ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__ket_thuc_sau_bat_dau ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((ngay_bat_dau IS NULL) OR (ngay_ket_thuc IS NULL) OR (ngay_ket_thuc >= ngay_bat_dau)))';


--
-- Name: CONSTRAINT kiem_tra__banner__kich_thuoc_anh_hop_le ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__kich_thuoc_anh_hop_le ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((chieu_rong >= 1) AND (chieu_rong <= 1600) AND (chieu_cao >= 1) AND (chieu_cao <= 1600)))';


--
-- Name: CONSTRAINT kiem_tra__banner__kich_thuoc_byte_khop ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__kich_thuoc_byte_khop ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((kich_thuoc_byte = octet_length(noi_dung_anh)) AND (kich_thuoc_byte >= 1) AND (kich_thuoc_byte <= 3145728)))';


--
-- Name: CONSTRAINT kiem_tra__banner__mau_nen_da_cat_khoang_trang ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__mau_nen_da_cat_khoang_trang ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(mau_nen))';


--
-- Name: CONSTRAINT kiem_tra__banner__mau_nen_dung_dinh_dang ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__mau_nen_dung_dinh_dang ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((mau_nen ~ ''^#[0-9a-f]{6}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__banner__mau_nen_khong_rong ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__mau_nen_khong_rong ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(mau_nen))';


--
-- Name: CONSTRAINT kiem_tra__banner__mau_nen_mot_dong ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__mau_nen_mot_dong ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(mau_nen))';


--
-- Name: CONSTRAINT kiem_tra__banner__mo_ta_da_cat_khoang_trang ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__mo_ta_da_cat_khoang_trang ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(mo_ta))';


--
-- Name: CONSTRAINT kiem_tra__banner__mo_ta_mot_dong ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__mo_ta_mot_dong ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(mo_ta))';


--
-- Name: CONSTRAINT kiem_tra__banner__nguon_anh_da_cat_khoang_trang ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__nguon_anh_da_cat_khoang_trang ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(nguon_anh))';


--
-- Name: CONSTRAINT kiem_tra__banner__nguon_anh_mot_dong ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__nguon_anh_mot_dong ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(nguon_anh))';


--
-- Name: CONSTRAINT kiem_tra__banner__nhan_nut_da_cat_khoang_trang ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__nhan_nut_da_cat_khoang_trang ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(nhan_nut))';


--
-- Name: CONSTRAINT kiem_tra__banner__nhan_nut_khong_rong ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__nhan_nut_khong_rong ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(nhan_nut))';


--
-- Name: CONSTRAINT kiem_tra__banner__nhan_nut_mot_dong ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__nhan_nut_mot_dong ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(nhan_nut))';


--
-- Name: CONSTRAINT kiem_tra__banner__thu_tu_khong_am ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__thu_tu_khong_am ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((thu_tu >= 0))';


--
-- Name: CONSTRAINT kiem_tra__banner__tieu_de_da_cat_khoang_trang ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__tieu_de_da_cat_khoang_trang ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(tieu_de))';


--
-- Name: CONSTRAINT kiem_tra__banner__tieu_de_khong_rong ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__tieu_de_khong_rong ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(tieu_de))';


--
-- Name: CONSTRAINT kiem_tra__banner__tieu_de_mot_dong ON banner_trang_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__banner__tieu_de_mot_dong ON public.banner_trang_chu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(tieu_de))';


--
-- Name: banner_trang_chu_id_banner_trang_chu_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.banner_trang_chu ALTER COLUMN id_banner_trang_chu ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.banner_trang_chu_id_banner_trang_chu_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: chi_nhanh; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chi_nhanh (
    id_chi_nhanh bigint NOT NULL,
    ma_chi_nhanh text NOT NULL,
    ten_chi_nhanh text NOT NULL,
    dia_chi text NOT NULL,
    vi_tri public.geography(Point,4326) NOT NULL,
    dang_hoat_dong boolean DEFAULT true NOT NULL,
    gio_dong_cua time without time zone DEFAULT '22:00:00'::time without time zone NOT NULL,
    gio_mo_cua time without time zone DEFAULT '07:00:00'::time without time zone NOT NULL,
    so_dien_thoai text DEFAULT ''::text NOT NULL,
    gioi_thieu text DEFAULT ''::text NOT NULL,
    CONSTRAINT kiem_tra__chi_nhanh__dia_chi_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(dia_chi)),
    CONSTRAINT kiem_tra__chi_nhanh__dia_chi_khong_rong CHECK (public.khong_rong(dia_chi)),
    CONSTRAINT kiem_tra__chi_nhanh__dia_chi_mot_dong CHECK (public.la_mot_dong(dia_chi)),
    CONSTRAINT kiem_tra__chi_nhanh__gio_dong_sau_gio_mo CHECK ((gio_dong_cua > gio_mo_cua)),
    CONSTRAINT kiem_tra__chi_nhanh__gioi_thieu_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(gioi_thieu)),
    CONSTRAINT kiem_tra__chi_nhanh__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_chi_nhanh)),
    CONSTRAINT kiem_tra__chi_nhanh__ma_dung_dinh_dang CHECK ((ma_chi_nhanh ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'::text)),
    CONSTRAINT kiem_tra__chi_nhanh__ma_khong_rong CHECK (public.khong_rong(ma_chi_nhanh)),
    CONSTRAINT kiem_tra__chi_nhanh__ma_mot_dong CHECK (public.la_mot_dong(ma_chi_nhanh)),
    CONSTRAINT kiem_tra__chi_nhanh__so_dien_thoai_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(so_dien_thoai)),
    CONSTRAINT kiem_tra__chi_nhanh__so_dien_thoai_dung_dinh_dang CHECK ((so_dien_thoai ~ '^((0(3[2-9]|5[2-9]|7[06-9]|8[1-9]|9[0-9])[0-9]{7}|02[0-9]{9}))?$'::text)),
    CONSTRAINT kiem_tra__chi_nhanh__so_dien_thoai_mot_dong CHECK (public.la_mot_dong(so_dien_thoai)),
    CONSTRAINT kiem_tra__chi_nhanh__ten_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ten_chi_nhanh)),
    CONSTRAINT kiem_tra__chi_nhanh__ten_khong_rong CHECK (public.khong_rong(ten_chi_nhanh)),
    CONSTRAINT kiem_tra__chi_nhanh__ten_mot_dong CHECK (public.la_mot_dong(ten_chi_nhanh))
);


--
-- Name: TABLE chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.chi_nhanh IS 'Mỗi hàng là một chi nhánh trong chuỗi mô phỏng.';


--
-- Name: COLUMN chi_nhanh.id_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_nhanh.id_chi_nhanh IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN chi_nhanh.ma_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_nhanh.ma_chi_nhanh IS 'Mã chi nhánh do quản trị nhập; văn bản một dòng.';


--
-- Name: COLUMN chi_nhanh.ten_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_nhanh.ten_chi_nhanh IS 'Tên hiển thị của cơ sở; văn bản một dòng.';


--
-- Name: COLUMN chi_nhanh.dia_chi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_nhanh.dia_chi IS 'Địa chỉ cơ sở do quản trị nhập; văn bản một dòng.';


--
-- Name: COLUMN chi_nhanh.vi_tri; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_nhanh.vi_tri IS 'Tọa độ kinh độ/vĩ độ WGS84 do quản trị nhập; điểm địa lý trên Trái Đất.';


--
-- Name: COLUMN chi_nhanh.dang_hoat_dong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_nhanh.dang_hoat_dong IS 'Chi nhánh đang tiếp nhận nghiệp vụ.';


--
-- Name: COLUMN chi_nhanh.gio_dong_cua; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_nhanh.gio_dong_cua IS 'Giờ đóng cửa hằng ngày theo giờ Việt Nam, sau giờ mở cửa.';


--
-- Name: COLUMN chi_nhanh.gio_mo_cua; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_nhanh.gio_mo_cua IS 'Giờ mở cửa hằng ngày theo giờ Việt Nam.';


--
-- Name: COLUMN chi_nhanh.so_dien_thoai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_nhanh.so_dien_thoai IS 'Số điện thoại của nhà thuốc, dạng nội địa; rỗng khi chưa có.';


--
-- Name: COLUMN chi_nhanh.gioi_thieu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_nhanh.gioi_thieu IS 'Giới thiệu chi nhánh hiển thị cho khách; HTML định dạng đã làm sạch bằng nh3.';


--
-- Name: CONSTRAINT kiem_tra__chi_nhanh__dia_chi_da_cat_khoang_trang ON chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__chi_nhanh__dia_chi_da_cat_khoang_trang ON public.chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(dia_chi))';


--
-- Name: CONSTRAINT kiem_tra__chi_nhanh__dia_chi_khong_rong ON chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__chi_nhanh__dia_chi_khong_rong ON public.chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(dia_chi))';


--
-- Name: CONSTRAINT kiem_tra__chi_nhanh__dia_chi_mot_dong ON chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__chi_nhanh__dia_chi_mot_dong ON public.chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(dia_chi))';


--
-- Name: CONSTRAINT kiem_tra__chi_nhanh__gio_dong_sau_gio_mo ON chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__chi_nhanh__gio_dong_sau_gio_mo ON public.chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((gio_dong_cua > gio_mo_cua))';


--
-- Name: CONSTRAINT kiem_tra__chi_nhanh__gioi_thieu_da_cat_khoang_trang ON chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__chi_nhanh__gioi_thieu_da_cat_khoang_trang ON public.chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(gioi_thieu))';


--
-- Name: CONSTRAINT kiem_tra__chi_nhanh__ma_da_cat_khoang_trang ON chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__chi_nhanh__ma_da_cat_khoang_trang ON public.chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_chi_nhanh))';


--
-- Name: CONSTRAINT kiem_tra__chi_nhanh__ma_dung_dinh_dang ON chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__chi_nhanh__ma_dung_dinh_dang ON public.chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_chi_nhanh ~ ''^[A-Z0-9][A-Z0-9_-]{0,31}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__chi_nhanh__ma_khong_rong ON chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__chi_nhanh__ma_khong_rong ON public.chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_chi_nhanh))';


--
-- Name: CONSTRAINT kiem_tra__chi_nhanh__ma_mot_dong ON chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__chi_nhanh__ma_mot_dong ON public.chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_chi_nhanh))';


--
-- Name: CONSTRAINT kiem_tra__chi_nhanh__so_dien_thoai_da_cat_khoang_trang ON chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__chi_nhanh__so_dien_thoai_da_cat_khoang_trang ON public.chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(so_dien_thoai))';


--
-- Name: CONSTRAINT kiem_tra__chi_nhanh__so_dien_thoai_dung_dinh_dang ON chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__chi_nhanh__so_dien_thoai_dung_dinh_dang ON public.chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((so_dien_thoai ~ ''^((0(3[2-9]|5[2-9]|7[06-9]|8[1-9]|9[0-9])[0-9]{7}|02[0-9]{9}))?$''::text))';


--
-- Name: CONSTRAINT kiem_tra__chi_nhanh__so_dien_thoai_mot_dong ON chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__chi_nhanh__so_dien_thoai_mot_dong ON public.chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(so_dien_thoai))';


--
-- Name: CONSTRAINT kiem_tra__chi_nhanh__ten_da_cat_khoang_trang ON chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__chi_nhanh__ten_da_cat_khoang_trang ON public.chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ten_chi_nhanh))';


--
-- Name: CONSTRAINT kiem_tra__chi_nhanh__ten_khong_rong ON chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__chi_nhanh__ten_khong_rong ON public.chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ten_chi_nhanh))';


--
-- Name: CONSTRAINT kiem_tra__chi_nhanh__ten_mot_dong ON chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__chi_nhanh__ten_mot_dong ON public.chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ten_chi_nhanh))';


--
-- Name: chi_nhanh_id_chi_nhanh_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.chi_nhanh ALTER COLUMN id_chi_nhanh ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.chi_nhanh_id_chi_nhanh_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: chi_tiet_don_hang; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chi_tiet_don_hang (
    id_chi_tiet_don_hang bigint NOT NULL,
    so_luong integer NOT NULL,
    gia_niem_yet numeric(14,0) NOT NULL,
    phan_tram_giam smallint DEFAULT 0 NOT NULL,
    don_gia numeric(14,0) NOT NULL,
    id_thuoc bigint NOT NULL,
    id_don_hang bigint NOT NULL,
    giam_gia_phan_bo numeric(14,0) DEFAULT 0 NOT NULL,
    CONSTRAINT kiem_tra__ct_don_hang__don_gia_khong_am CHECK ((don_gia >= (0)::numeric)),
    CONSTRAINT kiem_tra__ct_don_hang__don_gia_khong_phai_nan CHECK ((don_gia <> 'NaN'::numeric)),
    CONSTRAINT kiem_tra__ct_don_hang__gia_niem_yet_khong_am CHECK ((gia_niem_yet >= (0)::numeric)),
    CONSTRAINT kiem_tra__ct_don_hang__gia_niem_yet_khong_phai_nan CHECK ((gia_niem_yet <> 'NaN'::numeric)),
    CONSTRAINT kiem_tra__ct_don_hang__giam_gia_hop_le CHECK (((phan_tram_giam >= 0) AND (phan_tram_giam <= 90) AND (don_gia <= gia_niem_yet))),
    CONSTRAINT kiem_tra__ct_don_hang__giam_gia_phan_bo_khong_am CHECK ((giam_gia_phan_bo >= (0)::numeric)),
    CONSTRAINT kiem_tra__ct_don_hang__giam_gia_phan_bo_khong_phai_nan CHECK ((giam_gia_phan_bo <> 'NaN'::numeric)),
    CONSTRAINT kiem_tra__ct_don_hang__giam_khong_vuot_thanh_tien CHECK ((giam_gia_phan_bo <= ((so_luong)::numeric * don_gia))),
    CONSTRAINT kiem_tra__ct_don_hang__so_luong_duong CHECK ((so_luong > 0))
);


--
-- Name: TABLE chi_tiet_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.chi_tiet_don_hang IS 'Mỗi hàng là một thuốc trong đơn, kèm giá chụp lúc đặt.';


--
-- Name: COLUMN chi_tiet_don_hang.id_chi_tiet_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_don_hang.id_chi_tiet_don_hang IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN chi_tiet_don_hang.so_luong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_don_hang.so_luong IS 'Lượng cơ sở được yêu cầu; giới hạn số nguyên PostgreSQL 32 bit.';


--
-- Name: COLUMN chi_tiet_don_hang.gia_niem_yet; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_don_hang.gia_niem_yet IS 'Giá niêm yết một đơn vị cơ sở lúc đặt; VND nguyên, trần vận hành 14 chữ số theo quyết định Q02.';


--
-- Name: COLUMN chi_tiet_don_hang.phan_tram_giam; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_don_hang.phan_tram_giam IS 'Phần trăm khuyến mãi áp dụng lúc đặt, 0 khi không có.';


--
-- Name: COLUMN chi_tiet_don_hang.don_gia; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_don_hang.don_gia IS 'Giá một đơn vị cơ sở sau khuyến mãi lúc đặt; VND nguyên, trần vận hành 14 chữ số theo quyết định Q02.';


--
-- Name: COLUMN chi_tiet_don_hang.id_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_don_hang.id_thuoc IS 'Thuốc đúng sản phẩm khách yêu cầu.';


--
-- Name: COLUMN chi_tiet_don_hang.id_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_don_hang.id_don_hang IS 'Đơn sở hữu dòng.';


--
-- Name: COLUMN chi_tiet_don_hang.giam_gia_phan_bo; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_don_hang.giam_gia_phan_bo IS 'Phần giảm theo hạng thành viên của đơn phân bổ cho dòng theo tỷ lệ thành tiền, phần lẻ dồn vào dòng cuối; dòng thuốc kê đơn luôn 0. Tổng các dòng bằng giam_gia_thanh_vien; VND nguyên, trần vận hành 14 chữ số theo quyết định Q02.';


--
-- Name: CONSTRAINT kiem_tra__ct_don_hang__don_gia_khong_am ON chi_tiet_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_don_hang__don_gia_khong_am ON public.chi_tiet_don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((don_gia >= (0)::numeric))';


--
-- Name: CONSTRAINT kiem_tra__ct_don_hang__don_gia_khong_phai_nan ON chi_tiet_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_don_hang__don_gia_khong_phai_nan ON public.chi_tiet_don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((don_gia <> ''NaN''::numeric))';


--
-- Name: CONSTRAINT kiem_tra__ct_don_hang__gia_niem_yet_khong_am ON chi_tiet_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_don_hang__gia_niem_yet_khong_am ON public.chi_tiet_don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((gia_niem_yet >= (0)::numeric))';


--
-- Name: CONSTRAINT kiem_tra__ct_don_hang__gia_niem_yet_khong_phai_nan ON chi_tiet_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_don_hang__gia_niem_yet_khong_phai_nan ON public.chi_tiet_don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((gia_niem_yet <> ''NaN''::numeric))';


--
-- Name: CONSTRAINT kiem_tra__ct_don_hang__giam_gia_hop_le ON chi_tiet_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_don_hang__giam_gia_hop_le ON public.chi_tiet_don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((phan_tram_giam >= 0) AND (phan_tram_giam <= 90) AND (don_gia <= gia_niem_yet)))';


--
-- Name: CONSTRAINT kiem_tra__ct_don_hang__giam_gia_phan_bo_khong_am ON chi_tiet_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_don_hang__giam_gia_phan_bo_khong_am ON public.chi_tiet_don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((giam_gia_phan_bo >= (0)::numeric))';


--
-- Name: CONSTRAINT kiem_tra__ct_don_hang__giam_gia_phan_bo_khong_phai_nan ON chi_tiet_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_don_hang__giam_gia_phan_bo_khong_phai_nan ON public.chi_tiet_don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((giam_gia_phan_bo <> ''NaN''::numeric))';


--
-- Name: CONSTRAINT kiem_tra__ct_don_hang__giam_khong_vuot_thanh_tien ON chi_tiet_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_don_hang__giam_khong_vuot_thanh_tien ON public.chi_tiet_don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((giam_gia_phan_bo <= ((so_luong)::numeric * don_gia)))';


--
-- Name: CONSTRAINT kiem_tra__ct_don_hang__so_luong_duong ON chi_tiet_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_don_hang__so_luong_duong ON public.chi_tiet_don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((so_luong > 0))';


--
-- Name: chi_tiet_don_hang_id_chi_tiet_don_hang_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.chi_tiet_don_hang ALTER COLUMN id_chi_tiet_don_hang ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.chi_tiet_don_hang_id_chi_tiet_don_hang_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: chi_tiet_phieu_ban; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chi_tiet_phieu_ban (
    id_chi_tiet_phieu_ban bigint NOT NULL,
    ma_thuoc_luc_ban text NOT NULL,
    ten_thuoc_luc_ban text NOT NULL,
    so_luong integer NOT NULL,
    don_gia numeric(14,0) NOT NULL,
    id_thuoc bigint NOT NULL,
    id_phieu_ban bigint NOT NULL,
    giam_gia_phan_bo numeric(14,0) DEFAULT 0 NOT NULL,
    CONSTRAINT kiem_tra__ct_ban__don_gia_khong_am CHECK ((don_gia >= (0)::numeric)),
    CONSTRAINT kiem_tra__ct_ban__don_gia_khong_phai_nan CHECK ((don_gia <> 'NaN'::numeric)),
    CONSTRAINT kiem_tra__ct_ban__giam_gia_phan_bo_khong_am CHECK ((giam_gia_phan_bo >= (0)::numeric)),
    CONSTRAINT kiem_tra__ct_ban__giam_gia_phan_bo_khong_phai_nan CHECK ((giam_gia_phan_bo <> 'NaN'::numeric)),
    CONSTRAINT kiem_tra__ct_ban__giam_khong_vuot_thanh_tien CHECK ((giam_gia_phan_bo <= ((so_luong)::numeric * don_gia))),
    CONSTRAINT kiem_tra__ct_ban__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_thuoc_luc_ban)),
    CONSTRAINT kiem_tra__ct_ban__ma_dung_dinh_dang CHECK ((ma_thuoc_luc_ban ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'::text)),
    CONSTRAINT kiem_tra__ct_ban__ma_khong_rong CHECK (public.khong_rong(ma_thuoc_luc_ban)),
    CONSTRAINT kiem_tra__ct_ban__ma_mot_dong CHECK (public.la_mot_dong(ma_thuoc_luc_ban)),
    CONSTRAINT kiem_tra__ct_ban__so_luong_duong CHECK ((so_luong > 0)),
    CONSTRAINT kiem_tra__ct_ban__ten_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ten_thuoc_luc_ban)),
    CONSTRAINT kiem_tra__ct_ban__ten_khong_rong CHECK (public.khong_rong(ten_thuoc_luc_ban)),
    CONSTRAINT kiem_tra__ct_ban__ten_mot_dong CHECK (public.la_mot_dong(ten_thuoc_luc_ban))
);


--
-- Name: TABLE chi_tiet_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.chi_tiet_phieu_ban IS 'Mỗi hàng là một thuốc đã bán với giá và tên chụp tại quầy.';


--
-- Name: COLUMN chi_tiet_phieu_ban.id_chi_tiet_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_ban.id_chi_tiet_phieu_ban IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN chi_tiet_phieu_ban.ma_thuoc_luc_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_ban.ma_thuoc_luc_ban IS 'Mã sản phẩm được chụp khi bán; văn bản một dòng.';


--
-- Name: COLUMN chi_tiet_phieu_ban.ten_thuoc_luc_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_ban.ten_thuoc_luc_ban IS 'Tên sản phẩm được chụp khi bán; văn bản một dòng.';


--
-- Name: COLUMN chi_tiet_phieu_ban.so_luong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_ban.so_luong IS 'Lượng cơ sở bán; giới hạn số nguyên PostgreSQL 32 bit.';


--
-- Name: COLUMN chi_tiet_phieu_ban.don_gia; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_ban.don_gia IS 'Giá một đơn vị cơ sở khi xác nhận; VND nguyên, trần vận hành 14 chữ số theo quyết định Q02.';


--
-- Name: COLUMN chi_tiet_phieu_ban.id_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_ban.id_thuoc IS 'Sản phẩm được bán.';


--
-- Name: COLUMN chi_tiet_phieu_ban.id_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_ban.id_phieu_ban IS 'Phiếu bán.';


--
-- Name: COLUMN chi_tiet_phieu_ban.giam_gia_phan_bo; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_ban.giam_gia_phan_bo IS 'Ưu đãi thành viên của dòng chép từ dòng đơn khi xuất kho cho đơn; 0 khi bán trực tiếp. Doanh thu dòng sau ưu đãi bằng so_luong nhân don_gia trừ cột này; VND nguyên, trần vận hành 14 chữ số theo quyết định Q02.';


--
-- Name: CONSTRAINT kiem_tra__ct_ban__don_gia_khong_am ON chi_tiet_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_ban__don_gia_khong_am ON public.chi_tiet_phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((don_gia >= (0)::numeric))';


--
-- Name: CONSTRAINT kiem_tra__ct_ban__don_gia_khong_phai_nan ON chi_tiet_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_ban__don_gia_khong_phai_nan ON public.chi_tiet_phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((don_gia <> ''NaN''::numeric))';


--
-- Name: CONSTRAINT kiem_tra__ct_ban__giam_gia_phan_bo_khong_am ON chi_tiet_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_ban__giam_gia_phan_bo_khong_am ON public.chi_tiet_phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((giam_gia_phan_bo >= (0)::numeric))';


--
-- Name: CONSTRAINT kiem_tra__ct_ban__giam_gia_phan_bo_khong_phai_nan ON chi_tiet_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_ban__giam_gia_phan_bo_khong_phai_nan ON public.chi_tiet_phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((giam_gia_phan_bo <> ''NaN''::numeric))';


--
-- Name: CONSTRAINT kiem_tra__ct_ban__giam_khong_vuot_thanh_tien ON chi_tiet_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_ban__giam_khong_vuot_thanh_tien ON public.chi_tiet_phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((giam_gia_phan_bo <= ((so_luong)::numeric * don_gia)))';


--
-- Name: CONSTRAINT kiem_tra__ct_ban__ma_da_cat_khoang_trang ON chi_tiet_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_ban__ma_da_cat_khoang_trang ON public.chi_tiet_phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_thuoc_luc_ban))';


--
-- Name: CONSTRAINT kiem_tra__ct_ban__ma_dung_dinh_dang ON chi_tiet_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_ban__ma_dung_dinh_dang ON public.chi_tiet_phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_thuoc_luc_ban ~ ''^[A-Z0-9][A-Z0-9_-]{0,31}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__ct_ban__ma_khong_rong ON chi_tiet_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_ban__ma_khong_rong ON public.chi_tiet_phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_thuoc_luc_ban))';


--
-- Name: CONSTRAINT kiem_tra__ct_ban__ma_mot_dong ON chi_tiet_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_ban__ma_mot_dong ON public.chi_tiet_phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_thuoc_luc_ban))';


--
-- Name: CONSTRAINT kiem_tra__ct_ban__so_luong_duong ON chi_tiet_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_ban__so_luong_duong ON public.chi_tiet_phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((so_luong > 0))';


--
-- Name: CONSTRAINT kiem_tra__ct_ban__ten_da_cat_khoang_trang ON chi_tiet_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_ban__ten_da_cat_khoang_trang ON public.chi_tiet_phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ten_thuoc_luc_ban))';


--
-- Name: CONSTRAINT kiem_tra__ct_ban__ten_khong_rong ON chi_tiet_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_ban__ten_khong_rong ON public.chi_tiet_phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ten_thuoc_luc_ban))';


--
-- Name: CONSTRAINT kiem_tra__ct_ban__ten_mot_dong ON chi_tiet_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_ban__ten_mot_dong ON public.chi_tiet_phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ten_thuoc_luc_ban))';


--
-- Name: chi_tiet_phieu_ban_id_chi_tiet_phieu_ban_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.chi_tiet_phieu_ban ALTER COLUMN id_chi_tiet_phieu_ban ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.chi_tiet_phieu_ban_id_chi_tiet_phieu_ban_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: chi_tiet_phieu_dieu_chuyen; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chi_tiet_phieu_dieu_chuyen (
    id_chi_tiet_phieu_dieu_chuyen bigint CONSTRAINT chi_tiet_phieu_dieu_chuyen_id_chi_tiet_phieu_dieu_chuy_not_null NOT NULL,
    so_luong integer NOT NULL,
    id_lo_thuoc bigint NOT NULL,
    id_phieu_dieu_chuyen bigint NOT NULL,
    CONSTRAINT kiem_tra__ct_dieu_chuyen__so_luong_duong CHECK ((so_luong > 0))
);


--
-- Name: TABLE chi_tiet_phieu_dieu_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.chi_tiet_phieu_dieu_chuyen IS 'Mỗi hàng là lượng một lô đã chuyển giữa hai chi nhánh.';


--
-- Name: COLUMN chi_tiet_phieu_dieu_chuyen.id_chi_tiet_phieu_dieu_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_dieu_chuyen.id_chi_tiet_phieu_dieu_chuyen IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN chi_tiet_phieu_dieu_chuyen.so_luong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_dieu_chuyen.so_luong IS 'Lượng cơ sở chuyển; giới hạn số nguyên PostgreSQL 32 bit.';


--
-- Name: COLUMN chi_tiet_phieu_dieu_chuyen.id_lo_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_dieu_chuyen.id_lo_thuoc IS 'Lô được chuyển.';


--
-- Name: COLUMN chi_tiet_phieu_dieu_chuyen.id_phieu_dieu_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_dieu_chuyen.id_phieu_dieu_chuyen IS 'Chứng từ điều chuyển.';


--
-- Name: CONSTRAINT kiem_tra__ct_dieu_chuyen__so_luong_duong ON chi_tiet_phieu_dieu_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_dieu_chuyen__so_luong_duong ON public.chi_tiet_phieu_dieu_chuyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((so_luong > 0))';


--
-- Name: chi_tiet_phieu_dieu_chuyen_id_chi_tiet_phieu_dieu_chuyen_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.chi_tiet_phieu_dieu_chuyen ALTER COLUMN id_chi_tiet_phieu_dieu_chuyen ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.chi_tiet_phieu_dieu_chuyen_id_chi_tiet_phieu_dieu_chuyen_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: chi_tiet_phieu_kiem_ke; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chi_tiet_phieu_kiem_ke (
    id_chi_tiet_phieu_kiem_ke bigint NOT NULL,
    so_luong_so_sach integer NOT NULL,
    so_luong_thuc_te integer NOT NULL,
    id_lo_thuoc bigint NOT NULL,
    id_phieu_kiem_ke bigint NOT NULL,
    CONSTRAINT kiem_tra__ct_kiem_ke__so_luong_so_sach_khong_am CHECK ((so_luong_so_sach >= 0)),
    CONSTRAINT kiem_tra__ct_kiem_ke__so_luong_thuc_te_khong_am CHECK ((so_luong_thuc_te >= 0))
);


--
-- Name: TABLE chi_tiet_phieu_kiem_ke; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.chi_tiet_phieu_kiem_ke IS 'Mỗi hàng là kết quả đếm một lô và số dư được đối chiếu trong giao dịch.';


--
-- Name: COLUMN chi_tiet_phieu_kiem_ke.id_chi_tiet_phieu_kiem_ke; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_kiem_ke.id_chi_tiet_phieu_kiem_ke IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN chi_tiet_phieu_kiem_ke.so_luong_so_sach; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_kiem_ke.so_luong_so_sach IS 'Số dư ngay trước khi xác nhận; giới hạn số nguyên PostgreSQL 32 bit.';


--
-- Name: COLUMN chi_tiet_phieu_kiem_ke.so_luong_thuc_te; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_kiem_ke.so_luong_thuc_te IS 'Lượng cơ sở được đếm; giới hạn số nguyên PostgreSQL 32 bit.';


--
-- Name: COLUMN chi_tiet_phieu_kiem_ke.id_lo_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_kiem_ke.id_lo_thuoc IS 'Lô được đếm.';


--
-- Name: COLUMN chi_tiet_phieu_kiem_ke.id_phieu_kiem_ke; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_kiem_ke.id_phieu_kiem_ke IS 'Phiếu kiểm kê.';


--
-- Name: CONSTRAINT kiem_tra__ct_kiem_ke__so_luong_so_sach_khong_am ON chi_tiet_phieu_kiem_ke; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_kiem_ke__so_luong_so_sach_khong_am ON public.chi_tiet_phieu_kiem_ke IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((so_luong_so_sach >= 0))';


--
-- Name: CONSTRAINT kiem_tra__ct_kiem_ke__so_luong_thuc_te_khong_am ON chi_tiet_phieu_kiem_ke; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_kiem_ke__so_luong_thuc_te_khong_am ON public.chi_tiet_phieu_kiem_ke IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((so_luong_thuc_te >= 0))';


--
-- Name: chi_tiet_phieu_kiem_ke_id_chi_tiet_phieu_kiem_ke_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.chi_tiet_phieu_kiem_ke ALTER COLUMN id_chi_tiet_phieu_kiem_ke ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.chi_tiet_phieu_kiem_ke_id_chi_tiet_phieu_kiem_ke_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: chi_tiet_phieu_nhap; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chi_tiet_phieu_nhap (
    id_chi_tiet_phieu_nhap bigint NOT NULL,
    so_luong integer NOT NULL,
    don_gia numeric(14,0) NOT NULL,
    id_lo_thuoc bigint NOT NULL,
    id_phieu_nhap bigint NOT NULL,
    CONSTRAINT kiem_tra__ct_nhap__don_gia_khong_am CHECK ((don_gia >= (0)::numeric)),
    CONSTRAINT kiem_tra__ct_nhap__don_gia_khong_phai_nan CHECK ((don_gia <> 'NaN'::numeric)),
    CONSTRAINT kiem_tra__ct_nhap__so_luong_duong CHECK ((so_luong > 0))
);


--
-- Name: TABLE chi_tiet_phieu_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.chi_tiet_phieu_nhap IS 'Mỗi hàng là lượng nhập của một lô trong phiếu nhập.';


--
-- Name: COLUMN chi_tiet_phieu_nhap.id_chi_tiet_phieu_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_nhap.id_chi_tiet_phieu_nhap IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN chi_tiet_phieu_nhap.so_luong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_nhap.so_luong IS 'Lượng cơ sở nhập; giới hạn số nguyên PostgreSQL 32 bit.';


--
-- Name: COLUMN chi_tiet_phieu_nhap.don_gia; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_nhap.don_gia IS 'Giá nhập một đơn vị cơ sở; VND nguyên, trần vận hành 14 chữ số theo quyết định Q02.';


--
-- Name: COLUMN chi_tiet_phieu_nhap.id_lo_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_nhap.id_lo_thuoc IS 'Lô thực nhập.';


--
-- Name: COLUMN chi_tiet_phieu_nhap.id_phieu_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_nhap.id_phieu_nhap IS 'Phiếu nhập sở hữu dòng.';


--
-- Name: CONSTRAINT kiem_tra__ct_nhap__don_gia_khong_am ON chi_tiet_phieu_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_nhap__don_gia_khong_am ON public.chi_tiet_phieu_nhap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((don_gia >= (0)::numeric))';


--
-- Name: CONSTRAINT kiem_tra__ct_nhap__don_gia_khong_phai_nan ON chi_tiet_phieu_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_nhap__don_gia_khong_phai_nan ON public.chi_tiet_phieu_nhap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((don_gia <> ''NaN''::numeric))';


--
-- Name: CONSTRAINT kiem_tra__ct_nhap__so_luong_duong ON chi_tiet_phieu_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_nhap__so_luong_duong ON public.chi_tiet_phieu_nhap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((so_luong > 0))';


--
-- Name: chi_tiet_phieu_nhap_id_chi_tiet_phieu_nhap_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.chi_tiet_phieu_nhap ALTER COLUMN id_chi_tiet_phieu_nhap ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.chi_tiet_phieu_nhap_id_chi_tiet_phieu_nhap_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: chi_tiet_phieu_tra_nha_cung_cap; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chi_tiet_phieu_tra_nha_cung_cap (
    id_chi_tiet_phieu_tra_nha_cung_cap bigint CONSTRAINT chi_tiet_phieu_tra_nha_cung_id_chi_tiet_phieu_tra_nha__not_null NOT NULL,
    so_luong integer NOT NULL,
    id_lo_thuoc bigint NOT NULL,
    id_phieu_tra_nha_cung_cap bigint CONSTRAINT chi_tiet_phieu_tra_nha_cung__id_phieu_tra_nha_cung_cap_not_null NOT NULL,
    CONSTRAINT kiem_tra__ct_tra_ncc__so_luong_duong CHECK ((so_luong > 0))
);


--
-- Name: TABLE chi_tiet_phieu_tra_nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.chi_tiet_phieu_tra_nha_cung_cap IS 'Mỗi hàng là lượng trả của một lô đã nhập trong phiếu gốc.';


--
-- Name: COLUMN chi_tiet_phieu_tra_nha_cung_cap.id_chi_tiet_phieu_tra_nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_tra_nha_cung_cap.id_chi_tiet_phieu_tra_nha_cung_cap IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN chi_tiet_phieu_tra_nha_cung_cap.so_luong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_tra_nha_cung_cap.so_luong IS 'Lượng cơ sở trả; giới hạn số nguyên PostgreSQL 32 bit.';


--
-- Name: COLUMN chi_tiet_phieu_tra_nha_cung_cap.id_lo_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_tra_nha_cung_cap.id_lo_thuoc IS 'Lô trả đối tác.';


--
-- Name: COLUMN chi_tiet_phieu_tra_nha_cung_cap.id_phieu_tra_nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_tra_nha_cung_cap.id_phieu_tra_nha_cung_cap IS 'Chứng từ trả sở hữu dòng.';


--
-- Name: CONSTRAINT kiem_tra__ct_tra_ncc__so_luong_duong ON chi_tiet_phieu_tra_nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ct_tra_ncc__so_luong_duong ON public.chi_tiet_phieu_tra_nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((so_luong > 0))';


--
-- Name: chi_tiet_phieu_tra_nha_cung_c_id_chi_tiet_phieu_tra_nha_cun_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.chi_tiet_phieu_tra_nha_cung_cap ALTER COLUMN id_chi_tiet_phieu_tra_nha_cung_cap ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.chi_tiet_phieu_tra_nha_cung_c_id_chi_tiet_phieu_tra_nha_cun_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: chi_tiet_phieu_xuat_huy; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chi_tiet_phieu_xuat_huy (
    id_chi_tiet_phieu_xuat_huy bigint NOT NULL,
    so_luong integer NOT NULL,
    id_lo_thuoc bigint NOT NULL,
    id_phieu_xuat_huy bigint NOT NULL,
    CONSTRAINT kiem_tra__chi_tiet_phieu_xuat_huy__so_luong_duong CHECK ((so_luong > 0))
);


--
-- Name: TABLE chi_tiet_phieu_xuat_huy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.chi_tiet_phieu_xuat_huy IS 'Mỗi hàng là lượng một lô bị hủy trong phiếu xuất hủy.';


--
-- Name: COLUMN chi_tiet_phieu_xuat_huy.id_chi_tiet_phieu_xuat_huy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_xuat_huy.id_chi_tiet_phieu_xuat_huy IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN chi_tiet_phieu_xuat_huy.so_luong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_xuat_huy.so_luong IS 'Lượng cơ sở hủy; giới hạn số nguyên PostgreSQL 32 bit.';


--
-- Name: COLUMN chi_tiet_phieu_xuat_huy.id_lo_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_xuat_huy.id_lo_thuoc IS 'Lô bị hủy tại chi nhánh của phiếu.';


--
-- Name: COLUMN chi_tiet_phieu_xuat_huy.id_phieu_xuat_huy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chi_tiet_phieu_xuat_huy.id_phieu_xuat_huy IS 'Chứng từ xuất hủy sở hữu dòng.';


--
-- Name: CONSTRAINT kiem_tra__chi_tiet_phieu_xuat_huy__so_luong_duong ON chi_tiet_phieu_xuat_huy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__chi_tiet_phieu_xuat_huy__so_luong_duong ON public.chi_tiet_phieu_xuat_huy IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((so_luong > 0))';


--
-- Name: chi_tiet_phieu_xuat_huy_id_chi_tiet_phieu_xuat_huy_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.chi_tiet_phieu_xuat_huy ALTER COLUMN id_chi_tiet_phieu_xuat_huy ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.chi_tiet_phieu_xuat_huy_id_chi_tiet_phieu_xuat_huy_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: cuoc_tro_chuyen; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cuoc_tro_chuyen (
    id_cuoc_tro_chuyen bigint NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_chi_nhanh bigint NOT NULL,
    id_tai_khoan_khach bigint NOT NULL,
    id_tin_nhan_khach_da_doc bigint,
    id_tin_nhan_nha_thuoc_da_doc bigint,
    id_tai_khoan_danh_dau_xong bigint,
    thoi_diem_xong timestamp with time zone,
    id_tin_nhan_cuoi bigint,
    trang_thai_xu_ly text DEFAULT 'dang_mo'::text NOT NULL,
    CONSTRAINT kiem_tra__phong__trang_thai_hop_le CHECK ((trang_thai_xu_ly = ANY (ARRAY['dang_mo'::text, 'da_xong'::text]))),
    CONSTRAINT kiem_tra__phong__trang_thai_khop_moc_xong CHECK ((((id_tai_khoan_danh_dau_xong IS NULL) AND (thoi_diem_xong IS NULL) AND (trang_thai_xu_ly = 'dang_mo'::text)) OR ((id_tai_khoan_danh_dau_xong IS NOT NULL) AND (thoi_diem_xong IS NOT NULL) AND (trang_thai_xu_ly = 'da_xong'::text)))),
    CONSTRAINT kiem_tra__phong__trang_thai_xu_ly_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(trang_thai_xu_ly)),
    CONSTRAINT kiem_tra__phong__trang_thai_xu_ly_khong_rong CHECK (public.khong_rong(trang_thai_xu_ly)),
    CONSTRAINT kiem_tra__phong__trang_thai_xu_ly_mot_dong CHECK (public.la_mot_dong(trang_thai_xu_ly))
);


--
-- Name: TABLE cuoc_tro_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.cuoc_tro_chuyen IS 'Mỗi hàng là cuộc trò chuyện duy nhất của một khách với một chi nhánh, giữ toàn bộ lịch sử hỏi tư vấn, sản phẩm và đơn hàng.';


--
-- Name: COLUMN cuoc_tro_chuyen.id_cuoc_tro_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.cuoc_tro_chuyen.id_cuoc_tro_chuyen IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN cuoc_tro_chuyen.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.cuoc_tro_chuyen.thoi_diem_tao IS 'Thời điểm hệ thống ghi nhận nghiệp vụ.';


--
-- Name: COLUMN cuoc_tro_chuyen.id_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.cuoc_tro_chuyen.id_chi_nhanh IS 'Chi nhánh trả lời. Mọi câu hỏi của khách với chi nhánh (tư vấn, sản phẩm, đơn hàng) nằm chung một cuộc trò chuyện; thẻ sản phẩm/đơn gắn ở từng tin.';


--
-- Name: COLUMN cuoc_tro_chuyen.id_tai_khoan_khach; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.cuoc_tro_chuyen.id_tai_khoan_khach IS 'Khách sở hữu cuộc trò chuyện.';


--
-- Name: COLUMN cuoc_tro_chuyen.id_tin_nhan_khach_da_doc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.cuoc_tro_chuyen.id_tin_nhan_khach_da_doc IS 'Tin mới nhất khách đã xem; tin của nhà thuốc có id lớn hơn là chưa đọc. NULL khi khách chưa mở phòng. Service chỉ cho tăng và chỉ trỏ tin trong phòng.';


--
-- Name: COLUMN cuoc_tro_chuyen.id_tin_nhan_nha_thuoc_da_doc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.cuoc_tro_chuyen.id_tin_nhan_nha_thuoc_da_doc IS 'Tin mới nhất phía nhà thuốc đã xem (bất kỳ nhân sự nào của chi nhánh mở phòng); tin của khách có id lớn hơn là chưa đọc.';


--
-- Name: COLUMN cuoc_tro_chuyen.id_tai_khoan_danh_dau_xong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.cuoc_tro_chuyen.id_tai_khoan_danh_dau_xong IS 'Nhân sự đánh dấu đã xong; NULL khi đang trao đổi.';


--
-- Name: COLUMN cuoc_tro_chuyen.thoi_diem_xong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.cuoc_tro_chuyen.thoi_diem_xong IS 'Lúc đánh dấu đã xong; NULL khi đang trao đổi.';


--
-- Name: COLUMN cuoc_tro_chuyen.id_tin_nhan_cuoi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.cuoc_tro_chuyen.id_tin_nhan_cuoi IS 'Tin mới nhất của phòng, service cập nhật trong cùng giao dịch ghi tin. Lưu sẵn để hộp thư hàng nghìn phòng sắp xếp, lọc Chờ trả lời bằng chỉ mục thay vì quét tin_nhan. Phòng chỉ được tạo cùng tin đầu tiên nên NULL chỉ còn ở dữ liệu cũ.';


--
-- Name: COLUMN cuoc_tro_chuyen.trang_thai_xu_ly; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.cuoc_tro_chuyen.trang_thai_xu_ly IS 'dang_mo: còn cần theo dõi; da_xong: nhân sự đánh dấu đã giải quyết. Khách gửi tin mới thì phòng tự mở lại.';


--
-- Name: CONSTRAINT kiem_tra__phong__trang_thai_hop_le ON cuoc_tro_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phong__trang_thai_hop_le ON public.cuoc_tro_chuyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((trang_thai_xu_ly = ANY (ARRAY[''dang_mo''::text, ''da_xong''::text])))';


--
-- Name: CONSTRAINT kiem_tra__phong__trang_thai_khop_moc_xong ON cuoc_tro_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phong__trang_thai_khop_moc_xong ON public.cuoc_tro_chuyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((((id_tai_khoan_danh_dau_xong IS NULL) AND (thoi_diem_xong IS NULL) AND (trang_thai_xu_ly = ''dang_mo''::text)) OR ((id_tai_khoan_danh_dau_xong IS NOT NULL) AND (thoi_diem_xong IS NOT NULL) AND (trang_thai_xu_ly = ''da_xong''::text))))';


--
-- Name: CONSTRAINT kiem_tra__phong__trang_thai_xu_ly_da_cat_khoang_trang ON cuoc_tro_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phong__trang_thai_xu_ly_da_cat_khoang_trang ON public.cuoc_tro_chuyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(trang_thai_xu_ly))';


--
-- Name: CONSTRAINT kiem_tra__phong__trang_thai_xu_ly_khong_rong ON cuoc_tro_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phong__trang_thai_xu_ly_khong_rong ON public.cuoc_tro_chuyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(trang_thai_xu_ly))';


--
-- Name: CONSTRAINT kiem_tra__phong__trang_thai_xu_ly_mot_dong ON cuoc_tro_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phong__trang_thai_xu_ly_mot_dong ON public.cuoc_tro_chuyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(trang_thai_xu_ly))';


--
-- Name: cuoc_tro_chuyen_id_cuoc_tro_chuyen_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.cuoc_tro_chuyen ALTER COLUMN id_cuoc_tro_chuyen ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.cuoc_tro_chuyen_id_cuoc_tro_chuyen_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: danh_gia_chi_nhanh; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.danh_gia_chi_nhanh (
    id_danh_gia_chi_nhanh bigint NOT NULL,
    so_sao smallint NOT NULL,
    noi_dung_danh_gia text DEFAULT ''::text NOT NULL,
    dang_hien_thi boolean DEFAULT true NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_chi_nhanh bigint NOT NULL,
    id_tai_khoan_khach bigint NOT NULL,
    CONSTRAINT kiem_tra__danh_gia_chi_nhanh__noi_dung_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(noi_dung_danh_gia)),
    CONSTRAINT kiem_tra__danh_gia_chi_nhanh__so_sao_hop_le CHECK (((so_sao >= 1) AND (so_sao <= 5)))
);


--
-- Name: TABLE danh_gia_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.danh_gia_chi_nhanh IS 'Mỗi hàng là đánh giá của một khách cho một chi nhánh đã mua hàng.';


--
-- Name: COLUMN danh_gia_chi_nhanh.id_danh_gia_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.danh_gia_chi_nhanh.id_danh_gia_chi_nhanh IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN danh_gia_chi_nhanh.so_sao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.danh_gia_chi_nhanh.so_sao IS 'Điểm từ 1 đến 5 sao do khách chọn.';


--
-- Name: COLUMN danh_gia_chi_nhanh.noi_dung_danh_gia; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.danh_gia_chi_nhanh.noi_dung_danh_gia IS 'Nhận xét về phục vụ, tư vấn, giao nhận; nhiều dòng, rỗng khi chỉ chấm sao.';


--
-- Name: COLUMN danh_gia_chi_nhanh.dang_hien_thi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.danh_gia_chi_nhanh.dang_hien_thi IS 'Quản trị ẩn nhận xét vi phạm (quảng cáo, thông tin cá nhân) mà không xóa.';


--
-- Name: COLUMN danh_gia_chi_nhanh.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.danh_gia_chi_nhanh.thoi_diem_tao IS 'Lần khách gửi hoặc sửa đánh giá.';


--
-- Name: COLUMN danh_gia_chi_nhanh.id_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.danh_gia_chi_nhanh.id_chi_nhanh IS 'Chi nhánh được đánh giá.';


--
-- Name: COLUMN danh_gia_chi_nhanh.id_tai_khoan_khach; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.danh_gia_chi_nhanh.id_tai_khoan_khach IS 'Khách có đơn hoàn thành tại chi nhánh; mỗi khách một đánh giá cho một chi nhánh.';


--
-- Name: CONSTRAINT kiem_tra__danh_gia_chi_nhanh__noi_dung_da_cat_khoang_trang ON danh_gia_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__danh_gia_chi_nhanh__noi_dung_da_cat_khoang_trang ON public.danh_gia_chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(noi_dung_danh_gia))';


--
-- Name: CONSTRAINT kiem_tra__danh_gia_chi_nhanh__so_sao_hop_le ON danh_gia_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__danh_gia_chi_nhanh__so_sao_hop_le ON public.danh_gia_chi_nhanh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((so_sao >= 1) AND (so_sao <= 5)))';


--
-- Name: danh_gia_chi_nhanh_id_danh_gia_chi_nhanh_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.danh_gia_chi_nhanh ALTER COLUMN id_danh_gia_chi_nhanh ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.danh_gia_chi_nhanh_id_danh_gia_chi_nhanh_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: danh_gia_thuoc; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.danh_gia_thuoc (
    id_danh_gia_thuoc bigint NOT NULL,
    so_sao smallint NOT NULL,
    noi_dung_danh_gia text DEFAULT ''::text NOT NULL,
    dang_hien_thi boolean DEFAULT true NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_tai_khoan_khach bigint NOT NULL,
    id_thuoc bigint NOT NULL,
    CONSTRAINT kiem_tra__danh_gia_thuoc__noi_dung_danh_gia_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(noi_dung_danh_gia)),
    CONSTRAINT kiem_tra__danh_gia_thuoc__so_sao_hop_le CHECK (((so_sao >= 1) AND (so_sao <= 5)))
);


--
-- Name: TABLE danh_gia_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.danh_gia_thuoc IS 'Mỗi hàng là đánh giá của một khách cho một thuốc đã mua.';


--
-- Name: COLUMN danh_gia_thuoc.id_danh_gia_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.danh_gia_thuoc.id_danh_gia_thuoc IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN danh_gia_thuoc.so_sao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.danh_gia_thuoc.so_sao IS 'Điểm từ 1 đến 5 sao do khách chọn.';


--
-- Name: COLUMN danh_gia_thuoc.noi_dung_danh_gia; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.danh_gia_thuoc.noi_dung_danh_gia IS 'Nhận xét của khách; văn bản nhiều dòng, rỗng khi chỉ chấm sao.';


--
-- Name: COLUMN danh_gia_thuoc.dang_hien_thi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.danh_gia_thuoc.dang_hien_thi IS 'Quản trị ẩn nhận xét vi phạm (quảng cáo, thông tin cá nhân) mà không xóa.';


--
-- Name: COLUMN danh_gia_thuoc.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.danh_gia_thuoc.thoi_diem_tao IS 'Lần khách gửi hoặc sửa đánh giá.';


--
-- Name: COLUMN danh_gia_thuoc.id_tai_khoan_khach; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.danh_gia_thuoc.id_tai_khoan_khach IS 'Khách đã nhận thuốc qua đơn hoàn thành; mỗi khách một đánh giá cho một thuốc.';


--
-- Name: COLUMN danh_gia_thuoc.id_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.danh_gia_thuoc.id_thuoc IS 'Thuốc được đánh giá.';


--
-- Name: CONSTRAINT kiem_tra__danh_gia_thuoc__noi_dung_danh_gia_da_cat_khoang_trang ON danh_gia_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__danh_gia_thuoc__noi_dung_danh_gia_da_cat_khoang_trang ON public.danh_gia_thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(noi_dung_danh_gia))';


--
-- Name: CONSTRAINT kiem_tra__danh_gia_thuoc__so_sao_hop_le ON danh_gia_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__danh_gia_thuoc__so_sao_hop_le ON public.danh_gia_thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((so_sao >= 1) AND (so_sao <= 5)))';


--
-- Name: danh_gia_thuoc_id_danh_gia_thuoc_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.danh_gia_thuoc ALTER COLUMN id_danh_gia_thuoc ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.danh_gia_thuoc_id_danh_gia_thuoc_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: danh_muc_san_pham; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.danh_muc_san_pham (
    id_danh_muc_san_pham bigint NOT NULL,
    ma_danh_muc_san_pham text NOT NULL,
    ten_danh_muc_san_pham text NOT NULL,
    mo_ta text DEFAULT ''::text NOT NULL,
    bieu_tuong text DEFAULT 'pill'::text NOT NULL,
    thu_tu smallint DEFAULT 0 NOT NULL,
    dang_hien_thi boolean DEFAULT true NOT NULL,
    CONSTRAINT kiem_tra__danh_muc_san_pham__bieu_tuong_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(bieu_tuong)),
    CONSTRAINT kiem_tra__danh_muc_san_pham__bieu_tuong_dung_dinh_dang CHECK ((bieu_tuong ~ '^[a-z0-9]+(-[a-z0-9]+)*$'::text)),
    CONSTRAINT kiem_tra__danh_muc_san_pham__bieu_tuong_khong_rong CHECK (public.khong_rong(bieu_tuong)),
    CONSTRAINT kiem_tra__danh_muc_san_pham__bieu_tuong_mot_dong CHECK (public.la_mot_dong(bieu_tuong)),
    CONSTRAINT kiem_tra__danh_muc_san_pham__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_danh_muc_san_pham)),
    CONSTRAINT kiem_tra__danh_muc_san_pham__ma_dung_dinh_dang CHECK ((ma_danh_muc_san_pham ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'::text)),
    CONSTRAINT kiem_tra__danh_muc_san_pham__ma_khong_rong CHECK (public.khong_rong(ma_danh_muc_san_pham)),
    CONSTRAINT kiem_tra__danh_muc_san_pham__ma_mot_dong CHECK (public.la_mot_dong(ma_danh_muc_san_pham)),
    CONSTRAINT kiem_tra__danh_muc_san_pham__mo_ta_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(mo_ta)),
    CONSTRAINT kiem_tra__danh_muc_san_pham__mo_ta_mot_dong CHECK (public.la_mot_dong(mo_ta)),
    CONSTRAINT kiem_tra__danh_muc_san_pham__ten_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ten_danh_muc_san_pham)),
    CONSTRAINT kiem_tra__danh_muc_san_pham__ten_khong_rong CHECK (public.khong_rong(ten_danh_muc_san_pham)),
    CONSTRAINT kiem_tra__danh_muc_san_pham__ten_mot_dong CHECK (public.la_mot_dong(ten_danh_muc_san_pham)),
    CONSTRAINT kiem_tra__danh_muc_san_pham__thu_tu_khong_am CHECK ((thu_tu >= 0))
);


--
-- Name: TABLE danh_muc_san_pham; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.danh_muc_san_pham IS 'Mỗi hàng là một nhóm sản phẩm khách dùng để duyệt website.';


--
-- Name: COLUMN danh_muc_san_pham.id_danh_muc_san_pham; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.danh_muc_san_pham.id_danh_muc_san_pham IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN danh_muc_san_pham.ma_danh_muc_san_pham; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.danh_muc_san_pham.ma_danh_muc_san_pham IS 'Mã danh mục do quản trị nhập, dùng trên đường dẫn lọc.';


--
-- Name: COLUMN danh_muc_san_pham.ten_danh_muc_san_pham; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.danh_muc_san_pham.ten_danh_muc_san_pham IS 'Tên danh mục hiển thị cho khách, ví dụ giảm đau hạ sốt; một dòng.';


--
-- Name: COLUMN danh_muc_san_pham.mo_ta; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.danh_muc_san_pham.mo_ta IS 'Mô tả ngắn của danh mục; văn bản một dòng, có thể rỗng.';


--
-- Name: COLUMN danh_muc_san_pham.bieu_tuong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.danh_muc_san_pham.bieu_tuong IS 'Tên biểu tượng Lucide hiển thị cạnh danh mục, chữ thường và gạch ngang.';


--
-- Name: COLUMN danh_muc_san_pham.thu_tu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.danh_muc_san_pham.thu_tu IS 'Thứ tự hiển thị, số nhỏ đứng trước.';


--
-- Name: COLUMN danh_muc_san_pham.dang_hien_thi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.danh_muc_san_pham.dang_hien_thi IS 'Danh mục đang hiện trên website khách.';


--
-- Name: CONSTRAINT kiem_tra__danh_muc_san_pham__bieu_tuong_da_cat_khoang_trang ON danh_muc_san_pham; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__danh_muc_san_pham__bieu_tuong_da_cat_khoang_trang ON public.danh_muc_san_pham IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(bieu_tuong))';


--
-- Name: CONSTRAINT kiem_tra__danh_muc_san_pham__bieu_tuong_dung_dinh_dang ON danh_muc_san_pham; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__danh_muc_san_pham__bieu_tuong_dung_dinh_dang ON public.danh_muc_san_pham IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((bieu_tuong ~ ''^[a-z0-9]+(-[a-z0-9]+)*$''::text))';


--
-- Name: CONSTRAINT kiem_tra__danh_muc_san_pham__bieu_tuong_khong_rong ON danh_muc_san_pham; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__danh_muc_san_pham__bieu_tuong_khong_rong ON public.danh_muc_san_pham IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(bieu_tuong))';


--
-- Name: CONSTRAINT kiem_tra__danh_muc_san_pham__bieu_tuong_mot_dong ON danh_muc_san_pham; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__danh_muc_san_pham__bieu_tuong_mot_dong ON public.danh_muc_san_pham IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(bieu_tuong))';


--
-- Name: CONSTRAINT kiem_tra__danh_muc_san_pham__ma_da_cat_khoang_trang ON danh_muc_san_pham; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__danh_muc_san_pham__ma_da_cat_khoang_trang ON public.danh_muc_san_pham IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_danh_muc_san_pham))';


--
-- Name: CONSTRAINT kiem_tra__danh_muc_san_pham__ma_dung_dinh_dang ON danh_muc_san_pham; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__danh_muc_san_pham__ma_dung_dinh_dang ON public.danh_muc_san_pham IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_danh_muc_san_pham ~ ''^[A-Z0-9][A-Z0-9_-]{0,31}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__danh_muc_san_pham__ma_khong_rong ON danh_muc_san_pham; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__danh_muc_san_pham__ma_khong_rong ON public.danh_muc_san_pham IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_danh_muc_san_pham))';


--
-- Name: CONSTRAINT kiem_tra__danh_muc_san_pham__ma_mot_dong ON danh_muc_san_pham; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__danh_muc_san_pham__ma_mot_dong ON public.danh_muc_san_pham IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_danh_muc_san_pham))';


--
-- Name: CONSTRAINT kiem_tra__danh_muc_san_pham__mo_ta_da_cat_khoang_trang ON danh_muc_san_pham; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__danh_muc_san_pham__mo_ta_da_cat_khoang_trang ON public.danh_muc_san_pham IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(mo_ta))';


--
-- Name: CONSTRAINT kiem_tra__danh_muc_san_pham__mo_ta_mot_dong ON danh_muc_san_pham; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__danh_muc_san_pham__mo_ta_mot_dong ON public.danh_muc_san_pham IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(mo_ta))';


--
-- Name: CONSTRAINT kiem_tra__danh_muc_san_pham__ten_da_cat_khoang_trang ON danh_muc_san_pham; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__danh_muc_san_pham__ten_da_cat_khoang_trang ON public.danh_muc_san_pham IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ten_danh_muc_san_pham))';


--
-- Name: CONSTRAINT kiem_tra__danh_muc_san_pham__ten_khong_rong ON danh_muc_san_pham; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__danh_muc_san_pham__ten_khong_rong ON public.danh_muc_san_pham IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ten_danh_muc_san_pham))';


--
-- Name: CONSTRAINT kiem_tra__danh_muc_san_pham__ten_mot_dong ON danh_muc_san_pham; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__danh_muc_san_pham__ten_mot_dong ON public.danh_muc_san_pham IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ten_danh_muc_san_pham))';


--
-- Name: CONSTRAINT kiem_tra__danh_muc_san_pham__thu_tu_khong_am ON danh_muc_san_pham; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__danh_muc_san_pham__thu_tu_khong_am ON public.danh_muc_san_pham IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((thu_tu >= 0))';


--
-- Name: danh_muc_san_pham_id_danh_muc_san_pham_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.danh_muc_san_pham ALTER COLUMN id_danh_muc_san_pham ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.danh_muc_san_pham_id_danh_muc_san_pham_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


--
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.django_content_type ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_content_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.django_migrations (
    id bigint NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


--
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.django_migrations ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_migrations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_session; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


--
-- Name: don_hang; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.don_hang (
    id_don_hang bigint NOT NULL,
    ma_don_hang text NOT NULL,
    trang_thai text DEFAULT 'dang_giu'::text NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    thoi_diem_het_giu timestamp with time zone NOT NULL,
    tien_hang numeric(14,0) DEFAULT 0 NOT NULL,
    giam_gia_thanh_vien numeric(14,0) DEFAULT 0 NOT NULL,
    tong_thanh_toan numeric(14,0) DEFAULT 0 NOT NULL,
    ghi_chu_khach text DEFAULT ''::text NOT NULL,
    id_chi_nhanh bigint NOT NULL,
    id_tai_khoan_khach bigint NOT NULL,
    CONSTRAINT kiem_tra__don_hang__ghi_chu_khach_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ghi_chu_khach)),
    CONSTRAINT kiem_tra__don_hang__ghi_chu_khach_mot_dong CHECK (public.la_mot_dong(ghi_chu_khach)),
    CONSTRAINT kiem_tra__don_hang__giam_gia_thanh_vien_khong_am CHECK ((giam_gia_thanh_vien >= (0)::numeric)),
    CONSTRAINT kiem_tra__don_hang__giam_gia_thanh_vien_khong_phai_nan CHECK ((giam_gia_thanh_vien <> 'NaN'::numeric)),
    CONSTRAINT kiem_tra__don_hang__het_giu_sau_khi_tao CHECK ((thoi_diem_het_giu > thoi_diem_tao)),
    CONSTRAINT kiem_tra__don_hang__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_don_hang)),
    CONSTRAINT kiem_tra__don_hang__ma_dung_dinh_dang CHECK ((ma_don_hang ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'::text)),
    CONSTRAINT kiem_tra__don_hang__ma_khong_rong CHECK (public.khong_rong(ma_don_hang)),
    CONSTRAINT kiem_tra__don_hang__ma_mot_dong CHECK (public.la_mot_dong(ma_don_hang)),
    CONSTRAINT kiem_tra__don_hang__tien_hang_khong_am CHECK ((tien_hang >= (0)::numeric)),
    CONSTRAINT kiem_tra__don_hang__tien_hang_khong_phai_nan CHECK ((tien_hang <> 'NaN'::numeric)),
    CONSTRAINT kiem_tra__don_hang__tong_dung_cong_thuc CHECK (((tong_thanh_toan = (tien_hang - giam_gia_thanh_vien)) AND (giam_gia_thanh_vien <= tien_hang))),
    CONSTRAINT kiem_tra__don_hang__tong_thanh_toan_khong_am CHECK ((tong_thanh_toan >= (0)::numeric)),
    CONSTRAINT kiem_tra__don_hang__tong_thanh_toan_khong_phai_nan CHECK ((tong_thanh_toan <> 'NaN'::numeric)),
    CONSTRAINT kiem_tra__don_hang__trang_thai_hop_le CHECK ((trang_thai = ANY (ARRAY['dang_giu'::text, 'hoan_thanh'::text, 'da_huy'::text, 'het_han'::text])))
);


--
-- Name: TABLE don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.don_hang IS 'Mỗi hàng là một đơn đặt giữ của khách ở một chi nhánh; khách nhận và trả tiền tại quầy.';


--
-- Name: COLUMN don_hang.id_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.don_hang.id_don_hang IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN don_hang.ma_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.don_hang.ma_don_hang IS 'Mã đơn hệ thống cấp; văn bản một dòng.';


--
-- Name: COLUMN don_hang.trang_thai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.don_hang.trang_thai IS 'Trạng thái xử lý; chỉ service đổi theo bảng chuyển hợp lệ và ghi lich_su_don_hang: dang_giu, hoan_thanh (khách đã nhận và trả tiền tại quầy), da_huy, het_han.';


--
-- Name: COLUMN don_hang.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.don_hang.thoi_diem_tao IS 'Thời điểm khách đặt đơn.';


--
-- Name: COLUMN don_hang.thoi_diem_het_giu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.don_hang.thoi_diem_het_giu IS 'Hạn của lượng giữ hàng, 24 giờ sau khi đặt; quá hạn thì đơn hết hạn.';


--
-- Name: COLUMN don_hang.tien_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.don_hang.tien_hang IS 'Tổng thành tiền các dòng sau khuyến mãi; VND nguyên, trần vận hành 14 chữ số theo quyết định Q02.';


--
-- Name: COLUMN don_hang.giam_gia_thanh_vien; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.don_hang.giam_gia_thanh_vien IS 'Giảm theo hạng thành viên khi đặt; VND nguyên, trần vận hành 14 chữ số theo quyết định Q02.';


--
-- Name: COLUMN don_hang.tong_thanh_toan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.don_hang.tong_thanh_toan IS 'Số tiền khách trả tại quầy, bằng tiền hàng trừ giảm giá thành viên; VND nguyên, trần vận hành 14 chữ số theo quyết định Q02.';


--
-- Name: COLUMN don_hang.ghi_chu_khach; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.don_hang.ghi_chu_khach IS 'Lời nhắn của khách cho nhà thuốc; một dòng, có thể rỗng.';


--
-- Name: COLUMN don_hang.id_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.don_hang.id_chi_nhanh IS 'Chi nhánh duy nhất giữ hàng, nơi khách đến nhận và trả tiền.';


--
-- Name: COLUMN don_hang.id_tai_khoan_khach; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.don_hang.id_tai_khoan_khach IS 'Khách sở hữu đơn.';


--
-- Name: CONSTRAINT kiem_tra__don_hang__ghi_chu_khach_da_cat_khoang_trang ON don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_hang__ghi_chu_khach_da_cat_khoang_trang ON public.don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ghi_chu_khach))';


--
-- Name: CONSTRAINT kiem_tra__don_hang__ghi_chu_khach_mot_dong ON don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_hang__ghi_chu_khach_mot_dong ON public.don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ghi_chu_khach))';


--
-- Name: CONSTRAINT kiem_tra__don_hang__giam_gia_thanh_vien_khong_am ON don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_hang__giam_gia_thanh_vien_khong_am ON public.don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((giam_gia_thanh_vien >= (0)::numeric))';


--
-- Name: CONSTRAINT kiem_tra__don_hang__giam_gia_thanh_vien_khong_phai_nan ON don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_hang__giam_gia_thanh_vien_khong_phai_nan ON public.don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((giam_gia_thanh_vien <> ''NaN''::numeric))';


--
-- Name: CONSTRAINT kiem_tra__don_hang__het_giu_sau_khi_tao ON don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_hang__het_giu_sau_khi_tao ON public.don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((thoi_diem_het_giu > thoi_diem_tao))';


--
-- Name: CONSTRAINT kiem_tra__don_hang__ma_da_cat_khoang_trang ON don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_hang__ma_da_cat_khoang_trang ON public.don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_don_hang))';


--
-- Name: CONSTRAINT kiem_tra__don_hang__ma_dung_dinh_dang ON don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_hang__ma_dung_dinh_dang ON public.don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_don_hang ~ ''^[A-Z0-9][A-Z0-9_-]{0,31}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__don_hang__ma_khong_rong ON don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_hang__ma_khong_rong ON public.don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_don_hang))';


--
-- Name: CONSTRAINT kiem_tra__don_hang__ma_mot_dong ON don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_hang__ma_mot_dong ON public.don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_don_hang))';


--
-- Name: CONSTRAINT kiem_tra__don_hang__tien_hang_khong_am ON don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_hang__tien_hang_khong_am ON public.don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((tien_hang >= (0)::numeric))';


--
-- Name: CONSTRAINT kiem_tra__don_hang__tien_hang_khong_phai_nan ON don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_hang__tien_hang_khong_phai_nan ON public.don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((tien_hang <> ''NaN''::numeric))';


--
-- Name: CONSTRAINT kiem_tra__don_hang__tong_dung_cong_thuc ON don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_hang__tong_dung_cong_thuc ON public.don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((tong_thanh_toan = (tien_hang - giam_gia_thanh_vien)) AND (giam_gia_thanh_vien <= tien_hang)))';


--
-- Name: CONSTRAINT kiem_tra__don_hang__tong_thanh_toan_khong_am ON don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_hang__tong_thanh_toan_khong_am ON public.don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((tong_thanh_toan >= (0)::numeric))';


--
-- Name: CONSTRAINT kiem_tra__don_hang__tong_thanh_toan_khong_phai_nan ON don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_hang__tong_thanh_toan_khong_phai_nan ON public.don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((tong_thanh_toan <> ''NaN''::numeric))';


--
-- Name: CONSTRAINT kiem_tra__don_hang__trang_thai_hop_le ON don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_hang__trang_thai_hop_le ON public.don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((trang_thai = ANY (ARRAY[''dang_giu''::text, ''hoan_thanh''::text, ''da_huy''::text, ''het_han''::text])))';


--
-- Name: don_hang_id_don_hang_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.don_hang ALTER COLUMN id_don_hang ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.don_hang_id_don_hang_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: don_vi_tinh; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.don_vi_tinh (
    id_don_vi_tinh bigint NOT NULL,
    ma_don_vi_tinh text NOT NULL,
    ten_don_vi_tinh text NOT NULL,
    CONSTRAINT kiem_tra__don_vi_tinh__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_don_vi_tinh)),
    CONSTRAINT kiem_tra__don_vi_tinh__ma_dung_dinh_dang CHECK ((ma_don_vi_tinh ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'::text)),
    CONSTRAINT kiem_tra__don_vi_tinh__ma_khong_rong CHECK (public.khong_rong(ma_don_vi_tinh)),
    CONSTRAINT kiem_tra__don_vi_tinh__ma_mot_dong CHECK (public.la_mot_dong(ma_don_vi_tinh)),
    CONSTRAINT kiem_tra__don_vi_tinh__ten_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ten_don_vi_tinh)),
    CONSTRAINT kiem_tra__don_vi_tinh__ten_khong_rong CHECK (public.khong_rong(ten_don_vi_tinh)),
    CONSTRAINT kiem_tra__don_vi_tinh__ten_mot_dong CHECK (public.la_mot_dong(ten_don_vi_tinh))
);


--
-- Name: TABLE don_vi_tinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.don_vi_tinh IS 'Mỗi hàng là một đơn vị cơ sở có cùng nghĩa trong hệ thống.';


--
-- Name: COLUMN don_vi_tinh.id_don_vi_tinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.don_vi_tinh.id_don_vi_tinh IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN don_vi_tinh.ma_don_vi_tinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.don_vi_tinh.ma_don_vi_tinh IS 'Mã đơn vị; văn bản một dòng.';


--
-- Name: COLUMN don_vi_tinh.ten_don_vi_tinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.don_vi_tinh.ten_don_vi_tinh IS 'Tên đơn vị cơ sở; văn bản một dòng.';


--
-- Name: CONSTRAINT kiem_tra__don_vi_tinh__ma_da_cat_khoang_trang ON don_vi_tinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_vi_tinh__ma_da_cat_khoang_trang ON public.don_vi_tinh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_don_vi_tinh))';


--
-- Name: CONSTRAINT kiem_tra__don_vi_tinh__ma_dung_dinh_dang ON don_vi_tinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_vi_tinh__ma_dung_dinh_dang ON public.don_vi_tinh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_don_vi_tinh ~ ''^[A-Z0-9][A-Z0-9_-]{0,31}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__don_vi_tinh__ma_khong_rong ON don_vi_tinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_vi_tinh__ma_khong_rong ON public.don_vi_tinh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_don_vi_tinh))';


--
-- Name: CONSTRAINT kiem_tra__don_vi_tinh__ma_mot_dong ON don_vi_tinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_vi_tinh__ma_mot_dong ON public.don_vi_tinh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_don_vi_tinh))';


--
-- Name: CONSTRAINT kiem_tra__don_vi_tinh__ten_da_cat_khoang_trang ON don_vi_tinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_vi_tinh__ten_da_cat_khoang_trang ON public.don_vi_tinh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ten_don_vi_tinh))';


--
-- Name: CONSTRAINT kiem_tra__don_vi_tinh__ten_khong_rong ON don_vi_tinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_vi_tinh__ten_khong_rong ON public.don_vi_tinh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ten_don_vi_tinh))';


--
-- Name: CONSTRAINT kiem_tra__don_vi_tinh__ten_mot_dong ON don_vi_tinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__don_vi_tinh__ten_mot_dong ON public.don_vi_tinh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ten_don_vi_tinh))';


--
-- Name: don_vi_tinh_id_don_vi_tinh_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.don_vi_tinh ALTER COLUMN id_don_vi_tinh ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.don_vi_tinh_id_don_vi_tinh_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: du_bao_bay_ngay; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.du_bao_bay_ngay (
    id_du_bao_bay_ngay bigint NOT NULL,
    ngay_goc date NOT NULL,
    ky_danh_gia text NOT NULL,
    so_luong_du_bao double precision NOT NULL,
    so_luong_thuc_te double precision,
    id_ket_qua_mo_hinh bigint NOT NULL,
    CONSTRAINT kiem_tra__du_bao__du_bao_huu_han CHECK (((so_luong_du_bao >= (0.0)::double precision) AND (so_luong_du_bao < 'Infinity'::double precision))),
    CONSTRAINT kiem_tra__du_bao__ky_danh_gia_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ky_danh_gia)),
    CONSTRAINT kiem_tra__du_bao__ky_danh_gia_khong_rong CHECK (public.khong_rong(ky_danh_gia)),
    CONSTRAINT kiem_tra__du_bao__ky_danh_gia_mot_dong CHECK (public.la_mot_dong(ky_danh_gia)),
    CONSTRAINT kiem_tra__du_bao__ky_hop_le CHECK ((ky_danh_gia = ANY (ARRAY['xac_thuc'::text, 'kiem_thu'::text, 'tuong_lai'::text]))),
    CONSTRAINT kiem_tra__du_bao__thuc_te_dung_ky CHECK ((((ky_danh_gia = 'tuong_lai'::text) AND (so_luong_thuc_te IS NULL)) OR ((NOT (ky_danh_gia = 'tuong_lai'::text)) AND (so_luong_thuc_te IS NOT NULL)))),
    CONSTRAINT kiem_tra__du_bao__thuc_te_huu_han CHECK (((so_luong_thuc_te >= (0.0)::double precision) AND (so_luong_thuc_te < 'Infinity'::double precision)))
);


--
-- Name: TABLE du_bao_bay_ngay; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.du_bao_bay_ngay IS 'Mỗi hàng là tổng lượng dự báo bảy ngày sau một ngày gốc, có đối chiếu khi đã có nhãn.';


--
-- Name: COLUMN du_bao_bay_ngay.id_du_bao_bay_ngay; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.du_bao_bay_ngay.id_du_bao_bay_ngay IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN du_bao_bay_ngay.ngay_goc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.du_bao_bay_ngay.ngay_goc IS 'Thông tin quan sát chỉ đến hết ngày này.';


--
-- Name: COLUMN du_bao_bay_ngay.ky_danh_gia; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.du_bao_bay_ngay.ky_danh_gia IS 'xac_thuc, kiem_thu hoặc tuong_lai; dự báo tổng 7 ngày sau ngày gốc; văn bản một dòng.';


--
-- Name: COLUMN du_bao_bay_ngay.so_luong_du_bao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.du_bao_bay_ngay.so_luong_du_bao IS 'Lượng dự báo đã chặn dưới tại 0 trước tính metric; giá trị xấp xỉ, đơn vị theo nguồn công khai.';


--
-- Name: COLUMN du_bao_bay_ngay.so_luong_thuc_te; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.du_bao_bay_ngay.so_luong_thuc_te IS 'Tổng lượng 7 ngày tương lai để đánh giá; giá trị xấp xỉ, đơn vị theo nguồn công khai. NULL nghĩa là tương lai chưa có thực tế.';


--
-- Name: COLUMN du_bao_bay_ngay.id_ket_qua_mo_hinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.du_bao_bay_ngay.id_ket_qua_mo_hinh IS 'Mô hình và phiên bản nguồn đã đánh giá.';


--
-- Name: CONSTRAINT kiem_tra__du_bao__du_bao_huu_han ON du_bao_bay_ngay; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__du_bao__du_bao_huu_han ON public.du_bao_bay_ngay IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((so_luong_du_bao >= (0.0)::double precision) AND (so_luong_du_bao < ''Infinity''::double precision)))';


--
-- Name: CONSTRAINT kiem_tra__du_bao__ky_danh_gia_da_cat_khoang_trang ON du_bao_bay_ngay; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__du_bao__ky_danh_gia_da_cat_khoang_trang ON public.du_bao_bay_ngay IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ky_danh_gia))';


--
-- Name: CONSTRAINT kiem_tra__du_bao__ky_danh_gia_khong_rong ON du_bao_bay_ngay; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__du_bao__ky_danh_gia_khong_rong ON public.du_bao_bay_ngay IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ky_danh_gia))';


--
-- Name: CONSTRAINT kiem_tra__du_bao__ky_danh_gia_mot_dong ON du_bao_bay_ngay; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__du_bao__ky_danh_gia_mot_dong ON public.du_bao_bay_ngay IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ky_danh_gia))';


--
-- Name: CONSTRAINT kiem_tra__du_bao__ky_hop_le ON du_bao_bay_ngay; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__du_bao__ky_hop_le ON public.du_bao_bay_ngay IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ky_danh_gia = ANY (ARRAY[''xac_thuc''::text, ''kiem_thu''::text, ''tuong_lai''::text])))';


--
-- Name: CONSTRAINT kiem_tra__du_bao__thuc_te_dung_ky ON du_bao_bay_ngay; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__du_bao__thuc_te_dung_ky ON public.du_bao_bay_ngay IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((((ky_danh_gia = ''tuong_lai''::text) AND (so_luong_thuc_te IS NULL)) OR ((NOT (ky_danh_gia = ''tuong_lai''::text)) AND (so_luong_thuc_te IS NOT NULL))))';


--
-- Name: CONSTRAINT kiem_tra__du_bao__thuc_te_huu_han ON du_bao_bay_ngay; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__du_bao__thuc_te_huu_han ON public.du_bao_bay_ngay IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((so_luong_thuc_te >= (0.0)::double precision) AND (so_luong_thuc_te < ''Infinity''::double precision)))';


--
-- Name: du_bao_bay_ngay_id_du_bao_bay_ngay_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.du_bao_bay_ngay ALTER COLUMN id_du_bao_bay_ngay ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.du_bao_bay_ngay_id_du_bao_bay_ngay_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: ket_qua_mo_hinh; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ket_qua_mo_hinh (
    id_ket_qua_mo_hinh bigint NOT NULL,
    ma_atc_nguon text NOT NULL,
    mo_hinh text NOT NULL,
    mae_xac_thuc double precision NOT NULL,
    rmse_xac_thuc double precision NOT NULL,
    mae_kiem_thu double precision NOT NULL,
    rmse_kiem_thu double precision NOT NULL,
    duoc_chon boolean DEFAULT false NOT NULL,
    id_lan_thuc_nghiem bigint NOT NULL,
    CONSTRAINT kiem_tra__ket_qua__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_atc_nguon)),
    CONSTRAINT kiem_tra__ket_qua__ma_dung_dinh_dang CHECK ((ma_atc_nguon ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'::text)),
    CONSTRAINT kiem_tra__ket_qua__ma_khong_rong CHECK (public.khong_rong(ma_atc_nguon)),
    CONSTRAINT kiem_tra__ket_qua__ma_mot_dong CHECK (public.la_mot_dong(ma_atc_nguon)),
    CONSTRAINT kiem_tra__ket_qua__mae_kiem_thu_huu_han CHECK (((mae_kiem_thu >= (0.0)::double precision) AND (mae_kiem_thu < 'Infinity'::double precision))),
    CONSTRAINT kiem_tra__ket_qua__mae_xac_thuc_huu_han CHECK (((mae_xac_thuc >= (0.0)::double precision) AND (mae_xac_thuc < 'Infinity'::double precision))),
    CONSTRAINT kiem_tra__ket_qua__mo_hinh_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(mo_hinh)),
    CONSTRAINT kiem_tra__ket_qua__mo_hinh_hop_le CHECK ((mo_hinh = ANY (ARRAY['hoi_quy_tuyen_tinh'::text, 'cay_quyet_dinh'::text, 'rung_ngau_nhien'::text, 'xgboost'::text, 'sarimax'::text]))),
    CONSTRAINT kiem_tra__ket_qua__mo_hinh_khong_rong CHECK (public.khong_rong(mo_hinh)),
    CONSTRAINT kiem_tra__ket_qua__mo_hinh_mot_dong CHECK (public.la_mot_dong(mo_hinh)),
    CONSTRAINT kiem_tra__ket_qua__rmse_kiem_thu_huu_han CHECK (((rmse_kiem_thu >= (0.0)::double precision) AND (rmse_kiem_thu < 'Infinity'::double precision))),
    CONSTRAINT kiem_tra__ket_qua__rmse_xac_thuc_huu_han CHECK (((rmse_xac_thuc >= (0.0)::double precision) AND (rmse_xac_thuc < 'Infinity'::double precision)))
);


--
-- Name: TABLE ket_qua_mo_hinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.ket_qua_mo_hinh IS 'Mỗi hàng là sai số của một trong năm mô hình theo nhóm ATC.';


--
-- Name: COLUMN ket_qua_mo_hinh.id_ket_qua_mo_hinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ket_qua_mo_hinh.id_ket_qua_mo_hinh IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN ket_qua_mo_hinh.ma_atc_nguon; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ket_qua_mo_hinh.ma_atc_nguon IS 'Nhóm ATC của kết quả; văn bản một dòng.';


--
-- Name: COLUMN ket_qua_mo_hinh.mo_hinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ket_qua_mo_hinh.mo_hinh IS 'Phương pháp dự báo: hoi_quy_tuyen_tinh, cay_quyet_dinh, rung_ngau_nhien, xgboost hoặc sarimax; văn bản một dòng.';


--
-- Name: COLUMN ket_qua_mo_hinh.mae_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ket_qua_mo_hinh.mae_xac_thuc IS 'MAE trên tập xác thực do chương trình tính; giá trị xấp xỉ, đơn vị theo nguồn công khai.';


--
-- Name: COLUMN ket_qua_mo_hinh.rmse_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ket_qua_mo_hinh.rmse_xac_thuc IS 'RMSE trên tập xác thực do chương trình tính; giá trị xấp xỉ, đơn vị theo nguồn công khai.';


--
-- Name: COLUMN ket_qua_mo_hinh.mae_kiem_thu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ket_qua_mo_hinh.mae_kiem_thu IS 'MAE trên tập kiểm thử do chương trình tính; giá trị xấp xỉ, đơn vị theo nguồn công khai.';


--
-- Name: COLUMN ket_qua_mo_hinh.rmse_kiem_thu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ket_qua_mo_hinh.rmse_kiem_thu IS 'RMSE trên tập kiểm thử do chương trình tính; giá trị xấp xỉ, đơn vị theo nguồn công khai.';


--
-- Name: COLUMN ket_qua_mo_hinh.duoc_chon; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ket_qua_mo_hinh.duoc_chon IS 'Mô hình được chọn bằng sai số trên tập xác thực.';


--
-- Name: COLUMN ket_qua_mo_hinh.id_lan_thuc_nghiem; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ket_qua_mo_hinh.id_lan_thuc_nghiem IS 'Lần chạy sở hữu kết quả.';


--
-- Name: CONSTRAINT kiem_tra__ket_qua__ma_da_cat_khoang_trang ON ket_qua_mo_hinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ket_qua__ma_da_cat_khoang_trang ON public.ket_qua_mo_hinh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_atc_nguon))';


--
-- Name: CONSTRAINT kiem_tra__ket_qua__ma_dung_dinh_dang ON ket_qua_mo_hinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ket_qua__ma_dung_dinh_dang ON public.ket_qua_mo_hinh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_atc_nguon ~ ''^[A-Z0-9][A-Z0-9_-]{0,31}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__ket_qua__ma_khong_rong ON ket_qua_mo_hinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ket_qua__ma_khong_rong ON public.ket_qua_mo_hinh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_atc_nguon))';


--
-- Name: CONSTRAINT kiem_tra__ket_qua__ma_mot_dong ON ket_qua_mo_hinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ket_qua__ma_mot_dong ON public.ket_qua_mo_hinh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_atc_nguon))';


--
-- Name: CONSTRAINT kiem_tra__ket_qua__mae_kiem_thu_huu_han ON ket_qua_mo_hinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ket_qua__mae_kiem_thu_huu_han ON public.ket_qua_mo_hinh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((mae_kiem_thu >= (0.0)::double precision) AND (mae_kiem_thu < ''Infinity''::double precision)))';


--
-- Name: CONSTRAINT kiem_tra__ket_qua__mae_xac_thuc_huu_han ON ket_qua_mo_hinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ket_qua__mae_xac_thuc_huu_han ON public.ket_qua_mo_hinh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((mae_xac_thuc >= (0.0)::double precision) AND (mae_xac_thuc < ''Infinity''::double precision)))';


--
-- Name: CONSTRAINT kiem_tra__ket_qua__mo_hinh_da_cat_khoang_trang ON ket_qua_mo_hinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ket_qua__mo_hinh_da_cat_khoang_trang ON public.ket_qua_mo_hinh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(mo_hinh))';


--
-- Name: CONSTRAINT kiem_tra__ket_qua__mo_hinh_hop_le ON ket_qua_mo_hinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ket_qua__mo_hinh_hop_le ON public.ket_qua_mo_hinh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((mo_hinh = ANY (ARRAY[''hoi_quy_tuyen_tinh''::text, ''cay_quyet_dinh''::text, ''rung_ngau_nhien''::text, ''xgboost''::text, ''sarimax''::text])))';


--
-- Name: CONSTRAINT kiem_tra__ket_qua__mo_hinh_khong_rong ON ket_qua_mo_hinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ket_qua__mo_hinh_khong_rong ON public.ket_qua_mo_hinh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(mo_hinh))';


--
-- Name: CONSTRAINT kiem_tra__ket_qua__mo_hinh_mot_dong ON ket_qua_mo_hinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ket_qua__mo_hinh_mot_dong ON public.ket_qua_mo_hinh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(mo_hinh))';


--
-- Name: CONSTRAINT kiem_tra__ket_qua__rmse_kiem_thu_huu_han ON ket_qua_mo_hinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ket_qua__rmse_kiem_thu_huu_han ON public.ket_qua_mo_hinh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((rmse_kiem_thu >= (0.0)::double precision) AND (rmse_kiem_thu < ''Infinity''::double precision)))';


--
-- Name: CONSTRAINT kiem_tra__ket_qua__rmse_xac_thuc_huu_han ON ket_qua_mo_hinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ket_qua__rmse_xac_thuc_huu_han ON public.ket_qua_mo_hinh IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((rmse_xac_thuc >= (0.0)::double precision) AND (rmse_xac_thuc < ''Infinity''::double precision)))';


--
-- Name: ket_qua_mo_hinh_id_ket_qua_mo_hinh_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.ket_qua_mo_hinh ALTER COLUMN id_ket_qua_mo_hinh ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.ket_qua_mo_hinh_id_ket_qua_mo_hinh_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: khuyen_mai; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.khuyen_mai (
    id_khuyen_mai bigint NOT NULL,
    ma_khuyen_mai text NOT NULL,
    ten_khuyen_mai text NOT NULL,
    phan_tram_giam smallint NOT NULL,
    ngay_bat_dau date NOT NULL,
    ngay_ket_thuc date NOT NULL,
    dang_hoat_dong boolean DEFAULT true NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_thuoc bigint NOT NULL,
    CONSTRAINT kiem_tra__khuyen_mai__ket_thuc_sau_bat_dau CHECK ((ngay_ket_thuc >= ngay_bat_dau)),
    CONSTRAINT kiem_tra__khuyen_mai__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_khuyen_mai)),
    CONSTRAINT kiem_tra__khuyen_mai__ma_dung_dinh_dang CHECK ((ma_khuyen_mai ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'::text)),
    CONSTRAINT kiem_tra__khuyen_mai__ma_khong_rong CHECK (public.khong_rong(ma_khuyen_mai)),
    CONSTRAINT kiem_tra__khuyen_mai__ma_mot_dong CHECK (public.la_mot_dong(ma_khuyen_mai)),
    CONSTRAINT kiem_tra__khuyen_mai__phan_tram_giam_hop_le CHECK (((phan_tram_giam >= 1) AND (phan_tram_giam <= 90))),
    CONSTRAINT kiem_tra__khuyen_mai__ten_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ten_khuyen_mai)),
    CONSTRAINT kiem_tra__khuyen_mai__ten_khong_rong CHECK (public.khong_rong(ten_khuyen_mai)),
    CONSTRAINT kiem_tra__khuyen_mai__ten_mot_dong CHECK (public.la_mot_dong(ten_khuyen_mai))
);


--
-- Name: TABLE khuyen_mai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.khuyen_mai IS 'Mỗi hàng là một đợt giảm giá theo phần trăm cho một thuốc; service không cho hai đợt đang hoạt động của cùng thuốc trùng ngày.';


--
-- Name: COLUMN khuyen_mai.id_khuyen_mai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.khuyen_mai.id_khuyen_mai IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN khuyen_mai.ma_khuyen_mai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.khuyen_mai.ma_khuyen_mai IS 'Mã chương trình do quản trị nhập.';


--
-- Name: COLUMN khuyen_mai.ten_khuyen_mai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.khuyen_mai.ten_khuyen_mai IS 'Tên chương trình hiển thị cho khách; một dòng.';


--
-- Name: COLUMN khuyen_mai.phan_tram_giam; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.khuyen_mai.phan_tram_giam IS 'Phần trăm giảm trên giá bán. Chương trình mới giới hạn từ 1 đến 50; giá trị 51 đến 90 chỉ giữ cho bản ghi cũ.';


--
-- Name: COLUMN khuyen_mai.ngay_bat_dau; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.khuyen_mai.ngay_bat_dau IS 'Ngày đầu áp dụng, tính theo giờ Việt Nam.';


--
-- Name: COLUMN khuyen_mai.ngay_ket_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.khuyen_mai.ngay_ket_thuc IS 'Ngày cuối áp dụng, tính cả ngày này.';


--
-- Name: COLUMN khuyen_mai.dang_hoat_dong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.khuyen_mai.dang_hoat_dong IS 'Quản trị có thể dừng chương trình trước hạn; không xóa để giữ lịch sử.';


--
-- Name: COLUMN khuyen_mai.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.khuyen_mai.thoi_diem_tao IS 'Thời điểm tạo chương trình.';


--
-- Name: COLUMN khuyen_mai.id_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.khuyen_mai.id_thuoc IS 'Thuốc được giảm giá.';


--
-- Name: CONSTRAINT kiem_tra__khuyen_mai__ket_thuc_sau_bat_dau ON khuyen_mai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__khuyen_mai__ket_thuc_sau_bat_dau ON public.khuyen_mai IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ngay_ket_thuc >= ngay_bat_dau))';


--
-- Name: CONSTRAINT kiem_tra__khuyen_mai__ma_da_cat_khoang_trang ON khuyen_mai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__khuyen_mai__ma_da_cat_khoang_trang ON public.khuyen_mai IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_khuyen_mai))';


--
-- Name: CONSTRAINT kiem_tra__khuyen_mai__ma_dung_dinh_dang ON khuyen_mai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__khuyen_mai__ma_dung_dinh_dang ON public.khuyen_mai IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_khuyen_mai ~ ''^[A-Z0-9][A-Z0-9_-]{0,31}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__khuyen_mai__ma_khong_rong ON khuyen_mai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__khuyen_mai__ma_khong_rong ON public.khuyen_mai IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_khuyen_mai))';


--
-- Name: CONSTRAINT kiem_tra__khuyen_mai__ma_mot_dong ON khuyen_mai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__khuyen_mai__ma_mot_dong ON public.khuyen_mai IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_khuyen_mai))';


--
-- Name: CONSTRAINT kiem_tra__khuyen_mai__phan_tram_giam_hop_le ON khuyen_mai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__khuyen_mai__phan_tram_giam_hop_le ON public.khuyen_mai IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((phan_tram_giam >= 1) AND (phan_tram_giam <= 90)))';


--
-- Name: CONSTRAINT kiem_tra__khuyen_mai__ten_da_cat_khoang_trang ON khuyen_mai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__khuyen_mai__ten_da_cat_khoang_trang ON public.khuyen_mai IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ten_khuyen_mai))';


--
-- Name: CONSTRAINT kiem_tra__khuyen_mai__ten_khong_rong ON khuyen_mai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__khuyen_mai__ten_khong_rong ON public.khuyen_mai IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ten_khuyen_mai))';


--
-- Name: CONSTRAINT kiem_tra__khuyen_mai__ten_mot_dong ON khuyen_mai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__khuyen_mai__ten_mot_dong ON public.khuyen_mai IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ten_khuyen_mai))';


--
-- Name: khuyen_mai_id_khuyen_mai_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.khuyen_mai ALTER COLUMN id_khuyen_mai ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.khuyen_mai_id_khuyen_mai_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: kich_ban_thieu_hang; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.kich_ban_thieu_hang (
    id_kich_ban_thieu_hang bigint NOT NULL,
    so_luong_ton double precision NOT NULL,
    so_luong_dang_giu double precision NOT NULL,
    so_luong_du_tru double precision NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_du_bao_bay_ngay bigint NOT NULL,
    CONSTRAINT kiem_tra__kich_ban_thieu_hang__giu_khong_vuot_ton CHECK ((so_luong_dang_giu <= so_luong_ton)),
    CONSTRAINT kiem_tra__kich_ban_thieu_hang__so_luong_dang_giu_khong_am CHECK (((so_luong_dang_giu >= (0.0)::double precision) AND (so_luong_dang_giu < 'Infinity'::double precision))),
    CONSTRAINT kiem_tra__kich_ban_thieu_hang__so_luong_du_tru_khong_am CHECK (((so_luong_du_tru >= (0.0)::double precision) AND (so_luong_du_tru < 'Infinity'::double precision))),
    CONSTRAINT kiem_tra__kich_ban_thieu_hang__so_luong_ton_khong_am CHECK (((so_luong_ton >= (0.0)::double precision) AND (so_luong_ton < 'Infinity'::double precision)))
);


--
-- Name: TABLE kich_ban_thieu_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.kich_ban_thieu_hang IS 'Mỗi hàng là kịch bản minh họa riêng theo đơn vị dữ liệu công khai; không tác động kho mô phỏng.';


--
-- Name: COLUMN kich_ban_thieu_hang.id_kich_ban_thieu_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.kich_ban_thieu_hang.id_kich_ban_thieu_hang IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN kich_ban_thieu_hang.so_luong_ton; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.kich_ban_thieu_hang.so_luong_ton IS 'Tồn giả định do người quản lý nhập; giá trị xấp xỉ, đơn vị theo nguồn công khai.';


--
-- Name: COLUMN kich_ban_thieu_hang.so_luong_dang_giu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.kich_ban_thieu_hang.so_luong_dang_giu IS 'Lượng giữ giả định do người quản lý nhập; giá trị xấp xỉ, đơn vị theo nguồn công khai.';


--
-- Name: COLUMN kich_ban_thieu_hang.so_luong_du_tru; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.kich_ban_thieu_hang.so_luong_du_tru IS 'Dự trữ giả định do người quản lý nhập; giá trị xấp xỉ, đơn vị theo nguồn công khai.';


--
-- Name: COLUMN kich_ban_thieu_hang.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.kich_ban_thieu_hang.thoi_diem_tao IS 'Thời điểm hệ thống ghi nhận nghiệp vụ.';


--
-- Name: COLUMN kich_ban_thieu_hang.id_du_bao_bay_ngay; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.kich_ban_thieu_hang.id_du_bao_bay_ngay IS 'Dự báo 7 ngày được dùng minh họa.';


--
-- Name: CONSTRAINT kiem_tra__kich_ban_thieu_hang__giu_khong_vuot_ton ON kich_ban_thieu_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__kich_ban_thieu_hang__giu_khong_vuot_ton ON public.kich_ban_thieu_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((so_luong_dang_giu <= so_luong_ton))';


--
-- Name: CONSTRAINT kiem_tra__kich_ban_thieu_hang__so_luong_dang_giu_khong_am ON kich_ban_thieu_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__kich_ban_thieu_hang__so_luong_dang_giu_khong_am ON public.kich_ban_thieu_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((so_luong_dang_giu >= (0.0)::double precision) AND (so_luong_dang_giu < ''Infinity''::double precision)))';


--
-- Name: CONSTRAINT kiem_tra__kich_ban_thieu_hang__so_luong_du_tru_khong_am ON kich_ban_thieu_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__kich_ban_thieu_hang__so_luong_du_tru_khong_am ON public.kich_ban_thieu_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((so_luong_du_tru >= (0.0)::double precision) AND (so_luong_du_tru < ''Infinity''::double precision)))';


--
-- Name: CONSTRAINT kiem_tra__kich_ban_thieu_hang__so_luong_ton_khong_am ON kich_ban_thieu_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__kich_ban_thieu_hang__so_luong_ton_khong_am ON public.kich_ban_thieu_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((so_luong_ton >= (0.0)::double precision) AND (so_luong_ton < ''Infinity''::double precision)))';


--
-- Name: kich_ban_thieu_hang_id_kich_ban_thieu_hang_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.kich_ban_thieu_hang ALTER COLUMN id_kich_ban_thieu_hang ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.kich_ban_thieu_hang_id_kich_ban_thieu_hang_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lan_thuc_nghiem; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lan_thuc_nghiem (
    id_lan_thuc_nghiem bigint NOT NULL,
    ngay_chot_huan_luyen date NOT NULL,
    ngay_chot_xac_thuc date NOT NULL,
    ngay_chot_kiem_thu date NOT NULL,
    cau_hinh jsonb NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_nguon_du_lieu bigint NOT NULL,
    CONSTRAINT kiem_tra__lan_thuc_nghiem__cac_moc_tang_dan CHECK (((ngay_chot_huan_luyen < ngay_chot_xac_thuc) AND (ngay_chot_xac_thuc < ngay_chot_kiem_thu)))
);


--
-- Name: TABLE lan_thuc_nghiem; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.lan_thuc_nghiem IS 'Mỗi hàng là lần thực nghiệm với dữ liệu và các mốc chia theo thời gian.';


--
-- Name: COLUMN lan_thuc_nghiem.id_lan_thuc_nghiem; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lan_thuc_nghiem.id_lan_thuc_nghiem IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN lan_thuc_nghiem.ngay_chot_huan_luyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lan_thuc_nghiem.ngay_chot_huan_luyen IS 'Ngày cuối nhãn tập huấn luyện được phép sử dụng.';


--
-- Name: COLUMN lan_thuc_nghiem.ngay_chot_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lan_thuc_nghiem.ngay_chot_xac_thuc IS 'Ngày cuối nhãn tập xác thực, trước tập kiểm thử.';


--
-- Name: COLUMN lan_thuc_nghiem.ngay_chot_kiem_thu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lan_thuc_nghiem.ngay_chot_kiem_thu IS 'Ngày cuối nhãn tập kiểm thử.';


--
-- Name: COLUMN lan_thuc_nghiem.cau_hinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lan_thuc_nghiem.cau_hinh IS 'Cấu hình siêu tham số khác nhau theo mô hình và phiên bản thư viện; không chứa dữ liệu tồn kho.';


--
-- Name: COLUMN lan_thuc_nghiem.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lan_thuc_nghiem.thoi_diem_tao IS 'Thời điểm hệ thống ghi nhận nghiệp vụ.';


--
-- Name: COLUMN lan_thuc_nghiem.id_nguon_du_lieu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lan_thuc_nghiem.id_nguon_du_lieu IS 'Nguồn quan sát độc lập.';


--
-- Name: CONSTRAINT kiem_tra__lan_thuc_nghiem__cac_moc_tang_dan ON lan_thuc_nghiem; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__lan_thuc_nghiem__cac_moc_tang_dan ON public.lan_thuc_nghiem IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((ngay_chot_huan_luyen < ngay_chot_xac_thuc) AND (ngay_chot_xac_thuc < ngay_chot_kiem_thu)))';


--
-- Name: lan_thuc_nghiem_id_lan_thuc_nghiem_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.lan_thuc_nghiem ALTER COLUMN id_lan_thuc_nghiem ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.lan_thuc_nghiem_id_lan_thuc_nghiem_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lich_su_dieu_kien_lo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lich_su_dieu_kien_lo (
    id_lich_su_dieu_kien_lo bigint NOT NULL,
    duoc_phep_ban boolean NOT NULL,
    ly_do text DEFAULT ''::text NOT NULL,
    so_van_ban_thu_hoi text DEFAULT ''::text NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_lo_thuoc bigint NOT NULL,
    id_tai_khoan_thuc_hien bigint,
    CONSTRAINT kiem_tra__lich_su_dieu_kien_lo__ly_do_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ly_do)),
    CONSTRAINT kiem_tra__lich_su_dieu_kien_lo__ly_do_khi_khoa CHECK ((duoc_phep_ban OR public.khong_rong(ly_do))),
    CONSTRAINT kiem_tra__lich_su_dieu_kien_lo__so_van_ban_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(so_van_ban_thu_hoi)),
    CONSTRAINT kiem_tra__lich_su_dieu_kien_lo__so_van_ban_mot_dong CHECK (public.la_mot_dong(so_van_ban_thu_hoi))
);


--
-- Name: TABLE lich_su_dieu_kien_lo; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.lich_su_dieu_kien_lo IS 'Mỗi hàng là một lần khóa hoặc mở bán một lô; chỉ thêm, không sửa hoặc xóa.';


--
-- Name: COLUMN lich_su_dieu_kien_lo.id_lich_su_dieu_kien_lo; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lich_su_dieu_kien_lo.id_lich_su_dieu_kien_lo IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN lich_su_dieu_kien_lo.duoc_phep_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lich_su_dieu_kien_lo.duoc_phep_ban IS 'Điều kiện bán của lô sau thao tác: true là mở bán, false là khóa bán.';


--
-- Name: COLUMN lich_su_dieu_kien_lo.ly_do; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lich_su_dieu_kien_lo.ly_do IS 'Lý do khóa hoặc mở bán; bắt buộc khi khóa. Cho phép nhiều dòng.';


--
-- Name: COLUMN lich_su_dieu_kien_lo.so_van_ban_thu_hoi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lich_su_dieu_kien_lo.so_van_ban_thu_hoi IS 'Số công văn hoặc quyết định thu hồi của cơ quan quản lý dược, nếu khóa vì thu hồi; rỗng khi không có. Văn bản một dòng.';


--
-- Name: COLUMN lich_su_dieu_kien_lo.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lich_su_dieu_kien_lo.thoi_diem_tao IS 'Thời điểm đổi điều kiện bán.';


--
-- Name: COLUMN lich_su_dieu_kien_lo.id_lo_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lich_su_dieu_kien_lo.id_lo_thuoc IS 'Lô được khóa hoặc mở bán ở mọi chi nhánh.';


--
-- Name: COLUMN lich_su_dieu_kien_lo.id_tai_khoan_thuc_hien; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lich_su_dieu_kien_lo.id_tai_khoan_thuc_hien IS 'Tài khoản khóa hoặc mở bán; NULL chỉ ở dòng ghi lại lô đã khóa trước khi có nhật ký này.';


--
-- Name: CONSTRAINT kiem_tra__lich_su_dieu_kien_lo__ly_do_da_cat_khoang_trang ON lich_su_dieu_kien_lo; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__lich_su_dieu_kien_lo__ly_do_da_cat_khoang_trang ON public.lich_su_dieu_kien_lo IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ly_do))';


--
-- Name: CONSTRAINT kiem_tra__lich_su_dieu_kien_lo__ly_do_khi_khoa ON lich_su_dieu_kien_lo; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__lich_su_dieu_kien_lo__ly_do_khi_khoa ON public.lich_su_dieu_kien_lo IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((duoc_phep_ban OR khong_rong(ly_do)))';


--
-- Name: CONSTRAINT kiem_tra__lich_su_dieu_kien_lo__so_van_ban_da_cat_khoang_trang ON lich_su_dieu_kien_lo; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__lich_su_dieu_kien_lo__so_van_ban_da_cat_khoang_trang ON public.lich_su_dieu_kien_lo IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(so_van_ban_thu_hoi))';


--
-- Name: CONSTRAINT kiem_tra__lich_su_dieu_kien_lo__so_van_ban_mot_dong ON lich_su_dieu_kien_lo; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__lich_su_dieu_kien_lo__so_van_ban_mot_dong ON public.lich_su_dieu_kien_lo IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(so_van_ban_thu_hoi))';


--
-- Name: lich_su_dieu_kien_lo_id_lich_su_dieu_kien_lo_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.lich_su_dieu_kien_lo ALTER COLUMN id_lich_su_dieu_kien_lo ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.lich_su_dieu_kien_lo_id_lich_su_dieu_kien_lo_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lich_su_don_hang; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lich_su_don_hang (
    id_lich_su_don_hang bigint NOT NULL,
    tu_trang_thai text,
    den_trang_thai text NOT NULL,
    ghi_chu text DEFAULT ''::text NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_don_hang bigint NOT NULL,
    id_tai_khoan_thuc_hien bigint,
    CONSTRAINT kiem_tra__lich_su_don_hang__den_trang_thai_hop_le CHECK ((den_trang_thai = ANY (ARRAY['dang_giu'::text, 'hoan_thanh'::text, 'da_huy'::text, 'het_han'::text]))),
    CONSTRAINT kiem_tra__lich_su_don_hang__ghi_chu_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ghi_chu)),
    CONSTRAINT kiem_tra__lich_su_don_hang__ghi_chu_mot_dong CHECK (public.la_mot_dong(ghi_chu)),
    CONSTRAINT kiem_tra__lich_su_don_hang__tu_trang_thai_hop_le CHECK (((tu_trang_thai IS NULL) OR (tu_trang_thai = ANY (ARRAY['dang_giu'::text, 'hoan_thanh'::text, 'da_huy'::text, 'het_han'::text]))))
);


--
-- Name: TABLE lich_su_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.lich_su_don_hang IS 'Mỗi hàng là một lần đơn đổi trạng thái; không sửa, không xóa.';


--
-- Name: COLUMN lich_su_don_hang.id_lich_su_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lich_su_don_hang.id_lich_su_don_hang IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN lich_su_don_hang.tu_trang_thai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lich_su_don_hang.tu_trang_thai IS 'Trạng thái trước khi đổi; NULL ở dòng tạo đơn.';


--
-- Name: COLUMN lich_su_don_hang.den_trang_thai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lich_su_don_hang.den_trang_thai IS 'Trạng thái sau khi đổi.';


--
-- Name: COLUMN lich_su_don_hang.ghi_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lich_su_don_hang.ghi_chu IS 'Lý do hoặc ghi chú hiển thị cho khách; một dòng, có thể rỗng.';


--
-- Name: COLUMN lich_su_don_hang.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lich_su_don_hang.thoi_diem_tao IS 'Thời điểm đổi trạng thái.';


--
-- Name: COLUMN lich_su_don_hang.id_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lich_su_don_hang.id_don_hang IS 'Đơn được đổi trạng thái.';


--
-- Name: COLUMN lich_su_don_hang.id_tai_khoan_thuc_hien; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lich_su_don_hang.id_tai_khoan_thuc_hien IS 'Khách hoặc nhân viên thao tác; NULL khi hệ thống tự đổi do quá hạn.';


--
-- Name: CONSTRAINT kiem_tra__lich_su_don_hang__den_trang_thai_hop_le ON lich_su_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__lich_su_don_hang__den_trang_thai_hop_le ON public.lich_su_don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((den_trang_thai = ANY (ARRAY[''dang_giu''::text, ''hoan_thanh''::text, ''da_huy''::text, ''het_han''::text])))';


--
-- Name: CONSTRAINT kiem_tra__lich_su_don_hang__ghi_chu_da_cat_khoang_trang ON lich_su_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__lich_su_don_hang__ghi_chu_da_cat_khoang_trang ON public.lich_su_don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ghi_chu))';


--
-- Name: CONSTRAINT kiem_tra__lich_su_don_hang__ghi_chu_mot_dong ON lich_su_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__lich_su_don_hang__ghi_chu_mot_dong ON public.lich_su_don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ghi_chu))';


--
-- Name: CONSTRAINT kiem_tra__lich_su_don_hang__tu_trang_thai_hop_le ON lich_su_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__lich_su_don_hang__tu_trang_thai_hop_le ON public.lich_su_don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((tu_trang_thai IS NULL) OR (tu_trang_thai = ANY (ARRAY[''dang_giu''::text, ''hoan_thanh''::text, ''da_huy''::text, ''het_han''::text]))))';


--
-- Name: lich_su_don_hang_id_lich_su_don_hang_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.lich_su_don_hang ALTER COLUMN id_lich_su_don_hang ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.lich_su_don_hang_id_lich_su_don_hang_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lo_thuoc; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lo_thuoc (
    id_lo_thuoc bigint NOT NULL,
    ma_lo_thuoc text NOT NULL,
    ngay_het_han date NOT NULL,
    duoc_phep_ban boolean DEFAULT true NOT NULL,
    id_thuoc bigint NOT NULL,
    CONSTRAINT kiem_tra__lo_thuoc__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_lo_thuoc)),
    CONSTRAINT kiem_tra__lo_thuoc__ma_dung_dinh_dang CHECK ((ma_lo_thuoc ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'::text)),
    CONSTRAINT kiem_tra__lo_thuoc__ma_khong_rong CHECK (public.khong_rong(ma_lo_thuoc)),
    CONSTRAINT kiem_tra__lo_thuoc__ma_mot_dong CHECK (public.la_mot_dong(ma_lo_thuoc))
);


--
-- Name: TABLE lo_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.lo_thuoc IS 'Mỗi hàng là một lô của một thuốc, dùng chung giữa các chi nhánh.';


--
-- Name: COLUMN lo_thuoc.id_lo_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lo_thuoc.id_lo_thuoc IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN lo_thuoc.ma_lo_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lo_thuoc.ma_lo_thuoc IS 'Mã lô của nhà sản xuất; văn bản một dòng.';


--
-- Name: COLUMN lo_thuoc.ngay_het_han; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lo_thuoc.ngay_het_han IS 'Ngày cuối lô còn được bán theo giờ Việt Nam, do người nhập ghi.';


--
-- Name: COLUMN lo_thuoc.duoc_phep_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lo_thuoc.duoc_phep_ban IS 'Lô được phép xuất bán khi còn hạn.';


--
-- Name: COLUMN lo_thuoc.id_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lo_thuoc.id_thuoc IS 'Sản phẩm của lô.';


--
-- Name: CONSTRAINT kiem_tra__lo_thuoc__ma_da_cat_khoang_trang ON lo_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__lo_thuoc__ma_da_cat_khoang_trang ON public.lo_thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_lo_thuoc))';


--
-- Name: CONSTRAINT kiem_tra__lo_thuoc__ma_dung_dinh_dang ON lo_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__lo_thuoc__ma_dung_dinh_dang ON public.lo_thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_lo_thuoc ~ ''^[A-Z0-9][A-Z0-9_-]{0,31}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__lo_thuoc__ma_khong_rong ON lo_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__lo_thuoc__ma_khong_rong ON public.lo_thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_lo_thuoc))';


--
-- Name: CONSTRAINT kiem_tra__lo_thuoc__ma_mot_dong ON lo_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__lo_thuoc__ma_mot_dong ON public.lo_thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_lo_thuoc))';


--
-- Name: lo_thuoc_id_lo_thuoc_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.lo_thuoc ALTER COLUMN id_lo_thuoc ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.lo_thuoc_id_lo_thuoc_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: nguon_du_lieu; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nguon_du_lieu (
    id_nguon_du_lieu bigint NOT NULL,
    ten_nguon_du_lieu text NOT NULL,
    bam_sha256 text NOT NULL,
    don_vi_nguon text NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    CONSTRAINT kiem_tra__nguon_du_lieu__bam_sha256_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(bam_sha256)),
    CONSTRAINT kiem_tra__nguon_du_lieu__bam_sha256_dung_dinh_dang CHECK ((bam_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT kiem_tra__nguon_du_lieu__bam_sha256_khong_rong CHECK (public.khong_rong(bam_sha256)),
    CONSTRAINT kiem_tra__nguon_du_lieu__bam_sha256_mot_dong CHECK (public.la_mot_dong(bam_sha256)),
    CONSTRAINT kiem_tra__nguon_du_lieu__don_vi_nguon_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(don_vi_nguon)),
    CONSTRAINT kiem_tra__nguon_du_lieu__don_vi_nguon_khong_rong CHECK (public.khong_rong(don_vi_nguon)),
    CONSTRAINT kiem_tra__nguon_du_lieu__don_vi_nguon_mot_dong CHECK (public.la_mot_dong(don_vi_nguon)),
    CONSTRAINT kiem_tra__nguon_du_lieu__ten_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ten_nguon_du_lieu)),
    CONSTRAINT kiem_tra__nguon_du_lieu__ten_khong_rong CHECK (public.khong_rong(ten_nguon_du_lieu)),
    CONSTRAINT kiem_tra__nguon_du_lieu__ten_mot_dong CHECK (public.la_mot_dong(ten_nguon_du_lieu))
);


--
-- Name: TABLE nguon_du_lieu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.nguon_du_lieu IS 'Mỗi hàng là một phiên bản dữ liệu Pharma Sales công khai đã nạp vào DB.';


--
-- Name: COLUMN nguon_du_lieu.id_nguon_du_lieu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nguon_du_lieu.id_nguon_du_lieu IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN nguon_du_lieu.ten_nguon_du_lieu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nguon_du_lieu.ten_nguon_du_lieu IS 'Tên nguồn và phiên bản do người nạp nhập; văn bản một dòng.';


--
-- Name: COLUMN nguon_du_lieu.bam_sha256; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nguon_du_lieu.bam_sha256 IS 'SHA-256 nội dung nguồn, không phải đường dẫn tệp; văn bản một dòng.';


--
-- Name: COLUMN nguon_du_lieu.don_vi_nguon; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nguon_du_lieu.don_vi_nguon IS 'Đơn vị đo theo mô tả nguồn công khai, không đồng nhất kho mô phỏng; văn bản một dòng.';


--
-- Name: COLUMN nguon_du_lieu.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nguon_du_lieu.thoi_diem_tao IS 'Thời điểm hệ thống ghi nhận nghiệp vụ.';


--
-- Name: CONSTRAINT kiem_tra__nguon_du_lieu__bam_sha256_da_cat_khoang_trang ON nguon_du_lieu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nguon_du_lieu__bam_sha256_da_cat_khoang_trang ON public.nguon_du_lieu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(bam_sha256))';


--
-- Name: CONSTRAINT kiem_tra__nguon_du_lieu__bam_sha256_dung_dinh_dang ON nguon_du_lieu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nguon_du_lieu__bam_sha256_dung_dinh_dang ON public.nguon_du_lieu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((bam_sha256 ~ ''^[0-9a-f]{64}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__nguon_du_lieu__bam_sha256_khong_rong ON nguon_du_lieu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nguon_du_lieu__bam_sha256_khong_rong ON public.nguon_du_lieu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(bam_sha256))';


--
-- Name: CONSTRAINT kiem_tra__nguon_du_lieu__bam_sha256_mot_dong ON nguon_du_lieu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nguon_du_lieu__bam_sha256_mot_dong ON public.nguon_du_lieu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(bam_sha256))';


--
-- Name: CONSTRAINT kiem_tra__nguon_du_lieu__don_vi_nguon_da_cat_khoang_trang ON nguon_du_lieu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nguon_du_lieu__don_vi_nguon_da_cat_khoang_trang ON public.nguon_du_lieu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(don_vi_nguon))';


--
-- Name: CONSTRAINT kiem_tra__nguon_du_lieu__don_vi_nguon_khong_rong ON nguon_du_lieu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nguon_du_lieu__don_vi_nguon_khong_rong ON public.nguon_du_lieu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(don_vi_nguon))';


--
-- Name: CONSTRAINT kiem_tra__nguon_du_lieu__don_vi_nguon_mot_dong ON nguon_du_lieu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nguon_du_lieu__don_vi_nguon_mot_dong ON public.nguon_du_lieu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(don_vi_nguon))';


--
-- Name: CONSTRAINT kiem_tra__nguon_du_lieu__ten_da_cat_khoang_trang ON nguon_du_lieu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nguon_du_lieu__ten_da_cat_khoang_trang ON public.nguon_du_lieu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ten_nguon_du_lieu))';


--
-- Name: CONSTRAINT kiem_tra__nguon_du_lieu__ten_khong_rong ON nguon_du_lieu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nguon_du_lieu__ten_khong_rong ON public.nguon_du_lieu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ten_nguon_du_lieu))';


--
-- Name: CONSTRAINT kiem_tra__nguon_du_lieu__ten_mot_dong ON nguon_du_lieu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nguon_du_lieu__ten_mot_dong ON public.nguon_du_lieu IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ten_nguon_du_lieu))';


--
-- Name: nguon_du_lieu_id_nguon_du_lieu_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.nguon_du_lieu ALTER COLUMN id_nguon_du_lieu ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.nguon_du_lieu_id_nguon_du_lieu_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: nha_cung_cap; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nha_cung_cap (
    id_nha_cung_cap bigint NOT NULL,
    ma_nha_cung_cap text NOT NULL,
    ten_nha_cung_cap text NOT NULL,
    dia_chi text DEFAULT ''::text NOT NULL,
    so_dien_thoai text DEFAULT ''::text NOT NULL,
    dang_hoat_dong boolean DEFAULT true NOT NULL,
    CONSTRAINT kiem_tra__nha_cung_cap__dia_chi_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(dia_chi)),
    CONSTRAINT kiem_tra__nha_cung_cap__dia_chi_mot_dong CHECK (public.la_mot_dong(dia_chi)),
    CONSTRAINT kiem_tra__nha_cung_cap__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_nha_cung_cap)),
    CONSTRAINT kiem_tra__nha_cung_cap__ma_dung_dinh_dang CHECK ((ma_nha_cung_cap ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'::text)),
    CONSTRAINT kiem_tra__nha_cung_cap__ma_khong_rong CHECK (public.khong_rong(ma_nha_cung_cap)),
    CONSTRAINT kiem_tra__nha_cung_cap__ma_mot_dong CHECK (public.la_mot_dong(ma_nha_cung_cap)),
    CONSTRAINT kiem_tra__nha_cung_cap__so_dien_thoai_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(so_dien_thoai)),
    CONSTRAINT kiem_tra__nha_cung_cap__so_dien_thoai_dung_dinh_dang CHECK ((so_dien_thoai ~ '^(((0(3[2-9]|5[2-9]|7[06-9]|8[1-9]|9[0-9])[0-9]{7}|02[0-9]{9})|1[89]00([0-9]{4}|[0-9]{6})))?$'::text)),
    CONSTRAINT kiem_tra__nha_cung_cap__so_dien_thoai_mot_dong CHECK (public.la_mot_dong(so_dien_thoai)),
    CONSTRAINT kiem_tra__nha_cung_cap__ten_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ten_nha_cung_cap)),
    CONSTRAINT kiem_tra__nha_cung_cap__ten_khong_rong CHECK (public.khong_rong(ten_nha_cung_cap)),
    CONSTRAINT kiem_tra__nha_cung_cap__ten_mot_dong CHECK (public.la_mot_dong(ten_nha_cung_cap))
);


--
-- Name: TABLE nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.nha_cung_cap IS 'Mỗi hàng là một đối tác cung cấp thuốc.';


--
-- Name: COLUMN nha_cung_cap.id_nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nha_cung_cap.id_nha_cung_cap IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN nha_cung_cap.ma_nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nha_cung_cap.ma_nha_cung_cap IS 'Mã đối tác; văn bản một dòng.';


--
-- Name: COLUMN nha_cung_cap.ten_nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nha_cung_cap.ten_nha_cung_cap IS 'Tên đối tác; văn bản một dòng.';


--
-- Name: COLUMN nha_cung_cap.dia_chi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nha_cung_cap.dia_chi IS 'Địa chỉ liên hệ; văn bản một dòng.';


--
-- Name: COLUMN nha_cung_cap.so_dien_thoai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nha_cung_cap.so_dien_thoai IS 'Số liên hệ của nhà cung cấp, chỉ gồm chữ số: di động, cố định hoặc tổng đài 1800/1900; rỗng khi chưa có.';


--
-- Name: COLUMN nha_cung_cap.dang_hoat_dong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nha_cung_cap.dang_hoat_dong IS 'Đối tác đang được sử dụng khi nhập mới.';


--
-- Name: CONSTRAINT kiem_tra__nha_cung_cap__dia_chi_da_cat_khoang_trang ON nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nha_cung_cap__dia_chi_da_cat_khoang_trang ON public.nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(dia_chi))';


--
-- Name: CONSTRAINT kiem_tra__nha_cung_cap__dia_chi_mot_dong ON nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nha_cung_cap__dia_chi_mot_dong ON public.nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(dia_chi))';


--
-- Name: CONSTRAINT kiem_tra__nha_cung_cap__ma_da_cat_khoang_trang ON nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nha_cung_cap__ma_da_cat_khoang_trang ON public.nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_nha_cung_cap))';


--
-- Name: CONSTRAINT kiem_tra__nha_cung_cap__ma_dung_dinh_dang ON nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nha_cung_cap__ma_dung_dinh_dang ON public.nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_nha_cung_cap ~ ''^[A-Z0-9][A-Z0-9_-]{0,31}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__nha_cung_cap__ma_khong_rong ON nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nha_cung_cap__ma_khong_rong ON public.nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_nha_cung_cap))';


--
-- Name: CONSTRAINT kiem_tra__nha_cung_cap__ma_mot_dong ON nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nha_cung_cap__ma_mot_dong ON public.nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_nha_cung_cap))';


--
-- Name: CONSTRAINT kiem_tra__nha_cung_cap__so_dien_thoai_da_cat_khoang_trang ON nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nha_cung_cap__so_dien_thoai_da_cat_khoang_trang ON public.nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(so_dien_thoai))';


--
-- Name: CONSTRAINT kiem_tra__nha_cung_cap__so_dien_thoai_dung_dinh_dang ON nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nha_cung_cap__so_dien_thoai_dung_dinh_dang ON public.nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((so_dien_thoai ~ ''^(((0(3[2-9]|5[2-9]|7[06-9]|8[1-9]|9[0-9])[0-9]{7}|02[0-9]{9})|1[89]00([0-9]{4}|[0-9]{6})))?$''::text))';


--
-- Name: CONSTRAINT kiem_tra__nha_cung_cap__so_dien_thoai_mot_dong ON nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nha_cung_cap__so_dien_thoai_mot_dong ON public.nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(so_dien_thoai))';


--
-- Name: CONSTRAINT kiem_tra__nha_cung_cap__ten_da_cat_khoang_trang ON nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nha_cung_cap__ten_da_cat_khoang_trang ON public.nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ten_nha_cung_cap))';


--
-- Name: CONSTRAINT kiem_tra__nha_cung_cap__ten_khong_rong ON nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nha_cung_cap__ten_khong_rong ON public.nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ten_nha_cung_cap))';


--
-- Name: CONSTRAINT kiem_tra__nha_cung_cap__ten_mot_dong ON nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nha_cung_cap__ten_mot_dong ON public.nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ten_nha_cung_cap))';


--
-- Name: nha_cung_cap_id_nha_cung_cap_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.nha_cung_cap ALTER COLUMN id_nha_cung_cap ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.nha_cung_cap_id_nha_cung_cap_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: nhan_vien; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nhan_vien (
    id_nhan_vien bigint NOT NULL,
    ma_nhan_vien text NOT NULL,
    ten_nhan_vien text NOT NULL,
    so_dien_thoai text DEFAULT ''::text NOT NULL,
    id_tai_khoan bigint NOT NULL,
    CONSTRAINT kiem_tra__nhan_vien__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_nhan_vien)),
    CONSTRAINT kiem_tra__nhan_vien__ma_dung_dinh_dang CHECK ((ma_nhan_vien ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'::text)),
    CONSTRAINT kiem_tra__nhan_vien__ma_khong_rong CHECK (public.khong_rong(ma_nhan_vien)),
    CONSTRAINT kiem_tra__nhan_vien__ma_mot_dong CHECK (public.la_mot_dong(ma_nhan_vien)),
    CONSTRAINT kiem_tra__nhan_vien__so_dien_thoai_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(so_dien_thoai)),
    CONSTRAINT kiem_tra__nhan_vien__so_dien_thoai_dung_dinh_dang CHECK ((so_dien_thoai ~ '^((0(3[2-9]|5[2-9]|7[06-9]|8[1-9]|9[0-9])[0-9]{7}|02[0-9]{9}))?$'::text)),
    CONSTRAINT kiem_tra__nhan_vien__so_dien_thoai_mot_dong CHECK (public.la_mot_dong(so_dien_thoai)),
    CONSTRAINT kiem_tra__nhan_vien__ten_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ten_nhan_vien)),
    CONSTRAINT kiem_tra__nhan_vien__ten_khong_rong CHECK (public.khong_rong(ten_nhan_vien)),
    CONSTRAINT kiem_tra__nhan_vien__ten_mot_dong CHECK (public.la_mot_dong(ten_nhan_vien))
);


--
-- Name: TABLE nhan_vien; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.nhan_vien IS 'Mỗi hàng là hồ sơ nhân viên, phạm vi làm việc lấy từ tài khoản.';


--
-- Name: COLUMN nhan_vien.id_nhan_vien; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhan_vien.id_nhan_vien IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN nhan_vien.ma_nhan_vien; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhan_vien.ma_nhan_vien IS 'Mã nhân viên; văn bản một dòng.';


--
-- Name: COLUMN nhan_vien.ten_nhan_vien; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhan_vien.ten_nhan_vien IS 'Họ tên nhân viên; văn bản một dòng.';


--
-- Name: COLUMN nhan_vien.so_dien_thoai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhan_vien.so_dien_thoai IS 'Số điện thoại Việt Nam của nhân viên, dạng nội địa chỉ gồm chữ số; rỗng khi chưa có.';


--
-- Name: COLUMN nhan_vien.id_tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhan_vien.id_tai_khoan IS 'Tài khoản làm việc của nhân viên.';


--
-- Name: CONSTRAINT kiem_tra__nhan_vien__ma_da_cat_khoang_trang ON nhan_vien; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhan_vien__ma_da_cat_khoang_trang ON public.nhan_vien IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_nhan_vien))';


--
-- Name: CONSTRAINT kiem_tra__nhan_vien__ma_dung_dinh_dang ON nhan_vien; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhan_vien__ma_dung_dinh_dang ON public.nhan_vien IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_nhan_vien ~ ''^[A-Z0-9][A-Z0-9_-]{0,31}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__nhan_vien__ma_khong_rong ON nhan_vien; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhan_vien__ma_khong_rong ON public.nhan_vien IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_nhan_vien))';


--
-- Name: CONSTRAINT kiem_tra__nhan_vien__ma_mot_dong ON nhan_vien; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhan_vien__ma_mot_dong ON public.nhan_vien IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_nhan_vien))';


--
-- Name: CONSTRAINT kiem_tra__nhan_vien__so_dien_thoai_da_cat_khoang_trang ON nhan_vien; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhan_vien__so_dien_thoai_da_cat_khoang_trang ON public.nhan_vien IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(so_dien_thoai))';


--
-- Name: CONSTRAINT kiem_tra__nhan_vien__so_dien_thoai_dung_dinh_dang ON nhan_vien; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhan_vien__so_dien_thoai_dung_dinh_dang ON public.nhan_vien IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((so_dien_thoai ~ ''^((0(3[2-9]|5[2-9]|7[06-9]|8[1-9]|9[0-9])[0-9]{7}|02[0-9]{9}))?$''::text))';


--
-- Name: CONSTRAINT kiem_tra__nhan_vien__so_dien_thoai_mot_dong ON nhan_vien; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhan_vien__so_dien_thoai_mot_dong ON public.nhan_vien IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(so_dien_thoai))';


--
-- Name: CONSTRAINT kiem_tra__nhan_vien__ten_da_cat_khoang_trang ON nhan_vien; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhan_vien__ten_da_cat_khoang_trang ON public.nhan_vien IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ten_nhan_vien))';


--
-- Name: CONSTRAINT kiem_tra__nhan_vien__ten_khong_rong ON nhan_vien; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhan_vien__ten_khong_rong ON public.nhan_vien IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ten_nhan_vien))';


--
-- Name: CONSTRAINT kiem_tra__nhan_vien__ten_mot_dong ON nhan_vien; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhan_vien__ten_mot_dong ON public.nhan_vien IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ten_nhan_vien))';


--
-- Name: nhan_vien_id_nhan_vien_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.nhan_vien ALTER COLUMN id_nhan_vien ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.nhan_vien_id_nhan_vien_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: nhat_ky_email; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nhat_ky_email (
    id_nhat_ky_email bigint NOT NULL,
    loai_email text NOT NULL,
    email_nhan text NOT NULL,
    tieu_de text NOT NULL,
    noi_dung_van_ban text NOT NULL,
    trang_thai text DEFAULT 'cho_gui'::text NOT NULL,
    chi_tiet_loi text DEFAULT ''::text NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    thoi_diem_gui timestamp with time zone,
    id_tai_khoan bigint,
    co_dinh_kem_hoa_don boolean DEFAULT false NOT NULL,
    id_don_hang bigint,
    noi_dung_html text,
    so_lan_gui smallint DEFAULT 1 NOT NULL,
    thoi_diem_thu_lai timestamp with time zone,
    CONSTRAINT kiem_tra__nhat_ky_email__chi_tiet_loi_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(chi_tiet_loi)),
    CONSTRAINT kiem_tra__nhat_ky_email__chi_tiet_loi_mot_dong CHECK (public.la_mot_dong(chi_tiet_loi)),
    CONSTRAINT kiem_tra__nhat_ky_email__dinh_kem_can_don_hang CHECK (((NOT co_dinh_kem_hoa_don) OR (id_don_hang IS NOT NULL))),
    CONSTRAINT kiem_tra__nhat_ky_email__email_nhan_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(email_nhan)),
    CONSTRAINT kiem_tra__nhat_ky_email__email_nhan_dung_dinh_dang CHECK ((email_nhan ~ '^[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)+$'::text)),
    CONSTRAINT kiem_tra__nhat_ky_email__email_nhan_khong_rong CHECK (public.khong_rong(email_nhan)),
    CONSTRAINT kiem_tra__nhat_ky_email__email_nhan_mot_dong CHECK (public.la_mot_dong(email_nhan)),
    CONSTRAINT kiem_tra__nhat_ky_email__ket_qua_dung_trang_thai CHECK ((((chi_tiet_loi = ''::text) AND (thoi_diem_gui IS NOT NULL) AND (trang_thai = 'da_gui'::text)) OR ((thoi_diem_gui IS NULL) AND (trang_thai = 'loi'::text)) OR ((chi_tiet_loi = ''::text) AND (thoi_diem_gui IS NULL) AND (trang_thai = 'cho_gui'::text)))),
    CONSTRAINT kiem_tra__nhat_ky_email__loai_email_hop_le CHECK ((loai_email = ANY (ARRAY['ma_xac_thuc'::text, 'chao_mung'::text, 'nhac_ten_dang_nhap'::text, 'mat_khau_da_doi'::text, 'email_da_doi'::text, 'ho_so_da_doi'::text, 'don_hang_moi'::text, 'don_hang_cap_nhat'::text, 'xuat_hoa_don'::text, 'email_da_co_tai_khoan'::text, 'trang_thai_tai_khoan'::text]))),
    CONSTRAINT kiem_tra__nhat_ky_email__loi_co_chi_tiet CHECK (((trang_thai = 'da_gui'::text) OR (trang_thai = 'cho_gui'::text) OR (NOT (chi_tiet_loi = ''::text)))),
    CONSTRAINT kiem_tra__nhat_ky_email__noi_dung_html_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(noi_dung_html)),
    CONSTRAINT kiem_tra__nhat_ky_email__noi_dung_html_khong_rong CHECK (public.khong_rong(noi_dung_html)),
    CONSTRAINT kiem_tra__nhat_ky_email__noi_dung_van_ban_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(noi_dung_van_ban)),
    CONSTRAINT kiem_tra__nhat_ky_email__noi_dung_van_ban_khong_rong CHECK (public.khong_rong(noi_dung_van_ban)),
    CONSTRAINT kiem_tra__nhat_ky_email__so_lan_gui_hop_le CHECK (((so_lan_gui >= 1) AND (so_lan_gui <= 5))),
    CONSTRAINT kiem_tra__nhat_ky_email__tieu_de_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(tieu_de)),
    CONSTRAINT kiem_tra__nhat_ky_email__tieu_de_khong_rong CHECK (public.khong_rong(tieu_de)),
    CONSTRAINT kiem_tra__nhat_ky_email__tieu_de_mot_dong CHECK (public.la_mot_dong(tieu_de)),
    CONSTRAINT kiem_tra__nhat_ky_email__trang_thai_hop_le CHECK ((trang_thai = ANY (ARRAY['cho_gui'::text, 'da_gui'::text, 'loi'::text])))
);


--
-- Name: TABLE nhat_ky_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.nhat_ky_email IS 'Mỗi hàng là một email hệ thống đã tạo, kèm kết quả gửi.';


--
-- Name: COLUMN nhat_ky_email.id_nhat_ky_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhat_ky_email.id_nhat_ky_email IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN nhat_ky_email.loai_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhat_ky_email.loai_email IS 'Mục đích của email do hệ thống chọn khi tạo; quyết định mẫu nội dung.';


--
-- Name: COLUMN nhat_ky_email.email_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhat_ky_email.email_nhan IS 'Địa chỉ người nhận đã chuẩn hóa chữ thường tại thời điểm gửi.';


--
-- Name: COLUMN nhat_ky_email.tieu_de; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhat_ky_email.tieu_de IS 'Tiêu đề email đã gửi; văn bản một dòng.';


--
-- Name: COLUMN nhat_ky_email.noi_dung_van_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhat_ky_email.noi_dung_van_ban IS 'Bản văn bản thuần của email để đối chiếu; mã OTP và khóa bí mật được che trước khi lưu.';


--
-- Name: COLUMN nhat_ky_email.trang_thai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhat_ky_email.trang_thai IS 'cho_gui khi transaction chưa xong, da_gui khi máy chủ SMTP nhận, loi khi lỗi.';


--
-- Name: COLUMN nhat_ky_email.chi_tiet_loi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhat_ky_email.chi_tiet_loi IS 'Thông báo lỗi một dòng từ máy chủ SMTP; rỗng khi không lỗi.';


--
-- Name: COLUMN nhat_ky_email.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhat_ky_email.thoi_diem_tao IS 'Thời điểm hệ thống ghi nhận yêu cầu gửi email.';


--
-- Name: COLUMN nhat_ky_email.thoi_diem_gui; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhat_ky_email.thoi_diem_gui IS 'Thời điểm máy chủ SMTP nhận email; NULL khi chưa gửi được.';


--
-- Name: COLUMN nhat_ky_email.id_tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhat_ky_email.id_tai_khoan IS 'Tài khoản liên quan; NULL khi email gửi trước lúc có tài khoản.';


--
-- Name: COLUMN nhat_ky_email.co_dinh_kem_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhat_ky_email.co_dinh_kem_hoa_don IS 'TRUE khi thư kèm hóa đơn bán lẻ PDF của đơn; tệp dựng từ phiếu bán lúc gửi, không lưu tệp.';


--
-- Name: COLUMN nhat_ky_email.id_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhat_ky_email.id_don_hang IS 'Đơn hàng mà thư nói tới; dùng giới hạn nhật ký theo chi nhánh và dựng lại hóa đơn khi gửi lại. NULL với thư tài khoản.';


--
-- Name: COLUMN nhat_ky_email.noi_dung_html; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhat_ky_email.noi_dung_html IS 'Bản HTML đúng như đã gửi (mã OTP đã che) để xem lại và gửi lại; NULL với thư tạo trước khi hệ thống lưu bản HTML.';


--
-- Name: COLUMN nhat_ky_email.so_lan_gui; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhat_ky_email.so_lan_gui IS 'Số lần đã thử gửi thư, gồm lần đầu và các lần gửi lại; từ 1 đến 5.';


--
-- Name: COLUMN nhat_ky_email.thoi_diem_thu_lai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhat_ky_email.thoi_diem_thu_lai IS 'Thời điểm giữ lượt gửi lại gần nhất; NULL nếu thư mới thử gửi lần đầu.';


--
-- Name: CONSTRAINT kiem_tra__nhat_ky_email__chi_tiet_loi_da_cat_khoang_trang ON nhat_ky_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhat_ky_email__chi_tiet_loi_da_cat_khoang_trang ON public.nhat_ky_email IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(chi_tiet_loi))';


--
-- Name: CONSTRAINT kiem_tra__nhat_ky_email__chi_tiet_loi_mot_dong ON nhat_ky_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhat_ky_email__chi_tiet_loi_mot_dong ON public.nhat_ky_email IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(chi_tiet_loi))';


--
-- Name: CONSTRAINT kiem_tra__nhat_ky_email__dinh_kem_can_don_hang ON nhat_ky_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhat_ky_email__dinh_kem_can_don_hang ON public.nhat_ky_email IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((NOT co_dinh_kem_hoa_don) OR (id_don_hang IS NOT NULL)))';


--
-- Name: CONSTRAINT kiem_tra__nhat_ky_email__email_nhan_da_cat_khoang_trang ON nhat_ky_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhat_ky_email__email_nhan_da_cat_khoang_trang ON public.nhat_ky_email IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(email_nhan))';


--
-- Name: CONSTRAINT kiem_tra__nhat_ky_email__email_nhan_dung_dinh_dang ON nhat_ky_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhat_ky_email__email_nhan_dung_dinh_dang ON public.nhat_ky_email IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((email_nhan ~ ''^[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)+$''::text))';


--
-- Name: CONSTRAINT kiem_tra__nhat_ky_email__email_nhan_khong_rong ON nhat_ky_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhat_ky_email__email_nhan_khong_rong ON public.nhat_ky_email IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(email_nhan))';


--
-- Name: CONSTRAINT kiem_tra__nhat_ky_email__email_nhan_mot_dong ON nhat_ky_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhat_ky_email__email_nhan_mot_dong ON public.nhat_ky_email IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(email_nhan))';


--
-- Name: CONSTRAINT kiem_tra__nhat_ky_email__ket_qua_dung_trang_thai ON nhat_ky_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhat_ky_email__ket_qua_dung_trang_thai ON public.nhat_ky_email IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((((chi_tiet_loi = ''''::text) AND (thoi_diem_gui IS NOT NULL) AND (trang_thai = ''da_gui''::text)) OR ((thoi_diem_gui IS NULL) AND (trang_thai = ''loi''::text)) OR ((chi_tiet_loi = ''''::text) AND (thoi_diem_gui IS NULL) AND (trang_thai = ''cho_gui''::text))))';


--
-- Name: CONSTRAINT kiem_tra__nhat_ky_email__loai_email_hop_le ON nhat_ky_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhat_ky_email__loai_email_hop_le ON public.nhat_ky_email IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((loai_email = ANY (ARRAY[''ma_xac_thuc''::text, ''chao_mung''::text, ''nhac_ten_dang_nhap''::text, ''mat_khau_da_doi''::text, ''email_da_doi''::text, ''ho_so_da_doi''::text, ''don_hang_moi''::text, ''don_hang_cap_nhat''::text, ''xuat_hoa_don''::text, ''email_da_co_tai_khoan''::text, ''trang_thai_tai_khoan''::text])))';


--
-- Name: CONSTRAINT kiem_tra__nhat_ky_email__loi_co_chi_tiet ON nhat_ky_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhat_ky_email__loi_co_chi_tiet ON public.nhat_ky_email IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((trang_thai = ''da_gui''::text) OR (trang_thai = ''cho_gui''::text) OR (NOT (chi_tiet_loi = ''''::text))))';


--
-- Name: CONSTRAINT kiem_tra__nhat_ky_email__noi_dung_html_da_cat_khoang_trang ON nhat_ky_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhat_ky_email__noi_dung_html_da_cat_khoang_trang ON public.nhat_ky_email IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(noi_dung_html))';


--
-- Name: CONSTRAINT kiem_tra__nhat_ky_email__noi_dung_html_khong_rong ON nhat_ky_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhat_ky_email__noi_dung_html_khong_rong ON public.nhat_ky_email IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(noi_dung_html))';


--
-- Name: CONSTRAINT kiem_tra__nhat_ky_email__noi_dung_van_ban_da_cat_khoang_trang ON nhat_ky_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhat_ky_email__noi_dung_van_ban_da_cat_khoang_trang ON public.nhat_ky_email IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(noi_dung_van_ban))';


--
-- Name: CONSTRAINT kiem_tra__nhat_ky_email__noi_dung_van_ban_khong_rong ON nhat_ky_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhat_ky_email__noi_dung_van_ban_khong_rong ON public.nhat_ky_email IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(noi_dung_van_ban))';


--
-- Name: CONSTRAINT kiem_tra__nhat_ky_email__so_lan_gui_hop_le ON nhat_ky_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhat_ky_email__so_lan_gui_hop_le ON public.nhat_ky_email IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((so_lan_gui >= 1) AND (so_lan_gui <= 5)))';


--
-- Name: CONSTRAINT kiem_tra__nhat_ky_email__tieu_de_da_cat_khoang_trang ON nhat_ky_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhat_ky_email__tieu_de_da_cat_khoang_trang ON public.nhat_ky_email IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(tieu_de))';


--
-- Name: CONSTRAINT kiem_tra__nhat_ky_email__tieu_de_khong_rong ON nhat_ky_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhat_ky_email__tieu_de_khong_rong ON public.nhat_ky_email IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(tieu_de))';


--
-- Name: CONSTRAINT kiem_tra__nhat_ky_email__tieu_de_mot_dong ON nhat_ky_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhat_ky_email__tieu_de_mot_dong ON public.nhat_ky_email IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(tieu_de))';


--
-- Name: CONSTRAINT kiem_tra__nhat_ky_email__trang_thai_hop_le ON nhat_ky_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhat_ky_email__trang_thai_hop_le ON public.nhat_ky_email IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((trang_thai = ANY (ARRAY[''cho_gui''::text, ''da_gui''::text, ''loi''::text])))';


--
-- Name: nhat_ky_email_id_nhat_ky_email_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.nhat_ky_email ALTER COLUMN id_nhat_ky_email ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.nhat_ky_email_id_nhat_ky_email_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: nhom_atc; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nhom_atc (
    id_nhom_atc bigint NOT NULL,
    ma_nhom_atc text NOT NULL,
    ten_nhom_atc text NOT NULL,
    CONSTRAINT kiem_tra__nhom_atc__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_nhom_atc)),
    CONSTRAINT kiem_tra__nhom_atc__ma_dung_dinh_dang CHECK ((ma_nhom_atc ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'::text)),
    CONSTRAINT kiem_tra__nhom_atc__ma_khong_rong CHECK (public.khong_rong(ma_nhom_atc)),
    CONSTRAINT kiem_tra__nhom_atc__ma_mot_dong CHECK (public.la_mot_dong(ma_nhom_atc)),
    CONSTRAINT kiem_tra__nhom_atc__ten_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ten_nhom_atc)),
    CONSTRAINT kiem_tra__nhom_atc__ten_khong_rong CHECK (public.khong_rong(ten_nhom_atc)),
    CONSTRAINT kiem_tra__nhom_atc__ten_mot_dong CHECK (public.la_mot_dong(ten_nhom_atc))
);


--
-- Name: TABLE nhom_atc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.nhom_atc IS 'Mỗi hàng là một mã phân nhóm ATC, không biểu thị khả năng thay thế thuốc.';


--
-- Name: COLUMN nhom_atc.id_nhom_atc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhom_atc.id_nhom_atc IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN nhom_atc.ma_nhom_atc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhom_atc.ma_nhom_atc IS 'Mã ATC từ danh mục được dùng; văn bản một dòng.';


--
-- Name: COLUMN nhom_atc.ten_nhom_atc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhom_atc.ten_nhom_atc IS 'Diễn giải nhóm ATC; văn bản một dòng.';


--
-- Name: CONSTRAINT kiem_tra__nhom_atc__ma_da_cat_khoang_trang ON nhom_atc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhom_atc__ma_da_cat_khoang_trang ON public.nhom_atc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_nhom_atc))';


--
-- Name: CONSTRAINT kiem_tra__nhom_atc__ma_dung_dinh_dang ON nhom_atc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhom_atc__ma_dung_dinh_dang ON public.nhom_atc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_nhom_atc ~ ''^[A-Z0-9][A-Z0-9_-]{0,31}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__nhom_atc__ma_khong_rong ON nhom_atc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhom_atc__ma_khong_rong ON public.nhom_atc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_nhom_atc))';


--
-- Name: CONSTRAINT kiem_tra__nhom_atc__ma_mot_dong ON nhom_atc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhom_atc__ma_mot_dong ON public.nhom_atc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_nhom_atc))';


--
-- Name: CONSTRAINT kiem_tra__nhom_atc__ten_da_cat_khoang_trang ON nhom_atc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhom_atc__ten_da_cat_khoang_trang ON public.nhom_atc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ten_nhom_atc))';


--
-- Name: CONSTRAINT kiem_tra__nhom_atc__ten_khong_rong ON nhom_atc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhom_atc__ten_khong_rong ON public.nhom_atc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ten_nhom_atc))';


--
-- Name: CONSTRAINT kiem_tra__nhom_atc__ten_mot_dong ON nhom_atc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhom_atc__ten_mot_dong ON public.nhom_atc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ten_nhom_atc))';


--
-- Name: nhom_atc_id_nhom_atc_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.nhom_atc ALTER COLUMN id_nhom_atc ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.nhom_atc_id_nhom_atc_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: nhom_quyen; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nhom_quyen (
    id_nhom_quyen bigint NOT NULL,
    ma_nhom_quyen text NOT NULL,
    ten_nhom_quyen text NOT NULL,
    mo_ta text DEFAULT ''::text NOT NULL,
    vai_tro_mac_dinh text,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    CONSTRAINT kiem_tra__nhom_quyen__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_nhom_quyen)),
    CONSTRAINT kiem_tra__nhom_quyen__ma_dung_dinh_dang CHECK ((ma_nhom_quyen ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'::text)),
    CONSTRAINT kiem_tra__nhom_quyen__ma_khong_rong CHECK (public.khong_rong(ma_nhom_quyen)),
    CONSTRAINT kiem_tra__nhom_quyen__ma_mot_dong CHECK (public.la_mot_dong(ma_nhom_quyen)),
    CONSTRAINT kiem_tra__nhom_quyen__mo_ta_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(mo_ta)),
    CONSTRAINT kiem_tra__nhom_quyen__mo_ta_mot_dong CHECK (public.la_mot_dong(mo_ta)),
    CONSTRAINT kiem_tra__nhom_quyen__ten_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ten_nhom_quyen)),
    CONSTRAINT kiem_tra__nhom_quyen__ten_khong_rong CHECK (public.khong_rong(ten_nhom_quyen)),
    CONSTRAINT kiem_tra__nhom_quyen__ten_mot_dong CHECK (public.la_mot_dong(ten_nhom_quyen)),
    CONSTRAINT kiem_tra__nhom_quyen__vai_tro_mac_dinh_hop_le CHECK (((vai_tro_mac_dinh IS NULL) OR (vai_tro_mac_dinh = ANY (ARRAY['quan_ly_chi_nhanh'::text, 'nhan_vien'::text]))))
);


--
-- Name: TABLE nhom_quyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.nhom_quyen IS 'Mỗi hàng là một nhóm quyền có thể gán cho nhiều tài khoản nội bộ.';


--
-- Name: COLUMN nhom_quyen.id_nhom_quyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhom_quyen.id_nhom_quyen IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN nhom_quyen.ma_nhom_quyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhom_quyen.ma_nhom_quyen IS 'Mã nhóm do quản trị nhập; chữ hoa, số, gạch ngang.';


--
-- Name: COLUMN nhom_quyen.ten_nhom_quyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhom_quyen.ten_nhom_quyen IS 'Tên nhóm hiển thị khi gán quyền, ví dụ Dược sĩ phụ trách kho; một dòng.';


--
-- Name: COLUMN nhom_quyen.mo_ta; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhom_quyen.mo_ta IS 'Ghi chú phạm vi của nhóm; một dòng, có thể rỗng.';


--
-- Name: COLUMN nhom_quyen.vai_tro_mac_dinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhom_quyen.vai_tro_mac_dinh IS 'Vai trò dùng nhóm này khi tài khoản chưa được gán nhóm riêng; NULL với nhóm do quản trị tự tạo. Mỗi vai trò chỉ có một nhóm mặc định.';


--
-- Name: COLUMN nhom_quyen.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nhom_quyen.thoi_diem_tao IS 'Thời điểm tạo nhóm.';


--
-- Name: CONSTRAINT kiem_tra__nhom_quyen__ma_da_cat_khoang_trang ON nhom_quyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhom_quyen__ma_da_cat_khoang_trang ON public.nhom_quyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_nhom_quyen))';


--
-- Name: CONSTRAINT kiem_tra__nhom_quyen__ma_dung_dinh_dang ON nhom_quyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhom_quyen__ma_dung_dinh_dang ON public.nhom_quyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_nhom_quyen ~ ''^[A-Z0-9][A-Z0-9_-]{0,31}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__nhom_quyen__ma_khong_rong ON nhom_quyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhom_quyen__ma_khong_rong ON public.nhom_quyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_nhom_quyen))';


--
-- Name: CONSTRAINT kiem_tra__nhom_quyen__ma_mot_dong ON nhom_quyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhom_quyen__ma_mot_dong ON public.nhom_quyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_nhom_quyen))';


--
-- Name: CONSTRAINT kiem_tra__nhom_quyen__mo_ta_da_cat_khoang_trang ON nhom_quyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhom_quyen__mo_ta_da_cat_khoang_trang ON public.nhom_quyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(mo_ta))';


--
-- Name: CONSTRAINT kiem_tra__nhom_quyen__mo_ta_mot_dong ON nhom_quyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhom_quyen__mo_ta_mot_dong ON public.nhom_quyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(mo_ta))';


--
-- Name: CONSTRAINT kiem_tra__nhom_quyen__ten_da_cat_khoang_trang ON nhom_quyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhom_quyen__ten_da_cat_khoang_trang ON public.nhom_quyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ten_nhom_quyen))';


--
-- Name: CONSTRAINT kiem_tra__nhom_quyen__ten_khong_rong ON nhom_quyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhom_quyen__ten_khong_rong ON public.nhom_quyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ten_nhom_quyen))';


--
-- Name: CONSTRAINT kiem_tra__nhom_quyen__ten_mot_dong ON nhom_quyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhom_quyen__ten_mot_dong ON public.nhom_quyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ten_nhom_quyen))';


--
-- Name: CONSTRAINT kiem_tra__nhom_quyen__vai_tro_mac_dinh_hop_le ON nhom_quyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__nhom_quyen__vai_tro_mac_dinh_hop_le ON public.nhom_quyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((vai_tro_mac_dinh IS NULL) OR (vai_tro_mac_dinh = ANY (ARRAY[''quan_ly_chi_nhanh''::text, ''nhan_vien''::text]))))';


--
-- Name: nhom_quyen_id_nhom_quyen_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.nhom_quyen ALTER COLUMN id_nhom_quyen ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.nhom_quyen_id_nhom_quyen_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: phan_bo_don_hang; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.phan_bo_don_hang (
    id_phan_bo_don_hang bigint NOT NULL,
    so_luong integer NOT NULL,
    id_chi_tiet_don_hang bigint NOT NULL,
    id_ton_kho bigint NOT NULL,
    CONSTRAINT kiem_tra__pb_don_hang__so_luong_duong CHECK ((so_luong > 0))
);


--
-- Name: TABLE phan_bo_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.phan_bo_don_hang IS 'Mỗi hàng là lượng một dòng đơn giữ trên hàng tồn của một lô theo FEFO; chỉ tính khi đơn ở trạng thái giữ và chưa quá hạn.';


--
-- Name: COLUMN phan_bo_don_hang.id_phan_bo_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phan_bo_don_hang.id_phan_bo_don_hang IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN phan_bo_don_hang.so_luong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phan_bo_don_hang.so_luong IS 'Lượng cơ sở đang giữ; giới hạn số nguyên PostgreSQL 32 bit.';


--
-- Name: COLUMN phan_bo_don_hang.id_chi_tiet_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phan_bo_don_hang.id_chi_tiet_don_hang IS 'Dòng đơn được giữ hàng.';


--
-- Name: COLUMN phan_bo_don_hang.id_ton_kho; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phan_bo_don_hang.id_ton_kho IS 'Hàng tồn của lô tại chi nhánh đơn.';


--
-- Name: CONSTRAINT kiem_tra__pb_don_hang__so_luong_duong ON phan_bo_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__pb_don_hang__so_luong_duong ON public.phan_bo_don_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((so_luong > 0))';


--
-- Name: phan_bo_don_hang_id_phan_bo_don_hang_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.phan_bo_don_hang ALTER COLUMN id_phan_bo_don_hang ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.phan_bo_don_hang_id_phan_bo_don_hang_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: phan_bo_phieu_ban; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.phan_bo_phieu_ban (
    id_phan_bo_phieu_ban bigint NOT NULL,
    so_luong integer NOT NULL,
    id_chi_tiet_phieu_ban bigint NOT NULL,
    id_ton_kho bigint NOT NULL,
    CONSTRAINT kiem_tra__pb_ban__so_luong_duong CHECK ((so_luong > 0))
);


--
-- Name: TABLE phan_bo_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.phan_bo_phieu_ban IS 'Mỗi hàng là lượng thực xuất của một dòng bán từ một lô.';


--
-- Name: COLUMN phan_bo_phieu_ban.id_phan_bo_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phan_bo_phieu_ban.id_phan_bo_phieu_ban IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN phan_bo_phieu_ban.so_luong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phan_bo_phieu_ban.so_luong IS 'Lượng cơ sở xuất; giới hạn số nguyên PostgreSQL 32 bit.';


--
-- Name: COLUMN phan_bo_phieu_ban.id_chi_tiet_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phan_bo_phieu_ban.id_chi_tiet_phieu_ban IS 'Dòng thuốc bán.';


--
-- Name: COLUMN phan_bo_phieu_ban.id_ton_kho; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phan_bo_phieu_ban.id_ton_kho IS 'Hàng tồn thực xuất.';


--
-- Name: CONSTRAINT kiem_tra__pb_ban__so_luong_duong ON phan_bo_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__pb_ban__so_luong_duong ON public.phan_bo_phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((so_luong > 0))';


--
-- Name: phan_bo_phieu_ban_id_phan_bo_phieu_ban_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.phan_bo_phieu_ban ALTER COLUMN id_phan_bo_phieu_ban ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.phan_bo_phieu_ban_id_phan_bo_phieu_ban_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: phien_xac_thuc; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.phien_xac_thuc (
    id_phien_xac_thuc bigint NOT NULL,
    ma_phien_xac_thuc text NOT NULL,
    loai_xac_thuc text NOT NULL,
    email text NOT NULL,
    ten_dang_nhap_dang_ky text DEFAULT ''::text NOT NULL,
    ho_ten_dang_ky text DEFAULT ''::text NOT NULL,
    so_dien_thoai_dang_ky text DEFAULT ''::text NOT NULL,
    mat_khau_bam_dang_ky text DEFAULT ''::text NOT NULL,
    bam_otp text NOT NULL,
    so_lan_nhap_sai smallint DEFAULT 0 NOT NULL,
    so_lan_gui smallint DEFAULT 1 NOT NULL,
    thoi_diem_gui_cuoi timestamp with time zone NOT NULL,
    thoi_diem_het_han timestamp with time zone NOT NULL,
    thoi_diem_su_dung timestamp with time zone,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_tai_khoan bigint,
    dia_chi_ip inet,
    CONSTRAINT kiem_tra__xac_thuc__bam_otp_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(bam_otp)),
    CONSTRAINT kiem_tra__xac_thuc__bam_otp_dung_dinh_dang CHECK ((bam_otp ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT kiem_tra__xac_thuc__bam_otp_khong_rong CHECK (public.khong_rong(bam_otp)),
    CONSTRAINT kiem_tra__xac_thuc__bam_otp_mot_dong CHECK (public.la_mot_dong(bam_otp)),
    CONSTRAINT kiem_tra__xac_thuc__doi_email_can_tai_khoan CHECK (((NOT (loai_xac_thuc = 'doi_email'::text)) OR (id_tai_khoan IS NOT NULL))),
    CONSTRAINT kiem_tra__xac_thuc__du_lieu_dang_ky_dung_loai CHECK ((((ho_ten_dang_ky > ''::text) AND (loai_xac_thuc = 'dang_ky'::text) AND (mat_khau_bam_dang_ky > ''::text) AND (id_tai_khoan IS NULL) AND (ten_dang_nhap_dang_ky > ''::text)) OR ((NOT (loai_xac_thuc = 'dang_ky'::text)) AND (ho_ten_dang_ky = ''::text) AND (mat_khau_bam_dang_ky = ''::text) AND (so_dien_thoai_dang_ky = ''::text) AND (ten_dang_nhap_dang_ky = ''::text)))),
    CONSTRAINT kiem_tra__xac_thuc__email_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(email)),
    CONSTRAINT kiem_tra__xac_thuc__email_dung_dinh_dang CHECK ((email ~ '^[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)+$'::text)),
    CONSTRAINT kiem_tra__xac_thuc__email_khong_rong CHECK (public.khong_rong(email)),
    CONSTRAINT kiem_tra__xac_thuc__email_mot_dong CHECK (public.la_mot_dong(email)),
    CONSTRAINT kiem_tra__xac_thuc__het_han_sau_lan_gui CHECK ((thoi_diem_het_han > thoi_diem_gui_cuoi)),
    CONSTRAINT kiem_tra__xac_thuc__ho_ten_dang_ky_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ho_ten_dang_ky)),
    CONSTRAINT kiem_tra__xac_thuc__ho_ten_dang_ky_mot_dong CHECK (public.la_mot_dong(ho_ten_dang_ky)),
    CONSTRAINT kiem_tra__xac_thuc__hoan_tac_email_can_tai_khoan CHECK (((NOT (loai_xac_thuc = 'hoan_tac_email'::text)) OR (id_tai_khoan IS NOT NULL))),
    CONSTRAINT kiem_tra__xac_thuc__loai_xac_thuc_hop_le CHECK ((loai_xac_thuc = ANY (ARRAY['dang_ky'::text, 'quen_mat_khau'::text, 'doi_email'::text, 'hoan_tac_email'::text]))),
    CONSTRAINT kiem_tra__xac_thuc__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_phien_xac_thuc)),
    CONSTRAINT kiem_tra__xac_thuc__ma_dung_dinh_dang CHECK ((ma_phien_xac_thuc ~ '^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'::text)),
    CONSTRAINT kiem_tra__xac_thuc__ma_khong_rong CHECK (public.khong_rong(ma_phien_xac_thuc)),
    CONSTRAINT kiem_tra__xac_thuc__ma_mot_dong CHECK (public.la_mot_dong(ma_phien_xac_thuc)),
    CONSTRAINT kiem_tra__xac_thuc__mat_khau_bam_dang_ky_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(mat_khau_bam_dang_ky)),
    CONSTRAINT kiem_tra__xac_thuc__mat_khau_bam_dang_ky_mot_dong CHECK (public.la_mot_dong(mat_khau_bam_dang_ky)),
    CONSTRAINT kiem_tra__xac_thuc__so_dien_thoai_dang_ky_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(so_dien_thoai_dang_ky)),
    CONSTRAINT kiem_tra__xac_thuc__so_dien_thoai_dang_ky_dung_dinh_dang CHECK ((so_dien_thoai_dang_ky ~ '^((0(3[2-9]|5[2-9]|7[06-9]|8[1-9]|9[0-9])[0-9]{7}|02[0-9]{9}))?$'::text)),
    CONSTRAINT kiem_tra__xac_thuc__so_dien_thoai_dang_ky_mot_dong CHECK (public.la_mot_dong(so_dien_thoai_dang_ky)),
    CONSTRAINT kiem_tra__xac_thuc__so_lan_gui_hop_le CHECK (((so_lan_gui >= 1) AND (so_lan_gui <= 5))),
    CONSTRAINT kiem_tra__xac_thuc__so_lan_nhap_sai_toi_da CHECK (((so_lan_nhap_sai >= 0) AND (so_lan_nhap_sai <= 5))),
    CONSTRAINT kiem_tra__xac_thuc__ten_dang_nhap_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ten_dang_nhap_dang_ky)),
    CONSTRAINT kiem_tra__xac_thuc__ten_dang_nhap_mot_dong CHECK (public.la_mot_dong(ten_dang_nhap_dang_ky))
);


--
-- Name: TABLE phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.phien_xac_thuc IS 'Mỗi hàng là một phiên gửi mã OTP qua email cho một mục đích.';


--
-- Name: COLUMN phien_xac_thuc.id_phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phien_xac_thuc.id_phien_xac_thuc IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN phien_xac_thuc.ma_phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phien_xac_thuc.ma_phien_xac_thuc IS 'UUID ngẫu nhiên đặt trên đường dẫn trang nhập mã; không đoán được.';


--
-- Name: COLUMN phien_xac_thuc.loai_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phien_xac_thuc.loai_xac_thuc IS 'Mục đích của phiên: dang_ky, quen_mat_khau, doi_email (mã OTP) hoặc hoan_tac_email (liên kết gửi email cũ để khôi phục khi email bị đổi).';


--
-- Name: COLUMN phien_xac_thuc.email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phien_xac_thuc.email IS 'Email nhận mã, đã chuẩn hóa chữ thường.';


--
-- Name: COLUMN phien_xac_thuc.ten_dang_nhap_dang_ky; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phien_xac_thuc.ten_dang_nhap_dang_ky IS 'Tên đăng nhập chờ tạo khi đăng ký; rỗng với loại khác.';


--
-- Name: COLUMN phien_xac_thuc.ho_ten_dang_ky; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phien_xac_thuc.ho_ten_dang_ky IS 'Họ tên khai khi đăng ký; rỗng với loại khác.';


--
-- Name: COLUMN phien_xac_thuc.so_dien_thoai_dang_ky; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phien_xac_thuc.so_dien_thoai_dang_ky IS 'Số điện thoại khai khi đăng ký, có thể rỗng; rỗng với loại khác.';


--
-- Name: COLUMN phien_xac_thuc.mat_khau_bam_dang_ky; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phien_xac_thuc.mat_khau_bam_dang_ky IS 'Mật khẩu đã băm bằng Django khi đăng ký; rỗng với loại khác.';


--
-- Name: COLUMN phien_xac_thuc.bam_otp; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phien_xac_thuc.bam_otp IS 'HMAC-SHA256 hệ thập lục phân của mã OTP sáu chữ số, hoặc của khóa ngẫu nhiên trong liên kết khôi phục email; khóa HMAC là SECRET_KEY.';


--
-- Name: COLUMN phien_xac_thuc.so_lan_nhap_sai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phien_xac_thuc.so_lan_nhap_sai IS 'Số lần nhập sai; đạt 5 thì phiên bị khóa.';


--
-- Name: COLUMN phien_xac_thuc.so_lan_gui; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phien_xac_thuc.so_lan_gui IS 'Số lần đã gửi mã trong phiên, tối đa 5.';


--
-- Name: COLUMN phien_xac_thuc.thoi_diem_gui_cuoi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phien_xac_thuc.thoi_diem_gui_cuoi IS 'Lần gửi mã gần nhất; chặn gửi lại trong 60 giây.';


--
-- Name: COLUMN phien_xac_thuc.thoi_diem_het_han; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phien_xac_thuc.thoi_diem_het_han IS 'Sau thời điểm này mã hết hiệu lực: lần gửi cuối cộng 10 phút; liên kết khôi phục email cộng 7 ngày.';


--
-- Name: COLUMN phien_xac_thuc.thoi_diem_su_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phien_xac_thuc.thoi_diem_su_dung IS 'Thời điểm mã được dùng thành công; NULL khi chưa dùng.';


--
-- Name: COLUMN phien_xac_thuc.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phien_xac_thuc.thoi_diem_tao IS 'Thời điểm phiên được tạo; dùng giới hạn số phiên mỗi giờ.';


--
-- Name: COLUMN phien_xac_thuc.id_tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phien_xac_thuc.id_tai_khoan IS 'Tài khoản được xác thực; NULL khi đăng ký, hoặc khi quên mật khẩu với email không thuộc tài khoản nào (phiên giả để không lộ email đã đăng ký).';


--
-- Name: COLUMN phien_xac_thuc.dia_chi_ip; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phien_xac_thuc.dia_chi_ip IS 'Địa chỉ IP của trình duyệt yêu cầu mã; dùng giới hạn số phiên mỗi giờ theo IP. NULL với phiên tạo trước khi ghi IP hoặc do hệ thống tạo.';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__bam_otp_da_cat_khoang_trang ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__bam_otp_da_cat_khoang_trang ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(bam_otp))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__bam_otp_dung_dinh_dang ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__bam_otp_dung_dinh_dang ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((bam_otp ~ ''^[0-9a-f]{64}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__bam_otp_khong_rong ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__bam_otp_khong_rong ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(bam_otp))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__bam_otp_mot_dong ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__bam_otp_mot_dong ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(bam_otp))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__doi_email_can_tai_khoan ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__doi_email_can_tai_khoan ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((NOT (loai_xac_thuc = ''doi_email''::text)) OR (id_tai_khoan IS NOT NULL)))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__du_lieu_dang_ky_dung_loai ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__du_lieu_dang_ky_dung_loai ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((((ho_ten_dang_ky > ''''::text) AND (loai_xac_thuc = ''dang_ky''::text) AND (mat_khau_bam_dang_ky > ''''::text) AND (id_tai_khoan IS NULL) AND (ten_dang_nhap_dang_ky > ''''::text)) OR ((NOT (loai_xac_thuc = ''dang_ky''::text)) AND (ho_ten_dang_ky = ''''::text) AND (mat_khau_bam_dang_ky = ''''::text) AND (so_dien_thoai_dang_ky = ''''::text) AND (ten_dang_nhap_dang_ky = ''''::text))))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__email_da_cat_khoang_trang ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__email_da_cat_khoang_trang ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(email))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__email_dung_dinh_dang ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__email_dung_dinh_dang ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((email ~ ''^[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)+$''::text))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__email_khong_rong ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__email_khong_rong ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(email))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__email_mot_dong ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__email_mot_dong ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(email))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__het_han_sau_lan_gui ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__het_han_sau_lan_gui ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((thoi_diem_het_han > thoi_diem_gui_cuoi))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__ho_ten_dang_ky_da_cat_khoang_trang ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__ho_ten_dang_ky_da_cat_khoang_trang ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ho_ten_dang_ky))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__ho_ten_dang_ky_mot_dong ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__ho_ten_dang_ky_mot_dong ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ho_ten_dang_ky))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__hoan_tac_email_can_tai_khoan ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__hoan_tac_email_can_tai_khoan ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((NOT (loai_xac_thuc = ''hoan_tac_email''::text)) OR (id_tai_khoan IS NOT NULL)))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__loai_xac_thuc_hop_le ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__loai_xac_thuc_hop_le ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((loai_xac_thuc = ANY (ARRAY[''dang_ky''::text, ''quen_mat_khau''::text, ''doi_email''::text, ''hoan_tac_email''::text])))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__ma_da_cat_khoang_trang ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__ma_da_cat_khoang_trang ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_phien_xac_thuc))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__ma_dung_dinh_dang ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__ma_dung_dinh_dang ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_phien_xac_thuc ~ ''^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__ma_khong_rong ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__ma_khong_rong ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_phien_xac_thuc))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__ma_mot_dong ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__ma_mot_dong ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_phien_xac_thuc))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__mat_khau_bam_dang_ky_da_cat_khoang_trang ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__mat_khau_bam_dang_ky_da_cat_khoang_trang ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(mat_khau_bam_dang_ky))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__mat_khau_bam_dang_ky_mot_dong ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__mat_khau_bam_dang_ky_mot_dong ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(mat_khau_bam_dang_ky))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__so_dien_thoai_dang_ky_da_cat_khoang_trang ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__so_dien_thoai_dang_ky_da_cat_khoang_trang ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(so_dien_thoai_dang_ky))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__so_dien_thoai_dang_ky_dung_dinh_dang ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__so_dien_thoai_dang_ky_dung_dinh_dang ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((so_dien_thoai_dang_ky ~ ''^((0(3[2-9]|5[2-9]|7[06-9]|8[1-9]|9[0-9])[0-9]{7}|02[0-9]{9}))?$''::text))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__so_dien_thoai_dang_ky_mot_dong ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__so_dien_thoai_dang_ky_mot_dong ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(so_dien_thoai_dang_ky))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__so_lan_gui_hop_le ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__so_lan_gui_hop_le ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((so_lan_gui >= 1) AND (so_lan_gui <= 5)))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__so_lan_nhap_sai_toi_da ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__so_lan_nhap_sai_toi_da ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((so_lan_nhap_sai >= 0) AND (so_lan_nhap_sai <= 5)))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__ten_dang_nhap_da_cat_khoang_trang ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__ten_dang_nhap_da_cat_khoang_trang ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ten_dang_nhap_dang_ky))';


--
-- Name: CONSTRAINT kiem_tra__xac_thuc__ten_dang_nhap_mot_dong ON phien_xac_thuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xac_thuc__ten_dang_nhap_mot_dong ON public.phien_xac_thuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ten_dang_nhap_dang_ky))';


--
-- Name: phien_xac_thuc_id_phien_xac_thuc_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.phien_xac_thuc ALTER COLUMN id_phien_xac_thuc ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.phien_xac_thuc_id_phien_xac_thuc_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: phieu_ban; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.phieu_ban (
    id_phieu_ban bigint NOT NULL,
    ma_phieu_ban text NOT NULL,
    khoa_yeu_cau text NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_chi_nhanh bigint NOT NULL,
    id_tai_khoan_lap bigint NOT NULL,
    id_don_hang bigint,
    da_kiem_tra_don_thuoc boolean DEFAULT false NOT NULL,
    ma_don_thuoc text,
    noi_kham_benh text DEFAULT ''::text NOT NULL,
    ten_nguoi_ke_don text DEFAULT ''::text NOT NULL,
    ho_ten_nguoi_benh text DEFAULT ''::text NOT NULL,
    ngay_ke_don date,
    phuong_thuc_thanh_toan text DEFAULT 'tien_mat'::text NOT NULL,
    CONSTRAINT kiem_tra__phieu_ban__don_thuoc_du_thong_tin CHECK (((da_kiem_tra_don_thuoc AND (NOT (ten_nguoi_ke_don = ''::text)) AND (NOT (noi_kham_benh = ''::text))) OR ((NOT da_kiem_tra_don_thuoc) AND (ho_ten_nguoi_benh = ''::text) AND (ma_don_thuoc IS NULL) AND (ngay_ke_don IS NULL) AND (noi_kham_benh = ''::text) AND (ten_nguoi_ke_don = ''::text)))),
    CONSTRAINT kiem_tra__phieu_ban__ho_ten_nguoi_benh_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ho_ten_nguoi_benh)),
    CONSTRAINT kiem_tra__phieu_ban__ho_ten_nguoi_benh_mot_dong CHECK (public.la_mot_dong(ho_ten_nguoi_benh)),
    CONSTRAINT kiem_tra__phieu_ban__khoa_yeu_cau_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(khoa_yeu_cau)),
    CONSTRAINT kiem_tra__phieu_ban__khoa_yeu_cau_khong_rong CHECK (public.khong_rong(khoa_yeu_cau)),
    CONSTRAINT kiem_tra__phieu_ban__khoa_yeu_cau_mot_dong CHECK (public.la_mot_dong(khoa_yeu_cau)),
    CONSTRAINT kiem_tra__phieu_ban__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_phieu_ban)),
    CONSTRAINT kiem_tra__phieu_ban__ma_don_thuoc_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_don_thuoc)),
    CONSTRAINT kiem_tra__phieu_ban__ma_don_thuoc_dung_dinh_dang CHECK ((ma_don_thuoc ~ '^[A-Za-z0-9][A-Za-z0-9-]{5,29}$'::text)),
    CONSTRAINT kiem_tra__phieu_ban__ma_don_thuoc_khong_rong CHECK (public.khong_rong(ma_don_thuoc)),
    CONSTRAINT kiem_tra__phieu_ban__ma_don_thuoc_mot_dong CHECK (public.la_mot_dong(ma_don_thuoc)),
    CONSTRAINT kiem_tra__phieu_ban__ma_dung_dinh_dang CHECK ((ma_phieu_ban ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'::text)),
    CONSTRAINT kiem_tra__phieu_ban__ma_khong_rong CHECK (public.khong_rong(ma_phieu_ban)),
    CONSTRAINT kiem_tra__phieu_ban__ma_mot_dong CHECK (public.la_mot_dong(ma_phieu_ban)),
    CONSTRAINT kiem_tra__phieu_ban__ngay_ke_don_co_nguoi_benh CHECK ((((ho_ten_nguoi_benh = ''::text) AND (ngay_ke_don IS NULL)) OR ((ngay_ke_don IS NOT NULL) AND (NOT (ho_ten_nguoi_benh = ''::text))))),
    CONSTRAINT kiem_tra__phieu_ban__ngay_ke_don_khong_sau_ngay_ban CHECK (((ngay_ke_don IS NULL) OR (ngay_ke_don <= ((thoi_diem_tao AT TIME ZONE 'Asia/Ho_Chi_Minh'::text))::date))),
    CONSTRAINT kiem_tra__phieu_ban__nguoi_ke_don_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ten_nguoi_ke_don)),
    CONSTRAINT kiem_tra__phieu_ban__nguoi_ke_don_mot_dong CHECK (public.la_mot_dong(ten_nguoi_ke_don)),
    CONSTRAINT kiem_tra__phieu_ban__noi_kham_benh_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(noi_kham_benh)),
    CONSTRAINT kiem_tra__phieu_ban__noi_kham_benh_mot_dong CHECK (public.la_mot_dong(noi_kham_benh)),
    CONSTRAINT kiem_tra__phieu_ban__phuong_thuc_thanh_toan_hop_le CHECK ((phuong_thuc_thanh_toan = ANY (ARRAY['tien_mat'::text, 'chuyen_khoan'::text])))
);


--
-- Name: TABLE phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.phieu_ban IS 'Mỗi hàng là một lần bán tại quầy kèm xuất kho: bán trực tiếp hoặc giao đơn đặt giữ cho khách đến nhận.';


--
-- Name: COLUMN phieu_ban.id_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_ban.id_phieu_ban IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN phieu_ban.ma_phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_ban.ma_phieu_ban IS 'Mã phiếu hệ thống cấp; văn bản một dòng.';


--
-- Name: COLUMN phieu_ban.khoa_yeu_cau; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_ban.khoa_yeu_cau IS 'UUID chống xác nhận hai lần từ cùng form; văn bản một dòng.';


--
-- Name: COLUMN phieu_ban.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_ban.thoi_diem_tao IS 'Thời điểm hệ thống ghi nhận nghiệp vụ.';


--
-- Name: COLUMN phieu_ban.id_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_ban.id_chi_nhanh IS 'Chi nhánh bán.';


--
-- Name: COLUMN phieu_ban.id_tai_khoan_lap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_ban.id_tai_khoan_lap IS 'Nhân viên xác nhận bán.';


--
-- Name: COLUMN phieu_ban.id_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_ban.id_don_hang IS 'Đơn đặt giữ khách đến nhận; NULL nghĩa là bán trực tiếp tại quầy.';


--
-- Name: COLUMN phieu_ban.da_kiem_tra_don_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_ban.da_kiem_tra_don_thuoc IS 'Dược sĩ xác nhận đã kiểm tra đơn thuốc của bác sĩ; bắt buộc khi phiếu có thuốc kê đơn, service kiểm trước khi lập phiếu.';


--
-- Name: COLUMN phieu_ban.ma_don_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_ban.ma_don_thuoc IS 'Mã đơn thuốc điện tử in trên đơn (liên thông đơn thuốc quốc gia); NULL khi đơn giấy không có mã hoặc phiếu không có thuốc kê đơn.';


--
-- Name: COLUMN phieu_ban.noi_kham_benh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_ban.noi_kham_benh IS 'Cơ sở khám bệnh, chữa bệnh phát hành đơn; rỗng khi không có thuốc kê đơn.';


--
-- Name: COLUMN phieu_ban.ten_nguoi_ke_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_ban.ten_nguoi_ke_don IS 'Họ tên bác sĩ kê đơn; rỗng khi phiếu không có thuốc kê đơn.';


--
-- Name: COLUMN phieu_ban.ho_ten_nguoi_benh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_ban.ho_ten_nguoi_benh IS 'Họ tên người bệnh ghi trên đơn thuốc, đi cùng ngày kê đơn; rỗng khi không có thuốc kê đơn hoặc phiếu lập trước khi bổ sung cột.';


--
-- Name: COLUMN phieu_ban.ngay_ke_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_ban.ngay_ke_don IS 'Ngày bác sĩ kê đơn, không sau ngày bán; NULL khi phiếu không có thuốc kê đơn và ở phiếu lập trước khi bổ sung cột. Service bắt buộc ghi với phiếu mới có thuốc kê đơn.';


--
-- Name: COLUMN phieu_ban.phuong_thuc_thanh_toan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_ban.phuong_thuc_thanh_toan IS 'Cách khách trả tiền tại quầy: tien_mat hoặc chuyen_khoan; nhân viên lập phiếu xác nhận đã nhận đủ tiền.';


--
-- Name: CONSTRAINT kiem_tra__phieu_ban__don_thuoc_du_thong_tin ON phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_ban__don_thuoc_du_thong_tin ON public.phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((da_kiem_tra_don_thuoc AND (NOT (ten_nguoi_ke_don = ''''::text)) AND (NOT (noi_kham_benh = ''''::text))) OR ((NOT da_kiem_tra_don_thuoc) AND (ho_ten_nguoi_benh = ''''::text) AND (ma_don_thuoc IS NULL) AND (ngay_ke_don IS NULL) AND (noi_kham_benh = ''''::text) AND (ten_nguoi_ke_don = ''''::text))))';


--
-- Name: CONSTRAINT kiem_tra__phieu_ban__ho_ten_nguoi_benh_da_cat_khoang_trang ON phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_ban__ho_ten_nguoi_benh_da_cat_khoang_trang ON public.phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ho_ten_nguoi_benh))';


--
-- Name: CONSTRAINT kiem_tra__phieu_ban__ho_ten_nguoi_benh_mot_dong ON phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_ban__ho_ten_nguoi_benh_mot_dong ON public.phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ho_ten_nguoi_benh))';


--
-- Name: CONSTRAINT kiem_tra__phieu_ban__khoa_yeu_cau_da_cat_khoang_trang ON phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_ban__khoa_yeu_cau_da_cat_khoang_trang ON public.phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(khoa_yeu_cau))';


--
-- Name: CONSTRAINT kiem_tra__phieu_ban__khoa_yeu_cau_khong_rong ON phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_ban__khoa_yeu_cau_khong_rong ON public.phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(khoa_yeu_cau))';


--
-- Name: CONSTRAINT kiem_tra__phieu_ban__khoa_yeu_cau_mot_dong ON phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_ban__khoa_yeu_cau_mot_dong ON public.phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(khoa_yeu_cau))';


--
-- Name: CONSTRAINT kiem_tra__phieu_ban__ma_da_cat_khoang_trang ON phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_ban__ma_da_cat_khoang_trang ON public.phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_phieu_ban))';


--
-- Name: CONSTRAINT kiem_tra__phieu_ban__ma_don_thuoc_da_cat_khoang_trang ON phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_ban__ma_don_thuoc_da_cat_khoang_trang ON public.phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_don_thuoc))';


--
-- Name: CONSTRAINT kiem_tra__phieu_ban__ma_don_thuoc_dung_dinh_dang ON phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_ban__ma_don_thuoc_dung_dinh_dang ON public.phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_don_thuoc ~ ''^[A-Za-z0-9][A-Za-z0-9-]{5,29}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__phieu_ban__ma_don_thuoc_khong_rong ON phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_ban__ma_don_thuoc_khong_rong ON public.phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_don_thuoc))';


--
-- Name: CONSTRAINT kiem_tra__phieu_ban__ma_don_thuoc_mot_dong ON phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_ban__ma_don_thuoc_mot_dong ON public.phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_don_thuoc))';


--
-- Name: CONSTRAINT kiem_tra__phieu_ban__ma_dung_dinh_dang ON phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_ban__ma_dung_dinh_dang ON public.phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_phieu_ban ~ ''^[A-Z0-9][A-Z0-9_-]{0,31}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__phieu_ban__ma_khong_rong ON phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_ban__ma_khong_rong ON public.phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_phieu_ban))';


--
-- Name: CONSTRAINT kiem_tra__phieu_ban__ma_mot_dong ON phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_ban__ma_mot_dong ON public.phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_phieu_ban))';


--
-- Name: CONSTRAINT kiem_tra__phieu_ban__ngay_ke_don_co_nguoi_benh ON phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_ban__ngay_ke_don_co_nguoi_benh ON public.phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((((ho_ten_nguoi_benh = ''''::text) AND (ngay_ke_don IS NULL)) OR ((ngay_ke_don IS NOT NULL) AND (NOT (ho_ten_nguoi_benh = ''''::text)))))';


--
-- Name: CONSTRAINT kiem_tra__phieu_ban__ngay_ke_don_khong_sau_ngay_ban ON phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_ban__ngay_ke_don_khong_sau_ngay_ban ON public.phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((ngay_ke_don IS NULL) OR (ngay_ke_don <= ((thoi_diem_tao AT TIME ZONE ''Asia/Ho_Chi_Minh''::text))::date)))';


--
-- Name: CONSTRAINT kiem_tra__phieu_ban__nguoi_ke_don_da_cat_khoang_trang ON phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_ban__nguoi_ke_don_da_cat_khoang_trang ON public.phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ten_nguoi_ke_don))';


--
-- Name: CONSTRAINT kiem_tra__phieu_ban__nguoi_ke_don_mot_dong ON phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_ban__nguoi_ke_don_mot_dong ON public.phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ten_nguoi_ke_don))';


--
-- Name: CONSTRAINT kiem_tra__phieu_ban__noi_kham_benh_da_cat_khoang_trang ON phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_ban__noi_kham_benh_da_cat_khoang_trang ON public.phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(noi_kham_benh))';


--
-- Name: CONSTRAINT kiem_tra__phieu_ban__noi_kham_benh_mot_dong ON phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_ban__noi_kham_benh_mot_dong ON public.phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(noi_kham_benh))';


--
-- Name: CONSTRAINT kiem_tra__phieu_ban__phuong_thuc_thanh_toan_hop_le ON phieu_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_ban__phuong_thuc_thanh_toan_hop_le ON public.phieu_ban IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((phuong_thuc_thanh_toan = ANY (ARRAY[''tien_mat''::text, ''chuyen_khoan''::text])))';


--
-- Name: phieu_ban_id_phieu_ban_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.phieu_ban ALTER COLUMN id_phieu_ban ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.phieu_ban_id_phieu_ban_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: phieu_dieu_chuyen; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.phieu_dieu_chuyen (
    id_phieu_dieu_chuyen bigint NOT NULL,
    ma_phieu_dieu_chuyen text NOT NULL,
    ghi_chu text DEFAULT ''::text NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_chi_nhanh_dich bigint NOT NULL,
    id_chi_nhanh_nguon bigint NOT NULL,
    id_tai_khoan_lap bigint NOT NULL,
    khoa_yeu_cau text NOT NULL,
    CONSTRAINT kiem_tra__phieu_dieu_chuyen__ghi_chu_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ghi_chu)),
    CONSTRAINT kiem_tra__phieu_dieu_chuyen__khoa_yeu_cau_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(khoa_yeu_cau)),
    CONSTRAINT kiem_tra__phieu_dieu_chuyen__khoa_yeu_cau_dung_dinh_dang CHECK ((khoa_yeu_cau ~ '^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'::text)),
    CONSTRAINT kiem_tra__phieu_dieu_chuyen__khoa_yeu_cau_khong_rong CHECK (public.khong_rong(khoa_yeu_cau)),
    CONSTRAINT kiem_tra__phieu_dieu_chuyen__khoa_yeu_cau_mot_dong CHECK (public.la_mot_dong(khoa_yeu_cau)),
    CONSTRAINT kiem_tra__phieu_dieu_chuyen__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_phieu_dieu_chuyen)),
    CONSTRAINT kiem_tra__phieu_dieu_chuyen__ma_dung_dinh_dang CHECK ((ma_phieu_dieu_chuyen ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'::text)),
    CONSTRAINT kiem_tra__phieu_dieu_chuyen__ma_khong_rong CHECK (public.khong_rong(ma_phieu_dieu_chuyen)),
    CONSTRAINT kiem_tra__phieu_dieu_chuyen__ma_mot_dong CHECK (public.la_mot_dong(ma_phieu_dieu_chuyen)),
    CONSTRAINT kiem_tra__phieu_dieu_chuyen__nguon_khac_dich CHECK ((NOT (id_chi_nhanh_dich = id_chi_nhanh_nguon)))
);


--
-- Name: TABLE phieu_dieu_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.phieu_dieu_chuyen IS 'Mỗi hàng là một chứng từ đã xác nhận, không sửa hoặc xóa.';


--
-- Name: COLUMN phieu_dieu_chuyen.id_phieu_dieu_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_dieu_chuyen.id_phieu_dieu_chuyen IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN phieu_dieu_chuyen.ma_phieu_dieu_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_dieu_chuyen.ma_phieu_dieu_chuyen IS 'Mã chứng từ hệ thống cấp; văn bản một dòng.';


--
-- Name: COLUMN phieu_dieu_chuyen.ghi_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_dieu_chuyen.ghi_chu IS 'Ghi chú khi xác nhận; cho phép nhiều dòng.';


--
-- Name: COLUMN phieu_dieu_chuyen.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_dieu_chuyen.thoi_diem_tao IS 'Thời điểm hệ thống ghi nhận nghiệp vụ.';


--
-- Name: COLUMN phieu_dieu_chuyen.id_chi_nhanh_dich; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_dieu_chuyen.id_chi_nhanh_dich IS 'Cơ sở nhận hàng đồng thời trong giao dịch.';


--
-- Name: COLUMN phieu_dieu_chuyen.id_chi_nhanh_nguon; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_dieu_chuyen.id_chi_nhanh_nguon IS 'Cơ sở xuất hàng.';


--
-- Name: COLUMN phieu_dieu_chuyen.id_tai_khoan_lap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_dieu_chuyen.id_tai_khoan_lap IS 'Tài khoản xác nhận chứng từ.';


--
-- Name: COLUMN phieu_dieu_chuyen.khoa_yeu_cau; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_dieu_chuyen.khoa_yeu_cau IS 'UUID do form cấp mỗi lần mở; bấm lưu hai lần hoặc gửi lại form chỉ tạo một chứng từ. Văn bản một dòng.';


--
-- Name: CONSTRAINT kiem_tra__phieu_dieu_chuyen__ghi_chu_da_cat_khoang_trang ON phieu_dieu_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_dieu_chuyen__ghi_chu_da_cat_khoang_trang ON public.phieu_dieu_chuyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ghi_chu))';


--
-- Name: CONSTRAINT kiem_tra__phieu_dieu_chuyen__khoa_yeu_cau_da_cat_khoang_trang ON phieu_dieu_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_dieu_chuyen__khoa_yeu_cau_da_cat_khoang_trang ON public.phieu_dieu_chuyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(khoa_yeu_cau))';


--
-- Name: CONSTRAINT kiem_tra__phieu_dieu_chuyen__khoa_yeu_cau_dung_dinh_dang ON phieu_dieu_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_dieu_chuyen__khoa_yeu_cau_dung_dinh_dang ON public.phieu_dieu_chuyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((khoa_yeu_cau ~ ''^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__phieu_dieu_chuyen__khoa_yeu_cau_khong_rong ON phieu_dieu_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_dieu_chuyen__khoa_yeu_cau_khong_rong ON public.phieu_dieu_chuyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(khoa_yeu_cau))';


--
-- Name: CONSTRAINT kiem_tra__phieu_dieu_chuyen__khoa_yeu_cau_mot_dong ON phieu_dieu_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_dieu_chuyen__khoa_yeu_cau_mot_dong ON public.phieu_dieu_chuyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(khoa_yeu_cau))';


--
-- Name: CONSTRAINT kiem_tra__phieu_dieu_chuyen__ma_da_cat_khoang_trang ON phieu_dieu_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_dieu_chuyen__ma_da_cat_khoang_trang ON public.phieu_dieu_chuyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_phieu_dieu_chuyen))';


--
-- Name: CONSTRAINT kiem_tra__phieu_dieu_chuyen__ma_dung_dinh_dang ON phieu_dieu_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_dieu_chuyen__ma_dung_dinh_dang ON public.phieu_dieu_chuyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_phieu_dieu_chuyen ~ ''^[A-Z0-9][A-Z0-9_-]{0,31}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__phieu_dieu_chuyen__ma_khong_rong ON phieu_dieu_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_dieu_chuyen__ma_khong_rong ON public.phieu_dieu_chuyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_phieu_dieu_chuyen))';


--
-- Name: CONSTRAINT kiem_tra__phieu_dieu_chuyen__ma_mot_dong ON phieu_dieu_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_dieu_chuyen__ma_mot_dong ON public.phieu_dieu_chuyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_phieu_dieu_chuyen))';


--
-- Name: CONSTRAINT kiem_tra__phieu_dieu_chuyen__nguon_khac_dich ON phieu_dieu_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_dieu_chuyen__nguon_khac_dich ON public.phieu_dieu_chuyen IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((NOT (id_chi_nhanh_dich = id_chi_nhanh_nguon)))';


--
-- Name: phieu_dieu_chuyen_id_phieu_dieu_chuyen_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.phieu_dieu_chuyen ALTER COLUMN id_phieu_dieu_chuyen ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.phieu_dieu_chuyen_id_phieu_dieu_chuyen_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: phieu_kiem_ke; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.phieu_kiem_ke (
    id_phieu_kiem_ke bigint NOT NULL,
    ma_phieu_kiem_ke text NOT NULL,
    ghi_chu text DEFAULT ''::text NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_chi_nhanh bigint NOT NULL,
    id_tai_khoan_lap bigint NOT NULL,
    khoa_yeu_cau text NOT NULL,
    CONSTRAINT kiem_tra__phieu_kiem_ke__ghi_chu_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ghi_chu)),
    CONSTRAINT kiem_tra__phieu_kiem_ke__khoa_yeu_cau_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(khoa_yeu_cau)),
    CONSTRAINT kiem_tra__phieu_kiem_ke__khoa_yeu_cau_dung_dinh_dang CHECK ((khoa_yeu_cau ~ '^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'::text)),
    CONSTRAINT kiem_tra__phieu_kiem_ke__khoa_yeu_cau_khong_rong CHECK (public.khong_rong(khoa_yeu_cau)),
    CONSTRAINT kiem_tra__phieu_kiem_ke__khoa_yeu_cau_mot_dong CHECK (public.la_mot_dong(khoa_yeu_cau)),
    CONSTRAINT kiem_tra__phieu_kiem_ke__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_phieu_kiem_ke)),
    CONSTRAINT kiem_tra__phieu_kiem_ke__ma_dung_dinh_dang CHECK ((ma_phieu_kiem_ke ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'::text)),
    CONSTRAINT kiem_tra__phieu_kiem_ke__ma_khong_rong CHECK (public.khong_rong(ma_phieu_kiem_ke)),
    CONSTRAINT kiem_tra__phieu_kiem_ke__ma_mot_dong CHECK (public.la_mot_dong(ma_phieu_kiem_ke))
);


--
-- Name: TABLE phieu_kiem_ke; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.phieu_kiem_ke IS 'Mỗi hàng là một chứng từ đã xác nhận, không sửa hoặc xóa.';


--
-- Name: COLUMN phieu_kiem_ke.id_phieu_kiem_ke; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_kiem_ke.id_phieu_kiem_ke IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN phieu_kiem_ke.ma_phieu_kiem_ke; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_kiem_ke.ma_phieu_kiem_ke IS 'Mã chứng từ hệ thống cấp; văn bản một dòng.';


--
-- Name: COLUMN phieu_kiem_ke.ghi_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_kiem_ke.ghi_chu IS 'Ghi chú khi xác nhận; cho phép nhiều dòng.';


--
-- Name: COLUMN phieu_kiem_ke.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_kiem_ke.thoi_diem_tao IS 'Thời điểm hệ thống ghi nhận nghiệp vụ.';


--
-- Name: COLUMN phieu_kiem_ke.id_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_kiem_ke.id_chi_nhanh IS 'Chi nhánh kiểm kê và điều chỉnh ngay khi xác nhận.';


--
-- Name: COLUMN phieu_kiem_ke.id_tai_khoan_lap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_kiem_ke.id_tai_khoan_lap IS 'Tài khoản xác nhận chứng từ.';


--
-- Name: COLUMN phieu_kiem_ke.khoa_yeu_cau; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_kiem_ke.khoa_yeu_cau IS 'UUID do form cấp mỗi lần mở; bấm lưu hai lần hoặc gửi lại form chỉ tạo một chứng từ. Văn bản một dòng.';


--
-- Name: CONSTRAINT kiem_tra__phieu_kiem_ke__ghi_chu_da_cat_khoang_trang ON phieu_kiem_ke; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_kiem_ke__ghi_chu_da_cat_khoang_trang ON public.phieu_kiem_ke IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ghi_chu))';


--
-- Name: CONSTRAINT kiem_tra__phieu_kiem_ke__khoa_yeu_cau_da_cat_khoang_trang ON phieu_kiem_ke; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_kiem_ke__khoa_yeu_cau_da_cat_khoang_trang ON public.phieu_kiem_ke IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(khoa_yeu_cau))';


--
-- Name: CONSTRAINT kiem_tra__phieu_kiem_ke__khoa_yeu_cau_dung_dinh_dang ON phieu_kiem_ke; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_kiem_ke__khoa_yeu_cau_dung_dinh_dang ON public.phieu_kiem_ke IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((khoa_yeu_cau ~ ''^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__phieu_kiem_ke__khoa_yeu_cau_khong_rong ON phieu_kiem_ke; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_kiem_ke__khoa_yeu_cau_khong_rong ON public.phieu_kiem_ke IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(khoa_yeu_cau))';


--
-- Name: CONSTRAINT kiem_tra__phieu_kiem_ke__khoa_yeu_cau_mot_dong ON phieu_kiem_ke; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_kiem_ke__khoa_yeu_cau_mot_dong ON public.phieu_kiem_ke IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(khoa_yeu_cau))';


--
-- Name: CONSTRAINT kiem_tra__phieu_kiem_ke__ma_da_cat_khoang_trang ON phieu_kiem_ke; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_kiem_ke__ma_da_cat_khoang_trang ON public.phieu_kiem_ke IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_phieu_kiem_ke))';


--
-- Name: CONSTRAINT kiem_tra__phieu_kiem_ke__ma_dung_dinh_dang ON phieu_kiem_ke; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_kiem_ke__ma_dung_dinh_dang ON public.phieu_kiem_ke IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_phieu_kiem_ke ~ ''^[A-Z0-9][A-Z0-9_-]{0,31}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__phieu_kiem_ke__ma_khong_rong ON phieu_kiem_ke; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_kiem_ke__ma_khong_rong ON public.phieu_kiem_ke IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_phieu_kiem_ke))';


--
-- Name: CONSTRAINT kiem_tra__phieu_kiem_ke__ma_mot_dong ON phieu_kiem_ke; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_kiem_ke__ma_mot_dong ON public.phieu_kiem_ke IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_phieu_kiem_ke))';


--
-- Name: phieu_kiem_ke_id_phieu_kiem_ke_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.phieu_kiem_ke ALTER COLUMN id_phieu_kiem_ke ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.phieu_kiem_ke_id_phieu_kiem_ke_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: phieu_nhap; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.phieu_nhap (
    id_phieu_nhap bigint NOT NULL,
    ma_phieu_nhap text NOT NULL,
    ghi_chu text DEFAULT ''::text NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_chi_nhanh bigint NOT NULL,
    id_tai_khoan_lap bigint NOT NULL,
    id_nha_cung_cap bigint NOT NULL,
    khoa_yeu_cau text NOT NULL,
    so_hoa_don_nha_cung_cap text DEFAULT ''::text NOT NULL,
    CONSTRAINT kiem_tra__phieu_nhap__ghi_chu_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ghi_chu)),
    CONSTRAINT kiem_tra__phieu_nhap__khoa_yeu_cau_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(khoa_yeu_cau)),
    CONSTRAINT kiem_tra__phieu_nhap__khoa_yeu_cau_dung_dinh_dang CHECK ((khoa_yeu_cau ~ '^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'::text)),
    CONSTRAINT kiem_tra__phieu_nhap__khoa_yeu_cau_khong_rong CHECK (public.khong_rong(khoa_yeu_cau)),
    CONSTRAINT kiem_tra__phieu_nhap__khoa_yeu_cau_mot_dong CHECK (public.la_mot_dong(khoa_yeu_cau)),
    CONSTRAINT kiem_tra__phieu_nhap__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_phieu_nhap)),
    CONSTRAINT kiem_tra__phieu_nhap__ma_dung_dinh_dang CHECK ((ma_phieu_nhap ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'::text)),
    CONSTRAINT kiem_tra__phieu_nhap__ma_khong_rong CHECK (public.khong_rong(ma_phieu_nhap)),
    CONSTRAINT kiem_tra__phieu_nhap__ma_mot_dong CHECK (public.la_mot_dong(ma_phieu_nhap)),
    CONSTRAINT kiem_tra__phieu_nhap__so_hoa_don_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(so_hoa_don_nha_cung_cap)),
    CONSTRAINT kiem_tra__phieu_nhap__so_hoa_don_mot_dong CHECK (public.la_mot_dong(so_hoa_don_nha_cung_cap))
);


--
-- Name: TABLE phieu_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.phieu_nhap IS 'Mỗi hàng là một chứng từ đã xác nhận, không sửa hoặc xóa.';


--
-- Name: COLUMN phieu_nhap.id_phieu_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_nhap.id_phieu_nhap IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN phieu_nhap.ma_phieu_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_nhap.ma_phieu_nhap IS 'Mã chứng từ hệ thống cấp; văn bản một dòng.';


--
-- Name: COLUMN phieu_nhap.ghi_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_nhap.ghi_chu IS 'Ghi chú khi xác nhận; cho phép nhiều dòng.';


--
-- Name: COLUMN phieu_nhap.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_nhap.thoi_diem_tao IS 'Thời điểm hệ thống ghi nhận nghiệp vụ.';


--
-- Name: COLUMN phieu_nhap.id_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_nhap.id_chi_nhanh IS 'Chi nhánh nhận hàng.';


--
-- Name: COLUMN phieu_nhap.id_tai_khoan_lap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_nhap.id_tai_khoan_lap IS 'Tài khoản xác nhận chứng từ.';


--
-- Name: COLUMN phieu_nhap.id_nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_nhap.id_nha_cung_cap IS 'Đối tác giao hàng.';


--
-- Name: COLUMN phieu_nhap.khoa_yeu_cau; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_nhap.khoa_yeu_cau IS 'UUID do form cấp mỗi lần mở; bấm lưu hai lần hoặc gửi lại form chỉ tạo một chứng từ. Văn bản một dòng.';


--
-- Name: COLUMN phieu_nhap.so_hoa_don_nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_nhap.so_hoa_don_nha_cung_cap IS 'Ký hiệu và số hóa đơn nhà cung cấp giao kèm hàng, để đối chiếu chứng từ mua; rỗng khi chưa có hóa đơn. Văn bản một dòng.';


--
-- Name: CONSTRAINT kiem_tra__phieu_nhap__ghi_chu_da_cat_khoang_trang ON phieu_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_nhap__ghi_chu_da_cat_khoang_trang ON public.phieu_nhap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ghi_chu))';


--
-- Name: CONSTRAINT kiem_tra__phieu_nhap__khoa_yeu_cau_da_cat_khoang_trang ON phieu_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_nhap__khoa_yeu_cau_da_cat_khoang_trang ON public.phieu_nhap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(khoa_yeu_cau))';


--
-- Name: CONSTRAINT kiem_tra__phieu_nhap__khoa_yeu_cau_dung_dinh_dang ON phieu_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_nhap__khoa_yeu_cau_dung_dinh_dang ON public.phieu_nhap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((khoa_yeu_cau ~ ''^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__phieu_nhap__khoa_yeu_cau_khong_rong ON phieu_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_nhap__khoa_yeu_cau_khong_rong ON public.phieu_nhap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(khoa_yeu_cau))';


--
-- Name: CONSTRAINT kiem_tra__phieu_nhap__khoa_yeu_cau_mot_dong ON phieu_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_nhap__khoa_yeu_cau_mot_dong ON public.phieu_nhap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(khoa_yeu_cau))';


--
-- Name: CONSTRAINT kiem_tra__phieu_nhap__ma_da_cat_khoang_trang ON phieu_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_nhap__ma_da_cat_khoang_trang ON public.phieu_nhap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_phieu_nhap))';


--
-- Name: CONSTRAINT kiem_tra__phieu_nhap__ma_dung_dinh_dang ON phieu_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_nhap__ma_dung_dinh_dang ON public.phieu_nhap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_phieu_nhap ~ ''^[A-Z0-9][A-Z0-9_-]{0,31}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__phieu_nhap__ma_khong_rong ON phieu_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_nhap__ma_khong_rong ON public.phieu_nhap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_phieu_nhap))';


--
-- Name: CONSTRAINT kiem_tra__phieu_nhap__ma_mot_dong ON phieu_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_nhap__ma_mot_dong ON public.phieu_nhap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_phieu_nhap))';


--
-- Name: CONSTRAINT kiem_tra__phieu_nhap__so_hoa_don_da_cat_khoang_trang ON phieu_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_nhap__so_hoa_don_da_cat_khoang_trang ON public.phieu_nhap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(so_hoa_don_nha_cung_cap))';


--
-- Name: CONSTRAINT kiem_tra__phieu_nhap__so_hoa_don_mot_dong ON phieu_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_nhap__so_hoa_don_mot_dong ON public.phieu_nhap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(so_hoa_don_nha_cung_cap))';


--
-- Name: phieu_nhap_id_phieu_nhap_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.phieu_nhap ALTER COLUMN id_phieu_nhap ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.phieu_nhap_id_phieu_nhap_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: phieu_tra_nha_cung_cap; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.phieu_tra_nha_cung_cap (
    id_phieu_tra_nha_cung_cap bigint NOT NULL,
    ma_phieu_tra_nha_cung_cap text NOT NULL,
    ghi_chu text DEFAULT ''::text NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_tai_khoan_lap bigint NOT NULL,
    id_phieu_nhap bigint NOT NULL,
    khoa_yeu_cau text NOT NULL,
    CONSTRAINT kiem_tra__tra_ncc__ghi_chu_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ghi_chu)),
    CONSTRAINT kiem_tra__tra_ncc__khoa_yeu_cau_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(khoa_yeu_cau)),
    CONSTRAINT kiem_tra__tra_ncc__khoa_yeu_cau_dung_dinh_dang CHECK ((khoa_yeu_cau ~ '^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'::text)),
    CONSTRAINT kiem_tra__tra_ncc__khoa_yeu_cau_khong_rong CHECK (public.khong_rong(khoa_yeu_cau)),
    CONSTRAINT kiem_tra__tra_ncc__khoa_yeu_cau_mot_dong CHECK (public.la_mot_dong(khoa_yeu_cau)),
    CONSTRAINT kiem_tra__tra_ncc__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_phieu_tra_nha_cung_cap)),
    CONSTRAINT kiem_tra__tra_ncc__ma_dung_dinh_dang CHECK ((ma_phieu_tra_nha_cung_cap ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'::text)),
    CONSTRAINT kiem_tra__tra_ncc__ma_khong_rong CHECK (public.khong_rong(ma_phieu_tra_nha_cung_cap)),
    CONSTRAINT kiem_tra__tra_ncc__ma_mot_dong CHECK (public.la_mot_dong(ma_phieu_tra_nha_cung_cap))
);


--
-- Name: TABLE phieu_tra_nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.phieu_tra_nha_cung_cap IS 'Mỗi hàng là một chứng từ đã xác nhận, không sửa hoặc xóa.';


--
-- Name: COLUMN phieu_tra_nha_cung_cap.id_phieu_tra_nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_tra_nha_cung_cap.id_phieu_tra_nha_cung_cap IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN phieu_tra_nha_cung_cap.ma_phieu_tra_nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_tra_nha_cung_cap.ma_phieu_tra_nha_cung_cap IS 'Mã chứng từ hệ thống cấp; văn bản một dòng.';


--
-- Name: COLUMN phieu_tra_nha_cung_cap.ghi_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_tra_nha_cung_cap.ghi_chu IS 'Ghi chú khi xác nhận; cho phép nhiều dòng.';


--
-- Name: COLUMN phieu_tra_nha_cung_cap.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_tra_nha_cung_cap.thoi_diem_tao IS 'Thời điểm hệ thống ghi nhận nghiệp vụ.';


--
-- Name: COLUMN phieu_tra_nha_cung_cap.id_tai_khoan_lap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_tra_nha_cung_cap.id_tai_khoan_lap IS 'Tài khoản xác nhận chứng từ.';


--
-- Name: COLUMN phieu_tra_nha_cung_cap.id_phieu_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_tra_nha_cung_cap.id_phieu_nhap IS 'Phiếu nhập gốc, xác định nhà cung cấp và chi nhánh.';


--
-- Name: COLUMN phieu_tra_nha_cung_cap.khoa_yeu_cau; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_tra_nha_cung_cap.khoa_yeu_cau IS 'UUID do form cấp mỗi lần mở; bấm lưu hai lần hoặc gửi lại form chỉ tạo một chứng từ. Văn bản một dòng.';


--
-- Name: CONSTRAINT kiem_tra__tra_ncc__ghi_chu_da_cat_khoang_trang ON phieu_tra_nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tra_ncc__ghi_chu_da_cat_khoang_trang ON public.phieu_tra_nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ghi_chu))';


--
-- Name: CONSTRAINT kiem_tra__tra_ncc__khoa_yeu_cau_da_cat_khoang_trang ON phieu_tra_nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tra_ncc__khoa_yeu_cau_da_cat_khoang_trang ON public.phieu_tra_nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(khoa_yeu_cau))';


--
-- Name: CONSTRAINT kiem_tra__tra_ncc__khoa_yeu_cau_dung_dinh_dang ON phieu_tra_nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tra_ncc__khoa_yeu_cau_dung_dinh_dang ON public.phieu_tra_nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((khoa_yeu_cau ~ ''^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__tra_ncc__khoa_yeu_cau_khong_rong ON phieu_tra_nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tra_ncc__khoa_yeu_cau_khong_rong ON public.phieu_tra_nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(khoa_yeu_cau))';


--
-- Name: CONSTRAINT kiem_tra__tra_ncc__khoa_yeu_cau_mot_dong ON phieu_tra_nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tra_ncc__khoa_yeu_cau_mot_dong ON public.phieu_tra_nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(khoa_yeu_cau))';


--
-- Name: CONSTRAINT kiem_tra__tra_ncc__ma_da_cat_khoang_trang ON phieu_tra_nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tra_ncc__ma_da_cat_khoang_trang ON public.phieu_tra_nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_phieu_tra_nha_cung_cap))';


--
-- Name: CONSTRAINT kiem_tra__tra_ncc__ma_dung_dinh_dang ON phieu_tra_nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tra_ncc__ma_dung_dinh_dang ON public.phieu_tra_nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_phieu_tra_nha_cung_cap ~ ''^[A-Z0-9][A-Z0-9_-]{0,31}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__tra_ncc__ma_khong_rong ON phieu_tra_nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tra_ncc__ma_khong_rong ON public.phieu_tra_nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_phieu_tra_nha_cung_cap))';


--
-- Name: CONSTRAINT kiem_tra__tra_ncc__ma_mot_dong ON phieu_tra_nha_cung_cap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tra_ncc__ma_mot_dong ON public.phieu_tra_nha_cung_cap IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_phieu_tra_nha_cung_cap))';


--
-- Name: phieu_tra_nha_cung_cap_id_phieu_tra_nha_cung_cap_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.phieu_tra_nha_cung_cap ALTER COLUMN id_phieu_tra_nha_cung_cap ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.phieu_tra_nha_cung_cap_id_phieu_tra_nha_cung_cap_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: phieu_xuat_huy; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.phieu_xuat_huy (
    id_phieu_xuat_huy bigint NOT NULL,
    ma_phieu_xuat_huy text NOT NULL,
    loai_xuat_huy text NOT NULL,
    ghi_chu text DEFAULT ''::text NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_chi_nhanh bigint NOT NULL,
    id_tai_khoan_lap bigint NOT NULL,
    khoa_yeu_cau text NOT NULL,
    CONSTRAINT kiem_tra__phieu_xuat_huy__ghi_chu_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ghi_chu)),
    CONSTRAINT kiem_tra__phieu_xuat_huy__khoa_yeu_cau_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(khoa_yeu_cau)),
    CONSTRAINT kiem_tra__phieu_xuat_huy__khoa_yeu_cau_dung_dinh_dang CHECK ((khoa_yeu_cau ~ '^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'::text)),
    CONSTRAINT kiem_tra__phieu_xuat_huy__khoa_yeu_cau_khong_rong CHECK (public.khong_rong(khoa_yeu_cau)),
    CONSTRAINT kiem_tra__phieu_xuat_huy__khoa_yeu_cau_mot_dong CHECK (public.la_mot_dong(khoa_yeu_cau)),
    CONSTRAINT kiem_tra__phieu_xuat_huy__loai_xuat_huy_hop_le CHECK ((loai_xuat_huy = ANY (ARRAY['het_han'::text, 'hu_hong'::text, 'thu_hoi'::text]))),
    CONSTRAINT kiem_tra__phieu_xuat_huy__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_phieu_xuat_huy)),
    CONSTRAINT kiem_tra__phieu_xuat_huy__ma_dung_dinh_dang CHECK ((ma_phieu_xuat_huy ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'::text)),
    CONSTRAINT kiem_tra__phieu_xuat_huy__ma_khong_rong CHECK (public.khong_rong(ma_phieu_xuat_huy)),
    CONSTRAINT kiem_tra__phieu_xuat_huy__ma_mot_dong CHECK (public.la_mot_dong(ma_phieu_xuat_huy))
);


--
-- Name: TABLE phieu_xuat_huy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.phieu_xuat_huy IS 'Mỗi hàng là một chứng từ xuất hủy đã xác nhận, không sửa hoặc xóa.';


--
-- Name: COLUMN phieu_xuat_huy.id_phieu_xuat_huy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_xuat_huy.id_phieu_xuat_huy IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN phieu_xuat_huy.ma_phieu_xuat_huy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_xuat_huy.ma_phieu_xuat_huy IS 'Mã chứng từ hệ thống cấp; văn bản một dòng.';


--
-- Name: COLUMN phieu_xuat_huy.loai_xuat_huy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_xuat_huy.loai_xuat_huy IS 'het_han: mọi lô đã quá ngày hết hạn; hu_hong: hàng hỏng, vỡ, biến chất; thu_hoi: lô đang khóa bán theo thông báo thu hồi, ghi chú ghi số văn bản.';


--
-- Name: COLUMN phieu_xuat_huy.ghi_chu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_xuat_huy.ghi_chu IS 'Mô tả tình trạng hàng và biên bản kèm theo; cho phép nhiều dòng.';


--
-- Name: COLUMN phieu_xuat_huy.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_xuat_huy.thoi_diem_tao IS 'Thời điểm hệ thống ghi nhận nghiệp vụ.';


--
-- Name: COLUMN phieu_xuat_huy.id_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_xuat_huy.id_chi_nhanh IS 'Chi nhánh có hàng bị hủy.';


--
-- Name: COLUMN phieu_xuat_huy.id_tai_khoan_lap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_xuat_huy.id_tai_khoan_lap IS 'Quản lý chi nhánh xác nhận chứng từ.';


--
-- Name: COLUMN phieu_xuat_huy.khoa_yeu_cau; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.phieu_xuat_huy.khoa_yeu_cau IS 'UUID do form cấp mỗi lần mở; bấm lưu hai lần hoặc gửi lại form chỉ tạo một chứng từ. Văn bản một dòng.';


--
-- Name: CONSTRAINT kiem_tra__phieu_xuat_huy__ghi_chu_da_cat_khoang_trang ON phieu_xuat_huy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_xuat_huy__ghi_chu_da_cat_khoang_trang ON public.phieu_xuat_huy IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ghi_chu))';


--
-- Name: CONSTRAINT kiem_tra__phieu_xuat_huy__khoa_yeu_cau_da_cat_khoang_trang ON phieu_xuat_huy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_xuat_huy__khoa_yeu_cau_da_cat_khoang_trang ON public.phieu_xuat_huy IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(khoa_yeu_cau))';


--
-- Name: CONSTRAINT kiem_tra__phieu_xuat_huy__khoa_yeu_cau_dung_dinh_dang ON phieu_xuat_huy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_xuat_huy__khoa_yeu_cau_dung_dinh_dang ON public.phieu_xuat_huy IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((khoa_yeu_cau ~ ''^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__phieu_xuat_huy__khoa_yeu_cau_khong_rong ON phieu_xuat_huy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_xuat_huy__khoa_yeu_cau_khong_rong ON public.phieu_xuat_huy IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(khoa_yeu_cau))';


--
-- Name: CONSTRAINT kiem_tra__phieu_xuat_huy__khoa_yeu_cau_mot_dong ON phieu_xuat_huy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_xuat_huy__khoa_yeu_cau_mot_dong ON public.phieu_xuat_huy IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(khoa_yeu_cau))';


--
-- Name: CONSTRAINT kiem_tra__phieu_xuat_huy__loai_xuat_huy_hop_le ON phieu_xuat_huy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_xuat_huy__loai_xuat_huy_hop_le ON public.phieu_xuat_huy IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((loai_xuat_huy = ANY (ARRAY[''het_han''::text, ''hu_hong''::text, ''thu_hoi''::text])))';


--
-- Name: CONSTRAINT kiem_tra__phieu_xuat_huy__ma_da_cat_khoang_trang ON phieu_xuat_huy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_xuat_huy__ma_da_cat_khoang_trang ON public.phieu_xuat_huy IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_phieu_xuat_huy))';


--
-- Name: CONSTRAINT kiem_tra__phieu_xuat_huy__ma_dung_dinh_dang ON phieu_xuat_huy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_xuat_huy__ma_dung_dinh_dang ON public.phieu_xuat_huy IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_phieu_xuat_huy ~ ''^[A-Z0-9][A-Z0-9_-]{0,31}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__phieu_xuat_huy__ma_khong_rong ON phieu_xuat_huy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_xuat_huy__ma_khong_rong ON public.phieu_xuat_huy IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_phieu_xuat_huy))';


--
-- Name: CONSTRAINT kiem_tra__phieu_xuat_huy__ma_mot_dong ON phieu_xuat_huy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__phieu_xuat_huy__ma_mot_dong ON public.phieu_xuat_huy IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_phieu_xuat_huy))';


--
-- Name: phieu_xuat_huy_id_phieu_xuat_huy_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.phieu_xuat_huy ALTER COLUMN id_phieu_xuat_huy ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.phieu_xuat_huy_id_phieu_xuat_huy_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: quan_sat_ban_hang; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quan_sat_ban_hang (
    id_quan_sat_ban_hang bigint NOT NULL,
    ma_atc_nguon text NOT NULL,
    ngay_ban date NOT NULL,
    so_luong double precision NOT NULL,
    id_nguon_du_lieu bigint NOT NULL,
    CONSTRAINT kiem_tra__quan_sat__luong_huu_han_khong_am CHECK (((so_luong >= (0.0)::double precision) AND (so_luong < 'Infinity'::double precision))),
    CONSTRAINT kiem_tra__quan_sat__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_atc_nguon)),
    CONSTRAINT kiem_tra__quan_sat__ma_dung_dinh_dang CHECK ((ma_atc_nguon ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'::text)),
    CONSTRAINT kiem_tra__quan_sat__ma_khong_rong CHECK (public.khong_rong(ma_atc_nguon)),
    CONSTRAINT kiem_tra__quan_sat__ma_mot_dong CHECK (public.la_mot_dong(ma_atc_nguon))
);


--
-- Name: TABLE quan_sat_ban_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.quan_sat_ban_hang IS 'Mỗi hàng là một quan sát ngày/ATC của dữ liệu công khai, không thuộc chi nhánh mô phỏng.';


--
-- Name: COLUMN quan_sat_ban_hang.id_quan_sat_ban_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.quan_sat_ban_hang.id_quan_sat_ban_hang IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN quan_sat_ban_hang.ma_atc_nguon; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.quan_sat_ban_hang.ma_atc_nguon IS 'Mã nhóm ATC của chuỗi công khai; văn bản một dòng.';


--
-- Name: COLUMN quan_sat_ban_hang.ngay_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.quan_sat_ban_hang.ngay_ban IS 'Ngày quan sát trong nguồn 2014–2019.';


--
-- Name: COLUMN quan_sat_ban_hang.so_luong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.quan_sat_ban_hang.so_luong IS 'Lượng bán công khai; giá trị xấp xỉ, đơn vị theo nguồn công khai.';


--
-- Name: COLUMN quan_sat_ban_hang.id_nguon_du_lieu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.quan_sat_ban_hang.id_nguon_du_lieu IS 'Phiên bản nguồn.';


--
-- Name: CONSTRAINT kiem_tra__quan_sat__luong_huu_han_khong_am ON quan_sat_ban_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__quan_sat__luong_huu_han_khong_am ON public.quan_sat_ban_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((so_luong >= (0.0)::double precision) AND (so_luong < ''Infinity''::double precision)))';


--
-- Name: CONSTRAINT kiem_tra__quan_sat__ma_da_cat_khoang_trang ON quan_sat_ban_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__quan_sat__ma_da_cat_khoang_trang ON public.quan_sat_ban_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_atc_nguon))';


--
-- Name: CONSTRAINT kiem_tra__quan_sat__ma_dung_dinh_dang ON quan_sat_ban_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__quan_sat__ma_dung_dinh_dang ON public.quan_sat_ban_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_atc_nguon ~ ''^[A-Z0-9][A-Z0-9_-]{0,31}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__quan_sat__ma_khong_rong ON quan_sat_ban_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__quan_sat__ma_khong_rong ON public.quan_sat_ban_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_atc_nguon))';


--
-- Name: CONSTRAINT kiem_tra__quan_sat__ma_mot_dong ON quan_sat_ban_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__quan_sat__ma_mot_dong ON public.quan_sat_ban_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_atc_nguon))';


--
-- Name: quan_sat_ban_hang_id_quan_sat_ban_hang_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.quan_sat_ban_hang ALTER COLUMN id_quan_sat_ban_hang ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.quan_sat_ban_hang_id_quan_sat_ban_hang_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: quy_doi_bao_goi; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quy_doi_bao_goi (
    id_quy_doi_bao_goi bigint NOT NULL,
    ten_quy_doi_bao_goi text NOT NULL,
    he_so integer NOT NULL,
    id_thuoc bigint NOT NULL,
    CONSTRAINT kiem_tra__quy_doi_bao_goi__he_so_duong CHECK ((he_so > 0)),
    CONSTRAINT kiem_tra__quy_doi_bao_goi__ten_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ten_quy_doi_bao_goi)),
    CONSTRAINT kiem_tra__quy_doi_bao_goi__ten_khong_rong CHECK (public.khong_rong(ten_quy_doi_bao_goi)),
    CONSTRAINT kiem_tra__quy_doi_bao_goi__ten_mot_dong CHECK (public.la_mot_dong(ten_quy_doi_bao_goi))
);


--
-- Name: TABLE quy_doi_bao_goi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.quy_doi_bao_goi IS 'Mỗi hàng là một bao gói quy đổi của riêng một thuốc.';


--
-- Name: COLUMN quy_doi_bao_goi.id_quy_doi_bao_goi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.quy_doi_bao_goi.id_quy_doi_bao_goi IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN quy_doi_bao_goi.ten_quy_doi_bao_goi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.quy_doi_bao_goi.ten_quy_doi_bao_goi IS 'Tên bao gói, ví dụ hộp; văn bản một dòng.';


--
-- Name: COLUMN quy_doi_bao_goi.he_so; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.quy_doi_bao_goi.he_so IS 'Số đơn vị cơ sở trong một bao gói; giới hạn số nguyên PostgreSQL 32 bit.';


--
-- Name: COLUMN quy_doi_bao_goi.id_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.quy_doi_bao_goi.id_thuoc IS 'Sản phẩm sở hữu quy đổi.';


--
-- Name: CONSTRAINT kiem_tra__quy_doi_bao_goi__he_so_duong ON quy_doi_bao_goi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__quy_doi_bao_goi__he_so_duong ON public.quy_doi_bao_goi IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((he_so > 0))';


--
-- Name: CONSTRAINT kiem_tra__quy_doi_bao_goi__ten_da_cat_khoang_trang ON quy_doi_bao_goi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__quy_doi_bao_goi__ten_da_cat_khoang_trang ON public.quy_doi_bao_goi IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ten_quy_doi_bao_goi))';


--
-- Name: CONSTRAINT kiem_tra__quy_doi_bao_goi__ten_khong_rong ON quy_doi_bao_goi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__quy_doi_bao_goi__ten_khong_rong ON public.quy_doi_bao_goi IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ten_quy_doi_bao_goi))';


--
-- Name: CONSTRAINT kiem_tra__quy_doi_bao_goi__ten_mot_dong ON quy_doi_bao_goi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__quy_doi_bao_goi__ten_mot_dong ON public.quy_doi_bao_goi IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ten_quy_doi_bao_goi))';


--
-- Name: quy_doi_bao_goi_id_quy_doi_bao_goi_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.quy_doi_bao_goi ALTER COLUMN id_quy_doi_bao_goi ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.quy_doi_bao_goi_id_quy_doi_bao_goi_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: quyen_cua_nhom; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quyen_cua_nhom (
    id_quyen_cua_nhom bigint NOT NULL,
    ma_quyen text NOT NULL,
    id_nhom_quyen bigint NOT NULL,
    CONSTRAINT kiem_tra__quyen_cua_nhom__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_quyen)),
    CONSTRAINT kiem_tra__quyen_cua_nhom__ma_dung_dinh_dang CHECK ((ma_quyen ~ '^[a-z_]+\.[a-z_]+$'::text)),
    CONSTRAINT kiem_tra__quyen_cua_nhom__ma_khong_rong CHECK (public.khong_rong(ma_quyen)),
    CONSTRAINT kiem_tra__quyen_cua_nhom__ma_mot_dong CHECK (public.la_mot_dong(ma_quyen))
);


--
-- Name: TABLE quyen_cua_nhom; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.quyen_cua_nhom IS 'Mỗi hàng là một quyền mà một nhóm quyền được thực hiện.';


--
-- Name: COLUMN quyen_cua_nhom.id_quyen_cua_nhom; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.quyen_cua_nhom.id_quyen_cua_nhom IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN quyen_cua_nhom.ma_quyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.quyen_cua_nhom.ma_quyen IS 'Mã quyền dạng nhóm.hành_động, lấy từ danh mục quyền trong mã nguồn.';


--
-- Name: COLUMN quyen_cua_nhom.id_nhom_quyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.quyen_cua_nhom.id_nhom_quyen IS 'Nhóm được cấp quyền.';


--
-- Name: CONSTRAINT kiem_tra__quyen_cua_nhom__ma_da_cat_khoang_trang ON quyen_cua_nhom; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__quyen_cua_nhom__ma_da_cat_khoang_trang ON public.quyen_cua_nhom IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_quyen))';


--
-- Name: CONSTRAINT kiem_tra__quyen_cua_nhom__ma_dung_dinh_dang ON quyen_cua_nhom; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__quyen_cua_nhom__ma_dung_dinh_dang ON public.quyen_cua_nhom IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_quyen ~ ''^[a-z_]+\.[a-z_]+$''::text))';


--
-- Name: CONSTRAINT kiem_tra__quyen_cua_nhom__ma_khong_rong ON quyen_cua_nhom; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__quyen_cua_nhom__ma_khong_rong ON public.quyen_cua_nhom IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_quyen))';


--
-- Name: CONSTRAINT kiem_tra__quyen_cua_nhom__ma_mot_dong ON quyen_cua_nhom; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__quyen_cua_nhom__ma_mot_dong ON public.quyen_cua_nhom IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_quyen))';


--
-- Name: quyen_cua_nhom_id_quyen_cua_nhom_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.quyen_cua_nhom ALTER COLUMN id_quyen_cua_nhom ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.quyen_cua_nhom_id_quyen_cua_nhom_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: quyen_rieng_tai_khoan; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quyen_rieng_tai_khoan (
    id_quyen_rieng_tai_khoan bigint NOT NULL,
    ma_quyen text NOT NULL,
    duoc_phep boolean NOT NULL,
    id_tai_khoan bigint NOT NULL,
    CONSTRAINT kiem_tra__quyen_rieng_tai_khoan__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_quyen)),
    CONSTRAINT kiem_tra__quyen_rieng_tai_khoan__ma_dung_dinh_dang CHECK ((ma_quyen ~ '^[a-z_]+\.[a-z_]+$'::text)),
    CONSTRAINT kiem_tra__quyen_rieng_tai_khoan__ma_khong_rong CHECK (public.khong_rong(ma_quyen)),
    CONSTRAINT kiem_tra__quyen_rieng_tai_khoan__ma_mot_dong CHECK (public.la_mot_dong(ma_quyen))
);


--
-- Name: TABLE quyen_rieng_tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.quyen_rieng_tai_khoan IS 'Mỗi hàng là một quyền được cho thêm hoặc chặn riêng cho một tài khoản.';


--
-- Name: COLUMN quyen_rieng_tai_khoan.id_quyen_rieng_tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.quyen_rieng_tai_khoan.id_quyen_rieng_tai_khoan IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN quyen_rieng_tai_khoan.ma_quyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.quyen_rieng_tai_khoan.ma_quyen IS 'Mã quyền dạng nhóm.hành_động, lấy từ danh mục quyền trong mã nguồn.';


--
-- Name: COLUMN quyen_rieng_tai_khoan.duoc_phep; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.quyen_rieng_tai_khoan.duoc_phep IS 'TRUE cho thêm quyền ngoài nhóm; FALSE chặn quyền dù nhóm có cấp.';


--
-- Name: COLUMN quyen_rieng_tai_khoan.id_tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.quyen_rieng_tai_khoan.id_tai_khoan IS 'Tài khoản được tinh chỉnh quyền.';


--
-- Name: CONSTRAINT kiem_tra__quyen_rieng_tai_khoan__ma_da_cat_khoang_trang ON quyen_rieng_tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__quyen_rieng_tai_khoan__ma_da_cat_khoang_trang ON public.quyen_rieng_tai_khoan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_quyen))';


--
-- Name: CONSTRAINT kiem_tra__quyen_rieng_tai_khoan__ma_dung_dinh_dang ON quyen_rieng_tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__quyen_rieng_tai_khoan__ma_dung_dinh_dang ON public.quyen_rieng_tai_khoan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_quyen ~ ''^[a-z_]+\.[a-z_]+$''::text))';


--
-- Name: CONSTRAINT kiem_tra__quyen_rieng_tai_khoan__ma_khong_rong ON quyen_rieng_tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__quyen_rieng_tai_khoan__ma_khong_rong ON public.quyen_rieng_tai_khoan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_quyen))';


--
-- Name: CONSTRAINT kiem_tra__quyen_rieng_tai_khoan__ma_mot_dong ON quyen_rieng_tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__quyen_rieng_tai_khoan__ma_mot_dong ON public.quyen_rieng_tai_khoan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_quyen))';


--
-- Name: quyen_rieng_tai_khoan_id_quyen_rieng_tai_khoan_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.quyen_rieng_tai_khoan ALTER COLUMN id_quyen_rieng_tai_khoan ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.quyen_rieng_tai_khoan_id_quyen_rieng_tai_khoan_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: tai_khoan; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tai_khoan (
    id_tai_khoan bigint NOT NULL,
    ten_dang_nhap text NOT NULL,
    mat_khau_bam character varying(128) NOT NULL,
    dang_hoat_dong boolean DEFAULT true NOT NULL,
    la_quan_tri_he_thong boolean DEFAULT false NOT NULL,
    thoi_diem_dang_nhap_cuoi timestamp with time zone,
    id_chi_nhanh bigint,
    vai_tro text DEFAULT 'khach_hang'::text NOT NULL,
    da_xac_thuc_email boolean DEFAULT false NOT NULL,
    email text,
    ho_ten text DEFAULT ''::text NOT NULL,
    so_dien_thoai text DEFAULT ''::text NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_nhom_quyen bigint,
    so_lan_dang_nhap_sai smallint DEFAULT 0 NOT NULL,
    thoi_diem_mo_khoa_dang_nhap timestamp with time zone,
    CONSTRAINT kiem_tra__tai_khoan__chi_nhanh_dung_vai_tro CHECK ((((id_chi_nhanh IS NOT NULL) AND (vai_tro = ANY (ARRAY['quan_ly_chi_nhanh'::text, 'nhan_vien'::text]))) OR ((id_chi_nhanh IS NULL) AND (vai_tro = ANY (ARRAY['quan_tri_chuoi'::text, 'khach_hang'::text]))))),
    CONSTRAINT kiem_tra__tai_khoan__email_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(email)),
    CONSTRAINT kiem_tra__tai_khoan__email_dung_dinh_dang CHECK ((email ~ '^[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)+$'::text)),
    CONSTRAINT kiem_tra__tai_khoan__email_khong_rong CHECK (public.khong_rong(email)),
    CONSTRAINT kiem_tra__tai_khoan__email_mot_dong CHECK (public.la_mot_dong(email)),
    CONSTRAINT kiem_tra__tai_khoan__ho_ten_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ho_ten)),
    CONSTRAINT kiem_tra__tai_khoan__ho_ten_mot_dong CHECK (public.la_mot_dong(ho_ten)),
    CONSTRAINT kiem_tra__tai_khoan__mat_khau_bam_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang((mat_khau_bam)::text)),
    CONSTRAINT kiem_tra__tai_khoan__mat_khau_bam_khong_rong CHECK (public.khong_rong((mat_khau_bam)::text)),
    CONSTRAINT kiem_tra__tai_khoan__mat_khau_bam_mot_dong CHECK (public.la_mot_dong((mat_khau_bam)::text)),
    CONSTRAINT kiem_tra__tai_khoan__nhom_quyen_dung_vai_tro CHECK (((id_nhom_quyen IS NULL) OR (vai_tro = ANY (ARRAY['quan_ly_chi_nhanh'::text, 'nhan_vien'::text])))),
    CONSTRAINT kiem_tra__tai_khoan__quan_tri_he_thong_dung_vai_tro CHECK (((NOT la_quan_tri_he_thong) OR (vai_tro = 'quan_tri_chuoi'::text))),
    CONSTRAINT kiem_tra__tai_khoan__so_dien_thoai_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(so_dien_thoai)),
    CONSTRAINT kiem_tra__tai_khoan__so_dien_thoai_dung_dinh_dang CHECK ((so_dien_thoai ~ '^((0(3[2-9]|5[2-9]|7[06-9]|8[1-9]|9[0-9])[0-9]{7}|02[0-9]{9}))?$'::text)),
    CONSTRAINT kiem_tra__tai_khoan__so_dien_thoai_mot_dong CHECK (public.la_mot_dong(so_dien_thoai)),
    CONSTRAINT kiem_tra__tai_khoan__so_lan_dang_nhap_sai_hop_le CHECK (((so_lan_dang_nhap_sai >= 0) AND (so_lan_dang_nhap_sai <= 5))),
    CONSTRAINT kiem_tra__tai_khoan__ten_dang_nhap_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ten_dang_nhap)),
    CONSTRAINT kiem_tra__tai_khoan__ten_dang_nhap_khong_rong CHECK (public.khong_rong(ten_dang_nhap)),
    CONSTRAINT kiem_tra__tai_khoan__ten_dang_nhap_mot_dong CHECK (public.la_mot_dong(ten_dang_nhap)),
    CONSTRAINT kiem_tra__tai_khoan__vai_tro_hop_le CHECK ((vai_tro = ANY (ARRAY['quan_tri_chuoi'::text, 'quan_ly_chi_nhanh'::text, 'nhan_vien'::text, 'khach_hang'::text]))),
    CONSTRAINT kiem_tra__tai_khoan__xac_thuc_can_email CHECK (((NOT da_xac_thuc_email) OR (email IS NOT NULL)))
);


--
-- Name: TABLE tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.tai_khoan IS 'Mỗi hàng là một tài khoản xác thực có một vai trò nghiệp vụ.';


--
-- Name: COLUMN tai_khoan.id_tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tai_khoan.id_tai_khoan IS 'Định danh nội bộ do PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN tai_khoan.ten_dang_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tai_khoan.ten_dang_nhap IS 'Tên một dòng người tạo nhập, duy nhất và phân biệt hoa thường theo Q10.';


--
-- Name: COLUMN tai_khoan.mat_khau_bam; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tai_khoan.mat_khau_bam IS 'Chuỗi băm hoặc dấu mật khẩu không sử dụng được do Django tạo; một dòng, giới hạn 128 ký tự theo AbstractBaseUser.password của Django.';


--
-- Name: COLUMN tai_khoan.dang_hoat_dong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tai_khoan.dang_hoat_dong IS 'Cho phép cơ chế xác thực Django nhận tài khoản; hệ thống ghi.';


--
-- Name: COLUMN tai_khoan.la_quan_tri_he_thong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tai_khoan.la_quan_tri_he_thong IS 'Cờ quản trị kỹ thuật của Django tạo bằng createsuperuser, chỉ cấp cho quản trị chuỗi.';


--
-- Name: COLUMN tai_khoan.thoi_diem_dang_nhap_cuoi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tai_khoan.thoi_diem_dang_nhap_cuoi IS 'Thời điểm đăng nhập thành công gần nhất do Django cập nhật; NULL nghĩa là chưa ghi nhận lần đăng nhập.';


--
-- Name: COLUMN tai_khoan.id_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tai_khoan.id_chi_nhanh IS 'Chi nhánh làm việc của quản lý/nhân viên; NULL với khách và quản trị chuỗi.';


--
-- Name: COLUMN tai_khoan.vai_tro; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tai_khoan.vai_tro IS 'Vai trò nghiệp vụ do quản trị cấp; quan_tri_chuoi quản lý chuỗi, quan_ly_chi_nhanh quản lý cơ sở, nhan_vien làm việc tại cơ sở, khach_hang đặt giữ và chat.';


--
-- Name: COLUMN tai_khoan.da_xac_thuc_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tai_khoan.da_xac_thuc_email IS 'Người dùng đã nhập đúng mã OTP gửi tới email hiện tại.';


--
-- Name: COLUMN tai_khoan.email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tai_khoan.email IS 'Email đã chuẩn hóa chữ thường, duy nhất toàn hệ thống; NULL khi chưa khai báo.';


--
-- Name: COLUMN tai_khoan.ho_ten; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tai_khoan.ho_ten IS 'Họ tên người dùng tự khai hoặc quản trị nhập; văn bản một dòng, rỗng khi chưa khai.';


--
-- Name: COLUMN tai_khoan.so_dien_thoai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tai_khoan.so_dien_thoai IS 'Số điện thoại Việt Nam dạng nội địa 10 hoặc 11 chữ số; rỗng khi chưa khai.';


--
-- Name: COLUMN tai_khoan.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tai_khoan.thoi_diem_tao IS 'Thời điểm tài khoản được tạo.';


--
-- Name: COLUMN tai_khoan.id_nhom_quyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tai_khoan.id_nhom_quyen IS 'Nhóm quyền của quản lý hoặc nhân viên; NULL thì dùng nhóm mặc định của vai trò. Quản trị chuỗi luôn có mọi quyền nên không gán nhóm.';


--
-- Name: COLUMN tai_khoan.so_lan_dang_nhap_sai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tai_khoan.so_lan_dang_nhap_sai IS 'Số lần nhập sai mật khẩu liên tiếp; đạt 5 thì khóa đăng nhập 15 phút và đếm lại, đăng nhập đúng thì về 0.';


--
-- Name: COLUMN tai_khoan.thoi_diem_mo_khoa_dang_nhap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tai_khoan.thoi_diem_mo_khoa_dang_nhap IS 'Trước thời điểm này không nhận đăng nhập bằng mật khẩu; NULL khi không bị khóa.';


--
-- Name: CONSTRAINT kiem_tra__tai_khoan__chi_nhanh_dung_vai_tro ON tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tai_khoan__chi_nhanh_dung_vai_tro ON public.tai_khoan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((((id_chi_nhanh IS NOT NULL) AND (vai_tro = ANY (ARRAY[''quan_ly_chi_nhanh''::text, ''nhan_vien''::text]))) OR ((id_chi_nhanh IS NULL) AND (vai_tro = ANY (ARRAY[''quan_tri_chuoi''::text, ''khach_hang''::text])))))';


--
-- Name: CONSTRAINT kiem_tra__tai_khoan__email_da_cat_khoang_trang ON tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tai_khoan__email_da_cat_khoang_trang ON public.tai_khoan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(email))';


--
-- Name: CONSTRAINT kiem_tra__tai_khoan__email_dung_dinh_dang ON tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tai_khoan__email_dung_dinh_dang ON public.tai_khoan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((email ~ ''^[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)+$''::text))';


--
-- Name: CONSTRAINT kiem_tra__tai_khoan__email_khong_rong ON tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tai_khoan__email_khong_rong ON public.tai_khoan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(email))';


--
-- Name: CONSTRAINT kiem_tra__tai_khoan__email_mot_dong ON tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tai_khoan__email_mot_dong ON public.tai_khoan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(email))';


--
-- Name: CONSTRAINT kiem_tra__tai_khoan__ho_ten_da_cat_khoang_trang ON tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tai_khoan__ho_ten_da_cat_khoang_trang ON public.tai_khoan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ho_ten))';


--
-- Name: CONSTRAINT kiem_tra__tai_khoan__ho_ten_mot_dong ON tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tai_khoan__ho_ten_mot_dong ON public.tai_khoan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ho_ten))';


--
-- Name: CONSTRAINT kiem_tra__tai_khoan__mat_khau_bam_da_cat_khoang_trang ON tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tai_khoan__mat_khau_bam_da_cat_khoang_trang ON public.tai_khoan IS 'Chuỗi mật khẩu băm không có khoảng trắng hai đầu theo tập Unicode cố định.';


--
-- Name: CONSTRAINT kiem_tra__tai_khoan__mat_khau_bam_khong_rong ON tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tai_khoan__mat_khau_bam_khong_rong ON public.tai_khoan IS 'Chuỗi do cơ chế mật khẩu Django tạo phải có ký tự ngoài tập khoảng trắng.';


--
-- Name: CONSTRAINT kiem_tra__tai_khoan__mat_khau_bam_mot_dong ON tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tai_khoan__mat_khau_bam_mot_dong ON public.tai_khoan IS 'Chuỗi mật khẩu băm không chứa ký tự điều khiển hoặc ngắt dòng.';


--
-- Name: CONSTRAINT kiem_tra__tai_khoan__nhom_quyen_dung_vai_tro ON tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tai_khoan__nhom_quyen_dung_vai_tro ON public.tai_khoan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((id_nhom_quyen IS NULL) OR (vai_tro = ANY (ARRAY[''quan_ly_chi_nhanh''::text, ''nhan_vien''::text]))))';


--
-- Name: CONSTRAINT kiem_tra__tai_khoan__quan_tri_he_thong_dung_vai_tro ON tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tai_khoan__quan_tri_he_thong_dung_vai_tro ON public.tai_khoan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((NOT la_quan_tri_he_thong) OR (vai_tro = ''quan_tri_chuoi''::text)))';


--
-- Name: CONSTRAINT kiem_tra__tai_khoan__so_dien_thoai_da_cat_khoang_trang ON tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tai_khoan__so_dien_thoai_da_cat_khoang_trang ON public.tai_khoan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(so_dien_thoai))';


--
-- Name: CONSTRAINT kiem_tra__tai_khoan__so_dien_thoai_dung_dinh_dang ON tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tai_khoan__so_dien_thoai_dung_dinh_dang ON public.tai_khoan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((so_dien_thoai ~ ''^((0(3[2-9]|5[2-9]|7[06-9]|8[1-9]|9[0-9])[0-9]{7}|02[0-9]{9}))?$''::text))';


--
-- Name: CONSTRAINT kiem_tra__tai_khoan__so_dien_thoai_mot_dong ON tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tai_khoan__so_dien_thoai_mot_dong ON public.tai_khoan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(so_dien_thoai))';


--
-- Name: CONSTRAINT kiem_tra__tai_khoan__so_lan_dang_nhap_sai_hop_le ON tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tai_khoan__so_lan_dang_nhap_sai_hop_le ON public.tai_khoan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((so_lan_dang_nhap_sai >= 0) AND (so_lan_dang_nhap_sai <= 5)))';


--
-- Name: CONSTRAINT kiem_tra__tai_khoan__ten_dang_nhap_da_cat_khoang_trang ON tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tai_khoan__ten_dang_nhap_da_cat_khoang_trang ON public.tai_khoan IS 'Hai đầu tên không có khoảng trắng theo đúng tập Unicode của hàm DB, không phụ thuộc locale.';


--
-- Name: CONSTRAINT kiem_tra__tai_khoan__ten_dang_nhap_khong_rong ON tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tai_khoan__ten_dang_nhap_khong_rong ON public.tai_khoan IS 'Tên phải có ký tự ngoài tập khoảng trắng cố định; hàm STRICT đi cùng NOT NULL.';


--
-- Name: CONSTRAINT kiem_tra__tai_khoan__ten_dang_nhap_mot_dong ON tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tai_khoan__ten_dang_nhap_mot_dong ON public.tai_khoan IS 'Tên không chứa ký tự điều khiển hoặc ngắt dòng U+2028/U+2029.';


--
-- Name: CONSTRAINT kiem_tra__tai_khoan__vai_tro_hop_le ON tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tai_khoan__vai_tro_hop_le ON public.tai_khoan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((vai_tro = ANY (ARRAY[''quan_tri_chuoi''::text, ''quan_ly_chi_nhanh''::text, ''nhan_vien''::text, ''khach_hang''::text])))';


--
-- Name: CONSTRAINT kiem_tra__tai_khoan__xac_thuc_can_email ON tai_khoan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tai_khoan__xac_thuc_can_email ON public.tai_khoan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((NOT da_xac_thuc_email) OR (email IS NOT NULL)))';


--
-- Name: tai_khoan_id_tai_khoan_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.tai_khoan ALTER COLUMN id_tai_khoan ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.tai_khoan_id_tai_khoan_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: thong_tin_cua_hang; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.thong_tin_cua_hang (
    id_thong_tin_cua_hang smallint NOT NULL,
    ten_thuong_hieu text NOT NULL,
    khau_hieu text DEFAULT ''::text NOT NULL,
    hotline text NOT NULL,
    email_lien_he text NOT NULL,
    dia_chi_tru_so text NOT NULL,
    gio_lam_viec text NOT NULL,
    giay_phep_kinh_doanh text DEFAULT ''::text NOT NULL,
    thoi_diem_cap_nhat timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    CONSTRAINT kiem_tra__cua_hang__chi_mot_hang CHECK ((id_thong_tin_cua_hang = 1)),
    CONSTRAINT kiem_tra__cua_hang__dia_chi_tru_so_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(dia_chi_tru_so)),
    CONSTRAINT kiem_tra__cua_hang__dia_chi_tru_so_khong_rong CHECK (public.khong_rong(dia_chi_tru_so)),
    CONSTRAINT kiem_tra__cua_hang__dia_chi_tru_so_mot_dong CHECK (public.la_mot_dong(dia_chi_tru_so)),
    CONSTRAINT kiem_tra__cua_hang__email_lien_he_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(email_lien_he)),
    CONSTRAINT kiem_tra__cua_hang__email_lien_he_dung_dinh_dang CHECK ((email_lien_he ~ '^[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)+$'::text)),
    CONSTRAINT kiem_tra__cua_hang__email_lien_he_khong_rong CHECK (public.khong_rong(email_lien_he)),
    CONSTRAINT kiem_tra__cua_hang__email_lien_he_mot_dong CHECK (public.la_mot_dong(email_lien_he)),
    CONSTRAINT kiem_tra__cua_hang__giay_phep_kinh_doanh_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(giay_phep_kinh_doanh)),
    CONSTRAINT kiem_tra__cua_hang__giay_phep_kinh_doanh_mot_dong CHECK (public.la_mot_dong(giay_phep_kinh_doanh)),
    CONSTRAINT kiem_tra__cua_hang__gio_lam_viec_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(gio_lam_viec)),
    CONSTRAINT kiem_tra__cua_hang__gio_lam_viec_khong_rong CHECK (public.khong_rong(gio_lam_viec)),
    CONSTRAINT kiem_tra__cua_hang__gio_lam_viec_mot_dong CHECK (public.la_mot_dong(gio_lam_viec)),
    CONSTRAINT kiem_tra__cua_hang__hotline_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(hotline)),
    CONSTRAINT kiem_tra__cua_hang__hotline_dung_dinh_dang CHECK ((hotline ~ '^((0(3[2-9]|5[2-9]|7[06-9]|8[1-9]|9[0-9])[0-9]{7}|02[0-9]{9})|1[89]00([0-9]{4}|[0-9]{6}))$'::text)),
    CONSTRAINT kiem_tra__cua_hang__hotline_khong_rong CHECK (public.khong_rong(hotline)),
    CONSTRAINT kiem_tra__cua_hang__hotline_mot_dong CHECK (public.la_mot_dong(hotline)),
    CONSTRAINT kiem_tra__cua_hang__khau_hieu_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(khau_hieu)),
    CONSTRAINT kiem_tra__cua_hang__khau_hieu_mot_dong CHECK (public.la_mot_dong(khau_hieu)),
    CONSTRAINT kiem_tra__cua_hang__ten_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ten_thuong_hieu)),
    CONSTRAINT kiem_tra__cua_hang__ten_khong_rong CHECK (public.khong_rong(ten_thuong_hieu)),
    CONSTRAINT kiem_tra__cua_hang__ten_mot_dong CHECK (public.la_mot_dong(ten_thuong_hieu))
);


--
-- Name: TABLE thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.thong_tin_cua_hang IS 'Một hàng duy nhất chứa thông tin liên hệ chung của chuỗi nhà thuốc.';


--
-- Name: COLUMN thong_tin_cua_hang.id_thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thong_tin_cua_hang.id_thong_tin_cua_hang IS 'Luôn bằng 1: bảng chỉ có một hàng cấu hình.';


--
-- Name: COLUMN thong_tin_cua_hang.ten_thuong_hieu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thong_tin_cua_hang.ten_thuong_hieu IS 'Tên chuỗi nhà thuốc trên đầu trang, email, hóa đơn.';


--
-- Name: COLUMN thong_tin_cua_hang.khau_hieu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thong_tin_cua_hang.khau_hieu IS 'Dòng giới thiệu ngắn dưới tên thương hiệu; rỗng khi không dùng.';


--
-- Name: COLUMN thong_tin_cua_hang.hotline; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thong_tin_cua_hang.hotline IS 'Số điện thoại tư vấn chung, chỉ gồm chữ số: di động 10 số, cố định 11 số hoặc tổng đài 1800/1900 8 hay 10 số.';


--
-- Name: COLUMN thong_tin_cua_hang.email_lien_he; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thong_tin_cua_hang.email_lien_he IS 'Email nhận liên hệ của khách; chữ thường.';


--
-- Name: COLUMN thong_tin_cua_hang.dia_chi_tru_so; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thong_tin_cua_hang.dia_chi_tru_so IS 'Địa chỉ trụ sở in ở chân trang; một dòng.';


--
-- Name: COLUMN thong_tin_cua_hang.gio_lam_viec; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thong_tin_cua_hang.gio_lam_viec IS 'Giờ phục vụ chung hiển thị cho khách; một dòng.';


--
-- Name: COLUMN thong_tin_cua_hang.giay_phep_kinh_doanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thong_tin_cua_hang.giay_phep_kinh_doanh IS 'Số giấy chứng nhận đủ điều kiện kinh doanh dược; rỗng khi chưa nhập.';


--
-- Name: COLUMN thong_tin_cua_hang.thoi_diem_cap_nhat; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thong_tin_cua_hang.thoi_diem_cap_nhat IS 'Lần lưu gần nhất.';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__chi_mot_hang ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__chi_mot_hang ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((id_thong_tin_cua_hang = 1))';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__dia_chi_tru_so_da_cat_khoang_trang ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__dia_chi_tru_so_da_cat_khoang_trang ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(dia_chi_tru_so))';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__dia_chi_tru_so_khong_rong ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__dia_chi_tru_so_khong_rong ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(dia_chi_tru_so))';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__dia_chi_tru_so_mot_dong ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__dia_chi_tru_so_mot_dong ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(dia_chi_tru_so))';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__email_lien_he_da_cat_khoang_trang ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__email_lien_he_da_cat_khoang_trang ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(email_lien_he))';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__email_lien_he_dung_dinh_dang ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__email_lien_he_dung_dinh_dang ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((email_lien_he ~ ''^[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)+$''::text))';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__email_lien_he_khong_rong ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__email_lien_he_khong_rong ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(email_lien_he))';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__email_lien_he_mot_dong ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__email_lien_he_mot_dong ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(email_lien_he))';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__giay_phep_kinh_doanh_da_cat_khoang_trang ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__giay_phep_kinh_doanh_da_cat_khoang_trang ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(giay_phep_kinh_doanh))';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__giay_phep_kinh_doanh_mot_dong ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__giay_phep_kinh_doanh_mot_dong ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(giay_phep_kinh_doanh))';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__gio_lam_viec_da_cat_khoang_trang ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__gio_lam_viec_da_cat_khoang_trang ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(gio_lam_viec))';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__gio_lam_viec_khong_rong ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__gio_lam_viec_khong_rong ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(gio_lam_viec))';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__gio_lam_viec_mot_dong ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__gio_lam_viec_mot_dong ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(gio_lam_viec))';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__hotline_da_cat_khoang_trang ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__hotline_da_cat_khoang_trang ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(hotline))';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__hotline_dung_dinh_dang ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__hotline_dung_dinh_dang ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((hotline ~ ''^((0(3[2-9]|5[2-9]|7[06-9]|8[1-9]|9[0-9])[0-9]{7}|02[0-9]{9})|1[89]00([0-9]{4}|[0-9]{6}))$''::text))';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__hotline_khong_rong ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__hotline_khong_rong ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(hotline))';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__hotline_mot_dong ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__hotline_mot_dong ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(hotline))';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__khau_hieu_da_cat_khoang_trang ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__khau_hieu_da_cat_khoang_trang ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(khau_hieu))';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__khau_hieu_mot_dong ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__khau_hieu_mot_dong ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(khau_hieu))';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__ten_da_cat_khoang_trang ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__ten_da_cat_khoang_trang ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ten_thuong_hieu))';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__ten_khong_rong ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__ten_khong_rong ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ten_thuong_hieu))';


--
-- Name: CONSTRAINT kiem_tra__cua_hang__ten_mot_dong ON thong_tin_cua_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__cua_hang__ten_mot_dong ON public.thong_tin_cua_hang IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ten_thuong_hieu))';


--
-- Name: thuoc; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.thuoc (
    id_thuoc bigint NOT NULL,
    ma_thuoc text NOT NULL,
    ten_thuoc text NOT NULL,
    ham_luong text NOT NULL,
    dang_bao_che text NOT NULL,
    nha_san_xuat text NOT NULL,
    gia_ban numeric(14,0) NOT NULL,
    nguong_canh_bao integer DEFAULT 10 NOT NULL,
    dang_hoat_dong boolean DEFAULT true NOT NULL,
    id_don_vi_tinh bigint NOT NULL,
    id_nhom_atc bigint NOT NULL,
    hoat_chat text DEFAULT ''::text NOT NULL,
    la_thuoc_ke_don boolean DEFAULT false NOT NULL,
    mo_ta_ngan text DEFAULT ''::text NOT NULL,
    nuoc_san_xuat text DEFAULT ''::text NOT NULL,
    quy_cach_dong_goi text DEFAULT ''::text NOT NULL,
    so_dang_ky text DEFAULT ''::text NOT NULL,
    id_danh_muc_san_pham bigint,
    noi_dung_chi_tiet text DEFAULT ''::text NOT NULL,
    CONSTRAINT kiem_tra__thuoc__dang_bao_che_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(dang_bao_che)),
    CONSTRAINT kiem_tra__thuoc__dang_bao_che_khong_rong CHECK (public.khong_rong(dang_bao_che)),
    CONSTRAINT kiem_tra__thuoc__dang_bao_che_mot_dong CHECK (public.la_mot_dong(dang_bao_che)),
    CONSTRAINT kiem_tra__thuoc__gia_ban_khong_am CHECK ((gia_ban >= (0)::numeric)),
    CONSTRAINT kiem_tra__thuoc__gia_ban_khong_phai_nan CHECK ((gia_ban <> 'NaN'::numeric)),
    CONSTRAINT kiem_tra__thuoc__ham_luong_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ham_luong)),
    CONSTRAINT kiem_tra__thuoc__ham_luong_khong_rong CHECK (public.khong_rong(ham_luong)),
    CONSTRAINT kiem_tra__thuoc__ham_luong_mot_dong CHECK (public.la_mot_dong(ham_luong)),
    CONSTRAINT kiem_tra__thuoc__hoat_chat_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(hoat_chat)),
    CONSTRAINT kiem_tra__thuoc__hoat_chat_mot_dong CHECK (public.la_mot_dong(hoat_chat)),
    CONSTRAINT kiem_tra__thuoc__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_thuoc)),
    CONSTRAINT kiem_tra__thuoc__ma_dung_dinh_dang CHECK ((ma_thuoc ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'::text)),
    CONSTRAINT kiem_tra__thuoc__ma_khong_rong CHECK (public.khong_rong(ma_thuoc)),
    CONSTRAINT kiem_tra__thuoc__ma_mot_dong CHECK (public.la_mot_dong(ma_thuoc)),
    CONSTRAINT kiem_tra__thuoc__mo_ta_ngan_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(mo_ta_ngan)),
    CONSTRAINT kiem_tra__thuoc__mo_ta_ngan_mot_dong CHECK (public.la_mot_dong(mo_ta_ngan)),
    CONSTRAINT kiem_tra__thuoc__nguong_canh_bao_khong_am CHECK ((nguong_canh_bao >= 0)),
    CONSTRAINT kiem_tra__thuoc__nha_san_xuat_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(nha_san_xuat)),
    CONSTRAINT kiem_tra__thuoc__nha_san_xuat_khong_rong CHECK (public.khong_rong(nha_san_xuat)),
    CONSTRAINT kiem_tra__thuoc__nha_san_xuat_mot_dong CHECK (public.la_mot_dong(nha_san_xuat)),
    CONSTRAINT kiem_tra__thuoc__noi_dung_chi_tiet_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(noi_dung_chi_tiet)),
    CONSTRAINT kiem_tra__thuoc__nuoc_san_xuat_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(nuoc_san_xuat)),
    CONSTRAINT kiem_tra__thuoc__nuoc_san_xuat_mot_dong CHECK (public.la_mot_dong(nuoc_san_xuat)),
    CONSTRAINT kiem_tra__thuoc__quy_cach_dong_goi_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(quy_cach_dong_goi)),
    CONSTRAINT kiem_tra__thuoc__quy_cach_dong_goi_mot_dong CHECK (public.la_mot_dong(quy_cach_dong_goi)),
    CONSTRAINT kiem_tra__thuoc__so_dang_ky_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(so_dang_ky)),
    CONSTRAINT kiem_tra__thuoc__so_dang_ky_mot_dong CHECK (public.la_mot_dong(so_dang_ky)),
    CONSTRAINT kiem_tra__thuoc__ten_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ten_thuoc)),
    CONSTRAINT kiem_tra__thuoc__ten_khong_rong CHECK (public.khong_rong(ten_thuoc)),
    CONSTRAINT kiem_tra__thuoc__ten_mot_dong CHECK (public.la_mot_dong(ten_thuoc))
);


--
-- Name: TABLE thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.thuoc IS 'Mỗi hàng là một sản phẩm thuốc dùng chung toàn chuỗi.';


--
-- Name: COLUMN thuoc.id_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thuoc.id_thuoc IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN thuoc.ma_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thuoc.ma_thuoc IS 'SKU sản phẩm theo quyết định Q01; văn bản một dòng.';


--
-- Name: COLUMN thuoc.ten_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thuoc.ten_thuoc IS 'Tên thương mại của thuốc; văn bản một dòng.';


--
-- Name: COLUMN thuoc.ham_luong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thuoc.ham_luong IS 'Hàm lượng do quản trị nhập; văn bản một dòng.';


--
-- Name: COLUMN thuoc.dang_bao_che; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thuoc.dang_bao_che IS 'Dạng bào chế; văn bản một dòng.';


--
-- Name: COLUMN thuoc.nha_san_xuat; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thuoc.nha_san_xuat IS 'Nhà sản xuất; văn bản một dòng.';


--
-- Name: COLUMN thuoc.gia_ban; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thuoc.gia_ban IS 'Giá hiện tại một đơn vị cơ sở do quản trị nhập; VND nguyên, trần vận hành 14 chữ số theo quyết định Q02.';


--
-- Name: COLUMN thuoc.nguong_canh_bao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thuoc.nguong_canh_bao IS 'Ngưỡng lượng khả dụng thấp, theo đơn vị cơ sở; giới hạn số nguyên PostgreSQL 32 bit.';


--
-- Name: COLUMN thuoc.dang_hoat_dong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thuoc.dang_hoat_dong IS 'Thuốc còn được dùng cho nghiệp vụ mới.';


--
-- Name: COLUMN thuoc.id_don_vi_tinh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thuoc.id_don_vi_tinh IS 'Đơn vị cơ sở để quản lý lượng của thuốc.';


--
-- Name: COLUMN thuoc.id_nhom_atc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thuoc.id_nhom_atc IS 'Nhóm ATC của sản phẩm.';


--
-- Name: COLUMN thuoc.hoat_chat; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thuoc.hoat_chat IS 'Hoạt chất và hàm lượng từng thành phần; văn bản một dòng, có thể rỗng.';


--
-- Name: COLUMN thuoc.la_thuoc_ke_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thuoc.la_thuoc_ke_don IS 'Thuốc phải bán theo đơn; chỉ bán tại quầy khi dược sĩ đã kiểm tra đơn thuốc (Luật số 44/2024/QH15).';


--
-- Name: COLUMN thuoc.mo_ta_ngan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thuoc.mo_ta_ngan IS 'Mô tả ngắn hiện ở thẻ thuốc; văn bản một dòng, có thể rỗng.';


--
-- Name: COLUMN thuoc.nuoc_san_xuat; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thuoc.nuoc_san_xuat IS 'Nước sản xuất; văn bản một dòng, có thể rỗng.';


--
-- Name: COLUMN thuoc.quy_cach_dong_goi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thuoc.quy_cach_dong_goi IS 'Quy cách đóng gói, ví dụ hộp 10 vỉ x 10 viên; một dòng, có thể rỗng.';


--
-- Name: COLUMN thuoc.so_dang_ky; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thuoc.so_dang_ky IS 'Số đăng ký lưu hành do Bộ Y tế cấp; một dòng, có thể rỗng.';


--
-- Name: COLUMN thuoc.id_danh_muc_san_pham; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thuoc.id_danh_muc_san_pham IS 'Danh mục hiển thị cho khách; NULL khi chưa xếp danh mục.';


--
-- Name: COLUMN thuoc.noi_dung_chi_tiet; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.thuoc.noi_dung_chi_tiet IS 'Nội dung chi tiết hiển thị cho khách (công dụng, liều dùng, chống chỉ định, bảo quản...); một khung soạn thảo, HTML định dạng đã làm sạch bằng nh3.';


--
-- Name: CONSTRAINT kiem_tra__thuoc__dang_bao_che_da_cat_khoang_trang ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__dang_bao_che_da_cat_khoang_trang ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(dang_bao_che))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__dang_bao_che_khong_rong ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__dang_bao_che_khong_rong ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(dang_bao_che))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__dang_bao_che_mot_dong ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__dang_bao_che_mot_dong ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(dang_bao_che))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__gia_ban_khong_am ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__gia_ban_khong_am ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((gia_ban >= (0)::numeric))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__gia_ban_khong_phai_nan ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__gia_ban_khong_phai_nan ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((gia_ban <> ''NaN''::numeric))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__ham_luong_da_cat_khoang_trang ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__ham_luong_da_cat_khoang_trang ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ham_luong))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__ham_luong_khong_rong ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__ham_luong_khong_rong ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ham_luong))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__ham_luong_mot_dong ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__ham_luong_mot_dong ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ham_luong))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__hoat_chat_da_cat_khoang_trang ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__hoat_chat_da_cat_khoang_trang ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(hoat_chat))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__hoat_chat_mot_dong ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__hoat_chat_mot_dong ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(hoat_chat))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__ma_da_cat_khoang_trang ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__ma_da_cat_khoang_trang ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_thuoc))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__ma_dung_dinh_dang ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__ma_dung_dinh_dang ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_thuoc ~ ''^[A-Z0-9][A-Z0-9_-]{0,31}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__ma_khong_rong ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__ma_khong_rong ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_thuoc))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__ma_mot_dong ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__ma_mot_dong ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_thuoc))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__mo_ta_ngan_da_cat_khoang_trang ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__mo_ta_ngan_da_cat_khoang_trang ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(mo_ta_ngan))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__mo_ta_ngan_mot_dong ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__mo_ta_ngan_mot_dong ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(mo_ta_ngan))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__nguong_canh_bao_khong_am ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__nguong_canh_bao_khong_am ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((nguong_canh_bao >= 0))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__nha_san_xuat_da_cat_khoang_trang ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__nha_san_xuat_da_cat_khoang_trang ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(nha_san_xuat))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__nha_san_xuat_khong_rong ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__nha_san_xuat_khong_rong ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(nha_san_xuat))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__nha_san_xuat_mot_dong ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__nha_san_xuat_mot_dong ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(nha_san_xuat))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__noi_dung_chi_tiet_da_cat_khoang_trang ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__noi_dung_chi_tiet_da_cat_khoang_trang ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(noi_dung_chi_tiet))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__nuoc_san_xuat_da_cat_khoang_trang ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__nuoc_san_xuat_da_cat_khoang_trang ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(nuoc_san_xuat))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__nuoc_san_xuat_mot_dong ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__nuoc_san_xuat_mot_dong ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(nuoc_san_xuat))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__quy_cach_dong_goi_da_cat_khoang_trang ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__quy_cach_dong_goi_da_cat_khoang_trang ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(quy_cach_dong_goi))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__quy_cach_dong_goi_mot_dong ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__quy_cach_dong_goi_mot_dong ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(quy_cach_dong_goi))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__so_dang_ky_da_cat_khoang_trang ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__so_dang_ky_da_cat_khoang_trang ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(so_dang_ky))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__so_dang_ky_mot_dong ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__so_dang_ky_mot_dong ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(so_dang_ky))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__ten_da_cat_khoang_trang ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__ten_da_cat_khoang_trang ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ten_thuoc))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__ten_khong_rong ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__ten_khong_rong ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ten_thuoc))';


--
-- Name: CONSTRAINT kiem_tra__thuoc__ten_mot_dong ON thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__thuoc__ten_mot_dong ON public.thuoc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ten_thuoc))';


--
-- Name: thuoc_id_thuoc_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.thuoc ALTER COLUMN id_thuoc ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.thuoc_id_thuoc_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: tin_nhan; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tin_nhan (
    id_tin_nhan bigint NOT NULL,
    ma_tin_nhan text NOT NULL,
    noi_dung_tin_nhan text DEFAULT ''::text NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_cuoc_tro_chuyen bigint NOT NULL,
    id_tai_khoan_gui bigint NOT NULL,
    id_don_hang bigint,
    so_anh smallint DEFAULT 0 NOT NULL,
    id_thuoc bigint,
    CONSTRAINT kiem_tra__tin_nhan__co_chu_hoac_anh CHECK (((NOT (noi_dung_tin_nhan = ''::text)) OR (so_anh > 0))),
    CONSTRAINT kiem_tra__tin_nhan__ma_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_tin_nhan)),
    CONSTRAINT kiem_tra__tin_nhan__ma_dung_dinh_dang CHECK ((ma_tin_nhan ~ '^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'::text)),
    CONSTRAINT kiem_tra__tin_nhan__ma_khong_rong CHECK (public.khong_rong(ma_tin_nhan)),
    CONSTRAINT kiem_tra__tin_nhan__ma_mot_dong CHECK (public.la_mot_dong(ma_tin_nhan)),
    CONSTRAINT kiem_tra__tin_nhan__noi_dung_tin_nhan_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(noi_dung_tin_nhan)),
    CONSTRAINT kiem_tra__tin_nhan__noi_dung_toi_da_2000_ky_tu CHECK ((length(noi_dung_tin_nhan) <= 2000)),
    CONSTRAINT kiem_tra__tin_nhan__so_anh_hop_le CHECK (((so_anh >= 0) AND (so_anh <= 5))),
    CONSTRAINT kiem_tra__tin_nhan__toi_da_mot_the CHECK (((id_thuoc IS NULL) OR (id_don_hang IS NULL)))
);


--
-- Name: TABLE tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.tin_nhan IS 'Mỗi hàng là tin đã được ghi bền vững trước khi phát Redis.';


--
-- Name: COLUMN tin_nhan.id_tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tin_nhan.id_tin_nhan IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN tin_nhan.ma_tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tin_nhan.ma_tin_nhan IS 'UUID chống gửi trùng do trình duyệt tạo; văn bản một dòng.';


--
-- Name: COLUMN tin_nhan.noi_dung_tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tin_nhan.noi_dung_tin_nhan IS 'Nội dung khách/nhân viên nhập; cho phép nhiều dòng. Rỗng khi tin chỉ gồm ảnh (so_anh > 0).';


--
-- Name: COLUMN tin_nhan.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tin_nhan.thoi_diem_tao IS 'Thời điểm hệ thống ghi nhận nghiệp vụ.';


--
-- Name: COLUMN tin_nhan.id_cuoc_tro_chuyen; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tin_nhan.id_cuoc_tro_chuyen IS 'Cuộc trò chuyện sở hữu tin.';


--
-- Name: COLUMN tin_nhan.id_tai_khoan_gui; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tin_nhan.id_tai_khoan_gui IS 'Người gửi được xác định từ phiên đăng nhập.';


--
-- Name: COLUMN tin_nhan.id_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tin_nhan.id_don_hang IS 'Thẻ đơn hàng khi tin hỏi về một đơn; service kiểm đơn thuộc đúng khách và chi nhánh của cuộc trò chuyện. NULL với tin thường.';


--
-- Name: COLUMN tin_nhan.so_anh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tin_nhan.so_anh IS 'Số ảnh đính kèm trong anh_tin_nhan, 0 đến 5; service ghi cùng giao dịch với ảnh. Lưu sẵn để ràng buộc tin phải có chữ hoặc ảnh và để hộp thư hiện ''Đã gửi ảnh''.';


--
-- Name: COLUMN tin_nhan.id_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tin_nhan.id_thuoc IS 'Thẻ sản phẩm ''Bạn đang hỏi về sản phẩm này'' khi khách bắt đầu hỏi từ trang thuốc; NULL với tin thường.';


--
-- Name: CONSTRAINT kiem_tra__tin_nhan__co_chu_hoac_anh ON tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tin_nhan__co_chu_hoac_anh ON public.tin_nhan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((NOT (noi_dung_tin_nhan = ''''::text)) OR (so_anh > 0)))';


--
-- Name: CONSTRAINT kiem_tra__tin_nhan__ma_da_cat_khoang_trang ON tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tin_nhan__ma_da_cat_khoang_trang ON public.tin_nhan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_tin_nhan))';


--
-- Name: CONSTRAINT kiem_tra__tin_nhan__ma_dung_dinh_dang ON tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tin_nhan__ma_dung_dinh_dang ON public.tin_nhan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_tin_nhan ~ ''^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$''::text))';


--
-- Name: CONSTRAINT kiem_tra__tin_nhan__ma_khong_rong ON tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tin_nhan__ma_khong_rong ON public.tin_nhan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_tin_nhan))';


--
-- Name: CONSTRAINT kiem_tra__tin_nhan__ma_mot_dong ON tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tin_nhan__ma_mot_dong ON public.tin_nhan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_tin_nhan))';


--
-- Name: CONSTRAINT kiem_tra__tin_nhan__noi_dung_tin_nhan_da_cat_khoang_trang ON tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tin_nhan__noi_dung_tin_nhan_da_cat_khoang_trang ON public.tin_nhan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(noi_dung_tin_nhan))';


--
-- Name: CONSTRAINT kiem_tra__tin_nhan__noi_dung_toi_da_2000_ky_tu ON tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tin_nhan__noi_dung_toi_da_2000_ky_tu ON public.tin_nhan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((length(noi_dung_tin_nhan) <= 2000))';


--
-- Name: CONSTRAINT kiem_tra__tin_nhan__so_anh_hop_le ON tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tin_nhan__so_anh_hop_le ON public.tin_nhan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((so_anh >= 0) AND (so_anh <= 5)))';


--
-- Name: CONSTRAINT kiem_tra__tin_nhan__toi_da_mot_the ON tin_nhan; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tin_nhan__toi_da_mot_the ON public.tin_nhan IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (((id_thuoc IS NULL) OR (id_don_hang IS NULL)))';


--
-- Name: tin_nhan_id_tin_nhan_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.tin_nhan ALTER COLUMN id_tin_nhan ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.tin_nhan_id_tin_nhan_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: tin_tuc; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tin_tuc (
    id_tin_tuc bigint NOT NULL,
    duong_dan_tin_tuc text NOT NULL,
    tieu_de text NOT NULL,
    tom_tat text NOT NULL,
    noi_dung_tin_tuc text NOT NULL,
    dang_hien_thi boolean DEFAULT true NOT NULL,
    thoi_diem_dang timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    thoi_diem_cap_nhat timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    id_tai_khoan_viet bigint NOT NULL,
    CONSTRAINT kiem_tra__tin_tuc__duong_dan_tin_tuc_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(duong_dan_tin_tuc)),
    CONSTRAINT kiem_tra__tin_tuc__duong_dan_tin_tuc_dung_dinh_dang CHECK ((duong_dan_tin_tuc ~ '^[a-z0-9]+(-[a-z0-9]+)*$'::text)),
    CONSTRAINT kiem_tra__tin_tuc__duong_dan_tin_tuc_khong_rong CHECK (public.khong_rong(duong_dan_tin_tuc)),
    CONSTRAINT kiem_tra__tin_tuc__duong_dan_tin_tuc_mot_dong CHECK (public.la_mot_dong(duong_dan_tin_tuc)),
    CONSTRAINT kiem_tra__tin_tuc__noi_dung_tin_tuc_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(noi_dung_tin_tuc)),
    CONSTRAINT kiem_tra__tin_tuc__noi_dung_tin_tuc_khong_rong CHECK (public.khong_rong(noi_dung_tin_tuc)),
    CONSTRAINT kiem_tra__tin_tuc__tieu_de_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(tieu_de)),
    CONSTRAINT kiem_tra__tin_tuc__tieu_de_khong_rong CHECK (public.khong_rong(tieu_de)),
    CONSTRAINT kiem_tra__tin_tuc__tieu_de_mot_dong CHECK (public.la_mot_dong(tieu_de)),
    CONSTRAINT kiem_tra__tin_tuc__tom_tat_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(tom_tat)),
    CONSTRAINT kiem_tra__tin_tuc__tom_tat_khong_rong CHECK (public.khong_rong(tom_tat)),
    CONSTRAINT kiem_tra__tin_tuc__tom_tat_mot_dong CHECK (public.la_mot_dong(tom_tat))
);


--
-- Name: TABLE tin_tuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.tin_tuc IS 'Mỗi hàng là một bài tin tức, khuyến cáo sức khỏe của chuỗi nhà thuốc.';


--
-- Name: COLUMN tin_tuc.id_tin_tuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tin_tuc.id_tin_tuc IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN tin_tuc.duong_dan_tin_tuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tin_tuc.duong_dan_tin_tuc IS 'Phần cuối đường dẫn /tin-tuc/<...>/, chữ thường không dấu nối bằng gạch ngang.';


--
-- Name: COLUMN tin_tuc.tieu_de; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tin_tuc.tieu_de IS 'Tiêu đề bài viết; một dòng.';


--
-- Name: COLUMN tin_tuc.tom_tat; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tin_tuc.tom_tat IS 'Đoạn giới thiệu trong danh sách tin và thẻ mô tả trang; một dòng.';


--
-- Name: COLUMN tin_tuc.noi_dung_tin_tuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tin_tuc.noi_dung_tin_tuc IS 'Nội dung bài viết; HTML định dạng đã làm sạch bằng nh3.';


--
-- Name: COLUMN tin_tuc.dang_hien_thi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tin_tuc.dang_hien_thi IS 'Tắt để gỡ bài khỏi website mà không xóa.';


--
-- Name: COLUMN tin_tuc.thoi_diem_dang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tin_tuc.thoi_diem_dang IS 'Thời điểm bài xuất hiện trên website; đặt trong tương lai để hẹn giờ đăng.';


--
-- Name: COLUMN tin_tuc.thoi_diem_cap_nhat; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tin_tuc.thoi_diem_cap_nhat IS 'Lần lưu gần nhất.';


--
-- Name: COLUMN tin_tuc.id_tai_khoan_viet; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tin_tuc.id_tai_khoan_viet IS 'Quản trị chuỗi đăng bài lần đầu.';


--
-- Name: CONSTRAINT kiem_tra__tin_tuc__duong_dan_tin_tuc_da_cat_khoang_trang ON tin_tuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tin_tuc__duong_dan_tin_tuc_da_cat_khoang_trang ON public.tin_tuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(duong_dan_tin_tuc))';


--
-- Name: CONSTRAINT kiem_tra__tin_tuc__duong_dan_tin_tuc_dung_dinh_dang ON tin_tuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tin_tuc__duong_dan_tin_tuc_dung_dinh_dang ON public.tin_tuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((duong_dan_tin_tuc ~ ''^[a-z0-9]+(-[a-z0-9]+)*$''::text))';


--
-- Name: CONSTRAINT kiem_tra__tin_tuc__duong_dan_tin_tuc_khong_rong ON tin_tuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tin_tuc__duong_dan_tin_tuc_khong_rong ON public.tin_tuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(duong_dan_tin_tuc))';


--
-- Name: CONSTRAINT kiem_tra__tin_tuc__duong_dan_tin_tuc_mot_dong ON tin_tuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tin_tuc__duong_dan_tin_tuc_mot_dong ON public.tin_tuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(duong_dan_tin_tuc))';


--
-- Name: CONSTRAINT kiem_tra__tin_tuc__noi_dung_tin_tuc_da_cat_khoang_trang ON tin_tuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tin_tuc__noi_dung_tin_tuc_da_cat_khoang_trang ON public.tin_tuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(noi_dung_tin_tuc))';


--
-- Name: CONSTRAINT kiem_tra__tin_tuc__noi_dung_tin_tuc_khong_rong ON tin_tuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tin_tuc__noi_dung_tin_tuc_khong_rong ON public.tin_tuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(noi_dung_tin_tuc))';


--
-- Name: CONSTRAINT kiem_tra__tin_tuc__tieu_de_da_cat_khoang_trang ON tin_tuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tin_tuc__tieu_de_da_cat_khoang_trang ON public.tin_tuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(tieu_de))';


--
-- Name: CONSTRAINT kiem_tra__tin_tuc__tieu_de_khong_rong ON tin_tuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tin_tuc__tieu_de_khong_rong ON public.tin_tuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(tieu_de))';


--
-- Name: CONSTRAINT kiem_tra__tin_tuc__tieu_de_mot_dong ON tin_tuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tin_tuc__tieu_de_mot_dong ON public.tin_tuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(tieu_de))';


--
-- Name: CONSTRAINT kiem_tra__tin_tuc__tom_tat_da_cat_khoang_trang ON tin_tuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tin_tuc__tom_tat_da_cat_khoang_trang ON public.tin_tuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(tom_tat))';


--
-- Name: CONSTRAINT kiem_tra__tin_tuc__tom_tat_khong_rong ON tin_tuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tin_tuc__tom_tat_khong_rong ON public.tin_tuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(tom_tat))';


--
-- Name: CONSTRAINT kiem_tra__tin_tuc__tom_tat_mot_dong ON tin_tuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__tin_tuc__tom_tat_mot_dong ON public.tin_tuc IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(tom_tat))';


--
-- Name: tin_tuc_id_tin_tuc_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.tin_tuc ALTER COLUMN id_tin_tuc ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.tin_tuc_id_tin_tuc_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: ton_kho; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ton_kho (
    id_ton_kho bigint NOT NULL,
    so_luong integer DEFAULT 0 NOT NULL,
    id_chi_nhanh bigint NOT NULL,
    id_lo_thuoc bigint NOT NULL,
    CONSTRAINT kiem_tra__ton_kho__so_luong_khong_am CHECK ((so_luong >= 0))
);


--
-- Name: TABLE ton_kho; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.ton_kho IS 'Mỗi hàng là số dư vật lý của một lô tại một chi nhánh.';


--
-- Name: COLUMN ton_kho.id_ton_kho; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ton_kho.id_ton_kho IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN ton_kho.so_luong; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ton_kho.so_luong IS 'Số lượng vật lý theo đơn vị cơ sở; giới hạn số nguyên PostgreSQL 32 bit.';


--
-- Name: COLUMN ton_kho.id_chi_nhanh; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ton_kho.id_chi_nhanh IS 'Chi nhánh giữ hàng.';


--
-- Name: COLUMN ton_kho.id_lo_thuoc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ton_kho.id_lo_thuoc IS 'Lô hàng tồn.';


--
-- Name: CONSTRAINT kiem_tra__ton_kho__so_luong_khong_am ON ton_kho; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__ton_kho__so_luong_khong_am ON public.ton_kho IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((so_luong >= 0))';


--
-- Name: ton_kho_id_ton_kho_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.ton_kho ALTER COLUMN id_ton_kho ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.ton_kho_id_ton_kho_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: trang_noi_dung; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trang_noi_dung (
    id_trang_noi_dung bigint NOT NULL,
    duong_dan_trang text NOT NULL,
    tieu_de text NOT NULL,
    tom_tat text DEFAULT ''::text NOT NULL,
    noi_dung_trang text NOT NULL,
    dang_hien_thi boolean DEFAULT true NOT NULL,
    thu_tu smallint DEFAULT 0 NOT NULL,
    thoi_diem_cap_nhat timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    CONSTRAINT kiem_tra__trang__duong_dan_trang_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(duong_dan_trang)),
    CONSTRAINT kiem_tra__trang__duong_dan_trang_dung_dinh_dang CHECK ((duong_dan_trang ~ '^[a-z0-9]+(-[a-z0-9]+)*$'::text)),
    CONSTRAINT kiem_tra__trang__duong_dan_trang_khong_rong CHECK (public.khong_rong(duong_dan_trang)),
    CONSTRAINT kiem_tra__trang__duong_dan_trang_mot_dong CHECK (public.la_mot_dong(duong_dan_trang)),
    CONSTRAINT kiem_tra__trang__noi_dung_trang_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(noi_dung_trang)),
    CONSTRAINT kiem_tra__trang__noi_dung_trang_khong_rong CHECK (public.khong_rong(noi_dung_trang)),
    CONSTRAINT kiem_tra__trang__thu_tu_khong_am CHECK ((thu_tu >= 0)),
    CONSTRAINT kiem_tra__trang__tieu_de_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(tieu_de)),
    CONSTRAINT kiem_tra__trang__tieu_de_khong_rong CHECK (public.khong_rong(tieu_de)),
    CONSTRAINT kiem_tra__trang__tieu_de_mot_dong CHECK (public.la_mot_dong(tieu_de)),
    CONSTRAINT kiem_tra__trang__tom_tat_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(tom_tat)),
    CONSTRAINT kiem_tra__trang__tom_tat_mot_dong CHECK (public.la_mot_dong(tom_tat))
);


--
-- Name: TABLE trang_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.trang_noi_dung IS 'Mỗi hàng là một trang thông tin: giới thiệu, chính sách, hướng dẫn.';


--
-- Name: COLUMN trang_noi_dung.id_trang_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.trang_noi_dung.id_trang_noi_dung IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN trang_noi_dung.duong_dan_trang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.trang_noi_dung.duong_dan_trang IS 'Phần cuối đường dẫn /trang/<...>/, chữ thường không dấu nối bằng gạch ngang.';


--
-- Name: COLUMN trang_noi_dung.tieu_de; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.trang_noi_dung.tieu_de IS 'Tiêu đề trang; một dòng.';


--
-- Name: COLUMN trang_noi_dung.tom_tat; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.trang_noi_dung.tom_tat IS 'Câu tóm tắt dưới tiêu đề và trong thẻ mô tả trang; một dòng.';


--
-- Name: COLUMN trang_noi_dung.noi_dung_trang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.trang_noi_dung.noi_dung_trang IS 'Nội dung trang; HTML định dạng đã làm sạch bằng nh3.';


--
-- Name: COLUMN trang_noi_dung.dang_hien_thi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.trang_noi_dung.dang_hien_thi IS 'Tắt để ẩn trang khỏi website và chân trang.';


--
-- Name: COLUMN trang_noi_dung.thu_tu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.trang_noi_dung.thu_tu IS 'Thứ tự liên kết ở chân trang, số nhỏ đứng trước.';


--
-- Name: COLUMN trang_noi_dung.thoi_diem_cap_nhat; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.trang_noi_dung.thoi_diem_cap_nhat IS 'Lần lưu gần nhất.';


--
-- Name: CONSTRAINT kiem_tra__trang__duong_dan_trang_da_cat_khoang_trang ON trang_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__trang__duong_dan_trang_da_cat_khoang_trang ON public.trang_noi_dung IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(duong_dan_trang))';


--
-- Name: CONSTRAINT kiem_tra__trang__duong_dan_trang_dung_dinh_dang ON trang_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__trang__duong_dan_trang_dung_dinh_dang ON public.trang_noi_dung IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((duong_dan_trang ~ ''^[a-z0-9]+(-[a-z0-9]+)*$''::text))';


--
-- Name: CONSTRAINT kiem_tra__trang__duong_dan_trang_khong_rong ON trang_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__trang__duong_dan_trang_khong_rong ON public.trang_noi_dung IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(duong_dan_trang))';


--
-- Name: CONSTRAINT kiem_tra__trang__duong_dan_trang_mot_dong ON trang_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__trang__duong_dan_trang_mot_dong ON public.trang_noi_dung IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(duong_dan_trang))';


--
-- Name: CONSTRAINT kiem_tra__trang__noi_dung_trang_da_cat_khoang_trang ON trang_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__trang__noi_dung_trang_da_cat_khoang_trang ON public.trang_noi_dung IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(noi_dung_trang))';


--
-- Name: CONSTRAINT kiem_tra__trang__noi_dung_trang_khong_rong ON trang_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__trang__noi_dung_trang_khong_rong ON public.trang_noi_dung IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(noi_dung_trang))';


--
-- Name: CONSTRAINT kiem_tra__trang__thu_tu_khong_am ON trang_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__trang__thu_tu_khong_am ON public.trang_noi_dung IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((thu_tu >= 0))';


--
-- Name: CONSTRAINT kiem_tra__trang__tieu_de_da_cat_khoang_trang ON trang_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__trang__tieu_de_da_cat_khoang_trang ON public.trang_noi_dung IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(tieu_de))';


--
-- Name: CONSTRAINT kiem_tra__trang__tieu_de_khong_rong ON trang_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__trang__tieu_de_khong_rong ON public.trang_noi_dung IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(tieu_de))';


--
-- Name: CONSTRAINT kiem_tra__trang__tieu_de_mot_dong ON trang_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__trang__tieu_de_mot_dong ON public.trang_noi_dung IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(tieu_de))';


--
-- Name: CONSTRAINT kiem_tra__trang__tom_tat_da_cat_khoang_trang ON trang_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__trang__tom_tat_da_cat_khoang_trang ON public.trang_noi_dung IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(tom_tat))';


--
-- Name: CONSTRAINT kiem_tra__trang__tom_tat_mot_dong ON trang_noi_dung; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__trang__tom_tat_mot_dong ON public.trang_noi_dung IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(tom_tat))';


--
-- Name: trang_noi_dung_id_trang_noi_dung_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.trang_noi_dung ALTER COLUMN id_trang_noi_dung ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.trang_noi_dung_id_trang_noi_dung_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: yeu_cau_xuat_hoa_don; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.yeu_cau_xuat_hoa_don (
    id_yeu_cau_xuat_hoa_don bigint NOT NULL,
    ten_cong_ty text NOT NULL,
    ma_so_thue text NOT NULL,
    dia_chi_cong_ty text NOT NULL,
    email_nhan_hoa_don text NOT NULL,
    trang_thai text DEFAULT 'cho_xu_ly'::text NOT NULL,
    ghi_chu_xu_ly text DEFAULT ''::text NOT NULL,
    thoi_diem_tao timestamp with time zone DEFAULT statement_timestamp() NOT NULL,
    thoi_diem_xu_ly timestamp with time zone,
    id_don_hang bigint NOT NULL,
    id_tai_khoan_xu_ly bigint,
    ky_hieu_hoa_don text DEFAULT ''::text NOT NULL,
    ly_do_tu_choi text DEFAULT ''::text NOT NULL,
    so_hoa_don text DEFAULT ''::text NOT NULL,
    CONSTRAINT kiem_tra__xuat_hoa_don__dia_chi_cong_ty_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(dia_chi_cong_ty)),
    CONSTRAINT kiem_tra__xuat_hoa_don__dia_chi_cong_ty_khong_rong CHECK (public.khong_rong(dia_chi_cong_ty)),
    CONSTRAINT kiem_tra__xuat_hoa_don__dia_chi_cong_ty_mot_dong CHECK (public.la_mot_dong(dia_chi_cong_ty)),
    CONSTRAINT kiem_tra__xuat_hoa_don__email_nhan_hoa_don_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(email_nhan_hoa_don)),
    CONSTRAINT kiem_tra__xuat_hoa_don__email_nhan_hoa_don_dung_dinh_dang CHECK ((email_nhan_hoa_don ~ '^[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)+$'::text)),
    CONSTRAINT kiem_tra__xuat_hoa_don__email_nhan_hoa_don_khong_rong CHECK (public.khong_rong(email_nhan_hoa_don)),
    CONSTRAINT kiem_tra__xuat_hoa_don__email_nhan_hoa_don_mot_dong CHECK (public.la_mot_dong(email_nhan_hoa_don)),
    CONSTRAINT kiem_tra__xuat_hoa_don__ghi_chu_xu_ly_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ghi_chu_xu_ly)),
    CONSTRAINT kiem_tra__xuat_hoa_don__ket_qua_dung_trang_thai CHECK ((((ky_hieu_hoa_don = ''::text) AND (ly_do_tu_choi = ''::text) AND (so_hoa_don = ''::text) AND (trang_thai = 'cho_xu_ly'::text)) OR ((ly_do_tu_choi = ''::text) AND (trang_thai = 'da_xuat'::text) AND (((ky_hieu_hoa_don = ''::text) AND (so_hoa_don = ''::text)) OR ((NOT (ky_hieu_hoa_don = ''::text)) AND (NOT (so_hoa_don = ''::text))))) OR ((ky_hieu_hoa_don = ''::text) AND (so_hoa_don = ''::text) AND (trang_thai = 'tu_choi'::text) AND (NOT (ly_do_tu_choi = ''::text))))),
    CONSTRAINT kiem_tra__xuat_hoa_don__ky_hieu_hoa_don_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ky_hieu_hoa_don)),
    CONSTRAINT kiem_tra__xuat_hoa_don__ky_hieu_hoa_don_dung_dinh_dang CHECK ((ky_hieu_hoa_don ~ '^([1-9][CK][0-9]{2}[A-Z]{3})?$'::text)),
    CONSTRAINT kiem_tra__xuat_hoa_don__ky_hieu_hoa_don_mot_dong CHECK (public.la_mot_dong(ky_hieu_hoa_don)),
    CONSTRAINT kiem_tra__xuat_hoa_don__ly_do_tu_choi_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ly_do_tu_choi)),
    CONSTRAINT kiem_tra__xuat_hoa_don__ma_so_thue_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ma_so_thue)),
    CONSTRAINT kiem_tra__xuat_hoa_don__ma_so_thue_dung_dinh_dang CHECK ((ma_so_thue ~ '^[0-9]{10}(-[0-9]{3})?$'::text)),
    CONSTRAINT kiem_tra__xuat_hoa_don__ma_so_thue_khong_rong CHECK (public.khong_rong(ma_so_thue)),
    CONSTRAINT kiem_tra__xuat_hoa_don__ma_so_thue_mot_dong CHECK (public.la_mot_dong(ma_so_thue)),
    CONSTRAINT kiem_tra__xuat_hoa_don__so_hoa_don_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(so_hoa_don)),
    CONSTRAINT kiem_tra__xuat_hoa_don__so_hoa_don_dung_dinh_dang CHECK ((so_hoa_don ~ '^([0-9]{1,8})?$'::text)),
    CONSTRAINT kiem_tra__xuat_hoa_don__so_hoa_don_mot_dong CHECK (public.la_mot_dong(so_hoa_don)),
    CONSTRAINT kiem_tra__xuat_hoa_don__ten_cong_ty_da_cat_khoang_trang CHECK (public.da_cat_khoang_trang(ten_cong_ty)),
    CONSTRAINT kiem_tra__xuat_hoa_don__ten_cong_ty_khong_rong CHECK (public.khong_rong(ten_cong_ty)),
    CONSTRAINT kiem_tra__xuat_hoa_don__ten_cong_ty_mot_dong CHECK (public.la_mot_dong(ten_cong_ty)),
    CONSTRAINT kiem_tra__xuat_hoa_don__trang_thai_hop_le CHECK ((trang_thai = ANY (ARRAY['cho_xu_ly'::text, 'da_xuat'::text, 'tu_choi'::text]))),
    CONSTRAINT kiem_tra__xuat_hoa_don__xu_ly_dung_trang_thai CHECK ((((id_tai_khoan_xu_ly IS NULL) AND (thoi_diem_xu_ly IS NULL) AND (trang_thai = 'cho_xu_ly'::text)) OR ((NOT (trang_thai = 'cho_xu_ly'::text)) AND (id_tai_khoan_xu_ly IS NOT NULL) AND (thoi_diem_xu_ly IS NOT NULL) AND (NOT (ghi_chu_xu_ly = ''::text)))))
);


--
-- Name: TABLE yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.yeu_cau_xuat_hoa_don IS 'Mỗi hàng là yêu cầu hóa đơn doanh nghiệp cho một đơn; hóa đơn điện tử phát hành ngoài hệ thống.';


--
-- Name: COLUMN yeu_cau_xuat_hoa_don.id_yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.yeu_cau_xuat_hoa_don.id_yeu_cau_xuat_hoa_don IS 'Định danh nội bộ PostgreSQL cấp, không phải mã hiển thị.';


--
-- Name: COLUMN yeu_cau_xuat_hoa_don.ten_cong_ty; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.yeu_cau_xuat_hoa_don.ten_cong_ty IS 'Tên doanh nghiệp theo đăng ký thuế; một dòng.';


--
-- Name: COLUMN yeu_cau_xuat_hoa_don.ma_so_thue; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.yeu_cau_xuat_hoa_don.ma_so_thue IS 'Mã số thuế 10 chữ số, đơn vị phụ thuộc thêm -XXX.';


--
-- Name: COLUMN yeu_cau_xuat_hoa_don.dia_chi_cong_ty; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.yeu_cau_xuat_hoa_don.dia_chi_cong_ty IS 'Địa chỉ trụ sở theo đăng ký thuế; một dòng.';


--
-- Name: COLUMN yeu_cau_xuat_hoa_don.email_nhan_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.yeu_cau_xuat_hoa_don.email_nhan_hoa_don IS 'Email nhận hóa đơn điện tử; chữ thường.';


--
-- Name: COLUMN yeu_cau_xuat_hoa_don.trang_thai; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.yeu_cau_xuat_hoa_don.trang_thai IS 'cho_xu_ly: chờ nhân viên; da_xuat: đã phát hành ngoài hệ thống; tu_choi.';


--
-- Name: COLUMN yeu_cau_xuat_hoa_don.ghi_chu_xu_ly; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.yeu_cau_xuat_hoa_don.ghi_chu_xu_ly IS 'Câu tóm tắt kết quả gửi khách (ký hiệu và số hóa đơn, hoặc lý do từ chối); rỗng khi chờ xử lý.';


--
-- Name: COLUMN yeu_cau_xuat_hoa_don.thoi_diem_tao; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.yeu_cau_xuat_hoa_don.thoi_diem_tao IS 'Thời điểm khách gửi yêu cầu.';


--
-- Name: COLUMN yeu_cau_xuat_hoa_don.thoi_diem_xu_ly; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.yeu_cau_xuat_hoa_don.thoi_diem_xu_ly IS 'Thời điểm xuất hoặc từ chối; NULL khi chờ xử lý.';


--
-- Name: COLUMN yeu_cau_xuat_hoa_don.id_don_hang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.yeu_cau_xuat_hoa_don.id_don_hang IS 'Đơn cần hóa đơn đứng tên doanh nghiệp, gửi từ lúc đặt tới hết tháng nhận hàng; mỗi đơn một yêu cầu.';


--
-- Name: COLUMN yeu_cau_xuat_hoa_don.id_tai_khoan_xu_ly; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.yeu_cau_xuat_hoa_don.id_tai_khoan_xu_ly IS 'Nhân sự chi nhánh của đơn đã xử lý; NULL khi chờ xử lý.';


--
-- Name: COLUMN yeu_cau_xuat_hoa_don.ky_hieu_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.yeu_cau_xuat_hoa_don.ky_hieu_hoa_don IS 'Ký hiệu mẫu số và ký hiệu hóa đơn điện tử đã phát hành, ví dụ 1C26TAA; rỗng khi chưa xuất hoặc yêu cầu cũ chỉ có ghi chú.';


--
-- Name: COLUMN yeu_cau_xuat_hoa_don.ly_do_tu_choi; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.yeu_cau_xuat_hoa_don.ly_do_tu_choi IS 'Lý do không xuất hóa đơn công ty; chỉ có khi từ chối.';


--
-- Name: COLUMN yeu_cau_xuat_hoa_don.so_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.yeu_cau_xuat_hoa_don.so_hoa_don IS 'Số hóa đơn điện tử, 1 đến 8 chữ số; rỗng khi chưa xuất hoặc yêu cầu cũ.';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__dia_chi_cong_ty_da_cat_khoang_trang ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__dia_chi_cong_ty_da_cat_khoang_trang ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(dia_chi_cong_ty))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__dia_chi_cong_ty_khong_rong ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__dia_chi_cong_ty_khong_rong ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(dia_chi_cong_ty))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__dia_chi_cong_ty_mot_dong ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__dia_chi_cong_ty_mot_dong ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(dia_chi_cong_ty))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__email_nhan_hoa_don_da_cat_khoang_trang ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__email_nhan_hoa_don_da_cat_khoang_trang ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(email_nhan_hoa_don))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__email_nhan_hoa_don_dung_dinh_dang ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__email_nhan_hoa_don_dung_dinh_dang ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((email_nhan_hoa_don ~ ''^[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)+$''::text))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__email_nhan_hoa_don_khong_rong ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__email_nhan_hoa_don_khong_rong ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(email_nhan_hoa_don))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__email_nhan_hoa_don_mot_dong ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__email_nhan_hoa_don_mot_dong ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(email_nhan_hoa_don))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__ghi_chu_xu_ly_da_cat_khoang_trang ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__ghi_chu_xu_ly_da_cat_khoang_trang ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ghi_chu_xu_ly))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__ket_qua_dung_trang_thai ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__ket_qua_dung_trang_thai ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((((ky_hieu_hoa_don = ''''::text) AND (ly_do_tu_choi = ''''::text) AND (so_hoa_don = ''''::text) AND (trang_thai = ''cho_xu_ly''::text)) OR ((ly_do_tu_choi = ''''::text) AND (trang_thai = ''da_xuat''::text) AND (((ky_hieu_hoa_don = ''''::text) AND (so_hoa_don = ''''::text)) OR ((NOT (ky_hieu_hoa_don = ''''::text)) AND (NOT (so_hoa_don = ''''::text))))) OR ((ky_hieu_hoa_don = ''''::text) AND (so_hoa_don = ''''::text) AND (trang_thai = ''tu_choi''::text) AND (NOT (ly_do_tu_choi = ''''::text)))))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__ky_hieu_hoa_don_da_cat_khoang_trang ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__ky_hieu_hoa_don_da_cat_khoang_trang ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ky_hieu_hoa_don))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__ky_hieu_hoa_don_dung_dinh_dang ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__ky_hieu_hoa_don_dung_dinh_dang ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ky_hieu_hoa_don ~ ''^([1-9][CK][0-9]{2}[A-Z]{3})?$''::text))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__ky_hieu_hoa_don_mot_dong ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__ky_hieu_hoa_don_mot_dong ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ky_hieu_hoa_don))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__ly_do_tu_choi_da_cat_khoang_trang ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__ly_do_tu_choi_da_cat_khoang_trang ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ly_do_tu_choi))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__ma_so_thue_da_cat_khoang_trang ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__ma_so_thue_da_cat_khoang_trang ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ma_so_thue))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__ma_so_thue_dung_dinh_dang ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__ma_so_thue_dung_dinh_dang ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((ma_so_thue ~ ''^[0-9]{10}(-[0-9]{3})?$''::text))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__ma_so_thue_khong_rong ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__ma_so_thue_khong_rong ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ma_so_thue))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__ma_so_thue_mot_dong ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__ma_so_thue_mot_dong ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ma_so_thue))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__so_hoa_don_da_cat_khoang_trang ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__so_hoa_don_da_cat_khoang_trang ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(so_hoa_don))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__so_hoa_don_dung_dinh_dang ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__so_hoa_don_dung_dinh_dang ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((so_hoa_don ~ ''^([0-9]{1,8})?$''::text))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__so_hoa_don_mot_dong ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__so_hoa_don_mot_dong ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(so_hoa_don))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__ten_cong_ty_da_cat_khoang_trang ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__ten_cong_ty_da_cat_khoang_trang ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (da_cat_khoang_trang(ten_cong_ty))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__ten_cong_ty_khong_rong ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__ten_cong_ty_khong_rong ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (khong_rong(ten_cong_ty))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__ten_cong_ty_mot_dong ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__ten_cong_ty_mot_dong ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK (la_mot_dong(ten_cong_ty))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__trang_thai_hop_le ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__trang_thai_hop_le ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((trang_thai = ANY (ARRAY[''cho_xu_ly''::text, ''da_xuat''::text, ''tu_choi''::text])))';


--
-- Name: CONSTRAINT kiem_tra__xuat_hoa_don__xu_ly_dung_trang_thai ON yeu_cau_xuat_hoa_don; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT kiem_tra__xuat_hoa_don__xu_ly_dung_trang_thai ON public.yeu_cau_xuat_hoa_don IS 'Lớp bảo vệ cuối của CSDL, từ chối dữ liệu vi phạm: CHECK ((((id_tai_khoan_xu_ly IS NULL) AND (thoi_diem_xu_ly IS NULL) AND (trang_thai = ''cho_xu_ly''::text)) OR ((NOT (trang_thai = ''cho_xu_ly''::text)) AND (id_tai_khoan_xu_ly IS NOT NULL) AND (thoi_diem_xu_ly IS NOT NULL) AND (NOT (ghi_chu_xu_ly = ''''::text)))))';


--
-- Name: yeu_cau_xuat_hoa_don_id_yeu_cau_xuat_hoa_don_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.yeu_cau_xuat_hoa_don ALTER COLUMN id_yeu_cau_xuat_hoa_don ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.yeu_cau_xuat_hoa_don_id_yeu_cau_xuat_hoa_don_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- Name: auth_group_permissions auth_group_permissions_group_id_permission_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);


--
-- Name: auth_group_permissions auth_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- Name: auth_permission auth_permission_content_type_id_codename_01ab375a_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);


--
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- Name: django_content_type django_content_type_app_label_model_76bd3d3b_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);


--
-- Name: django_content_type django_content_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);


--
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- Name: django_session django_session_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);


--
-- Name: anh_tin_nhan duy_nhat__anh_tin_nhan__id_tin_nhan__thu_tu; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anh_tin_nhan
    ADD CONSTRAINT duy_nhat__anh_tin_nhan__id_tin_nhan__thu_tu UNIQUE (id_tin_nhan, thu_tu);


--
-- Name: chi_nhanh duy_nhat__chi_nhanh__ma_chi_nhanh; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_nhanh
    ADD CONSTRAINT duy_nhat__chi_nhanh__ma_chi_nhanh UNIQUE (ma_chi_nhanh);


--
-- Name: chi_tiet_don_hang duy_nhat__ct_don_hang__id_don_hang__id_thuoc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_don_hang
    ADD CONSTRAINT duy_nhat__ct_don_hang__id_don_hang__id_thuoc UNIQUE (id_don_hang, id_thuoc);


--
-- Name: chi_tiet_phieu_kiem_ke duy_nhat__ct_kiem_ke__id_phieu_kiem_ke__id_lo_thuoc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_phieu_kiem_ke
    ADD CONSTRAINT duy_nhat__ct_kiem_ke__id_phieu_kiem_ke__id_lo_thuoc UNIQUE (id_phieu_kiem_ke, id_lo_thuoc);


--
-- Name: danh_gia_chi_nhanh duy_nhat__danh_gia_chi_nhanh__id_chi_nhanh__id_tai_khoan_khach; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.danh_gia_chi_nhanh
    ADD CONSTRAINT duy_nhat__danh_gia_chi_nhanh__id_chi_nhanh__id_tai_khoan_khach UNIQUE (id_chi_nhanh, id_tai_khoan_khach);


--
-- Name: danh_gia_thuoc duy_nhat__danh_gia_thuoc__id_thuoc__id_tai_khoan_khach; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.danh_gia_thuoc
    ADD CONSTRAINT duy_nhat__danh_gia_thuoc__id_thuoc__id_tai_khoan_khach UNIQUE (id_thuoc, id_tai_khoan_khach);


--
-- Name: danh_muc_san_pham duy_nhat__danh_muc_san_pham__ma_danh_muc_san_pham; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.danh_muc_san_pham
    ADD CONSTRAINT duy_nhat__danh_muc_san_pham__ma_danh_muc_san_pham UNIQUE (ma_danh_muc_san_pham);


--
-- Name: don_hang duy_nhat__don_hang__ma_don_hang; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.don_hang
    ADD CONSTRAINT duy_nhat__don_hang__ma_don_hang UNIQUE (ma_don_hang);


--
-- Name: don_vi_tinh duy_nhat__don_vi_tinh__ma_don_vi_tinh; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.don_vi_tinh
    ADD CONSTRAINT duy_nhat__don_vi_tinh__ma_don_vi_tinh UNIQUE (ma_don_vi_tinh);


--
-- Name: du_bao_bay_ngay duy_nhat__du_bao__id_ket_qua_mo_hinh__ngay_goc__ky_danh_gia; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.du_bao_bay_ngay
    ADD CONSTRAINT duy_nhat__du_bao__id_ket_qua_mo_hinh__ngay_goc__ky_danh_gia UNIQUE (id_ket_qua_mo_hinh, ngay_goc, ky_danh_gia);


--
-- Name: ket_qua_mo_hinh duy_nhat__ket_qua__id_lan_thuc_nghiem__ma_atc_nguon__mo_hinh; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ket_qua_mo_hinh
    ADD CONSTRAINT duy_nhat__ket_qua__id_lan_thuc_nghiem__ma_atc_nguon__mo_hinh UNIQUE (id_lan_thuc_nghiem, ma_atc_nguon, mo_hinh);


--
-- Name: khuyen_mai duy_nhat__khuyen_mai__ma_khuyen_mai; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.khuyen_mai
    ADD CONSTRAINT duy_nhat__khuyen_mai__ma_khuyen_mai UNIQUE (ma_khuyen_mai);


--
-- Name: lo_thuoc duy_nhat__lo_thuoc__id_thuoc__ma_lo_thuoc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lo_thuoc
    ADD CONSTRAINT duy_nhat__lo_thuoc__id_thuoc__ma_lo_thuoc UNIQUE (id_thuoc, ma_lo_thuoc);


--
-- Name: nguon_du_lieu duy_nhat__nguon_du_lieu__bam_sha256; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nguon_du_lieu
    ADD CONSTRAINT duy_nhat__nguon_du_lieu__bam_sha256 UNIQUE (bam_sha256);


--
-- Name: nha_cung_cap duy_nhat__nha_cung_cap__ma_nha_cung_cap; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nha_cung_cap
    ADD CONSTRAINT duy_nhat__nha_cung_cap__ma_nha_cung_cap UNIQUE (ma_nha_cung_cap);


--
-- Name: nhan_vien duy_nhat__nhan_vien__id_tai_khoan; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nhan_vien
    ADD CONSTRAINT duy_nhat__nhan_vien__id_tai_khoan UNIQUE (id_tai_khoan);


--
-- Name: nhan_vien duy_nhat__nhan_vien__ma_nhan_vien; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nhan_vien
    ADD CONSTRAINT duy_nhat__nhan_vien__ma_nhan_vien UNIQUE (ma_nhan_vien);


--
-- Name: nhom_atc duy_nhat__nhom_atc__ma_nhom_atc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nhom_atc
    ADD CONSTRAINT duy_nhat__nhom_atc__ma_nhom_atc UNIQUE (ma_nhom_atc);


--
-- Name: nhom_quyen duy_nhat__nhom_quyen__ma_nhom_quyen; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nhom_quyen
    ADD CONSTRAINT duy_nhat__nhom_quyen__ma_nhom_quyen UNIQUE (ma_nhom_quyen);


--
-- Name: nhom_quyen duy_nhat__nhom_quyen__vai_tro_mac_dinh; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nhom_quyen
    ADD CONSTRAINT duy_nhat__nhom_quyen__vai_tro_mac_dinh UNIQUE (vai_tro_mac_dinh);


--
-- Name: phan_bo_phieu_ban duy_nhat__pb_ban__id_chi_tiet_phieu_ban__id_ton_kho; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phan_bo_phieu_ban
    ADD CONSTRAINT duy_nhat__pb_ban__id_chi_tiet_phieu_ban__id_ton_kho UNIQUE (id_chi_tiet_phieu_ban, id_ton_kho);


--
-- Name: phan_bo_don_hang duy_nhat__pb_don_hang__id_chi_tiet_don_hang__id_ton_kho; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phan_bo_don_hang
    ADD CONSTRAINT duy_nhat__pb_don_hang__id_chi_tiet_don_hang__id_ton_kho UNIQUE (id_chi_tiet_don_hang, id_ton_kho);


--
-- Name: phieu_ban duy_nhat__phieu_ban__id_don_hang; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_ban
    ADD CONSTRAINT duy_nhat__phieu_ban__id_don_hang UNIQUE (id_don_hang);


--
-- Name: phieu_ban duy_nhat__phieu_ban__khoa_yeu_cau; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_ban
    ADD CONSTRAINT duy_nhat__phieu_ban__khoa_yeu_cau UNIQUE (khoa_yeu_cau);


--
-- Name: phieu_ban duy_nhat__phieu_ban__ma_phieu_ban; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_ban
    ADD CONSTRAINT duy_nhat__phieu_ban__ma_phieu_ban UNIQUE (ma_phieu_ban);


--
-- Name: phieu_dieu_chuyen duy_nhat__phieu_dieu_chuyen__khoa_yeu_cau; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_dieu_chuyen
    ADD CONSTRAINT duy_nhat__phieu_dieu_chuyen__khoa_yeu_cau UNIQUE (khoa_yeu_cau);


--
-- Name: phieu_dieu_chuyen duy_nhat__phieu_dieu_chuyen__ma_phieu_dieu_chuyen; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_dieu_chuyen
    ADD CONSTRAINT duy_nhat__phieu_dieu_chuyen__ma_phieu_dieu_chuyen UNIQUE (ma_phieu_dieu_chuyen);


--
-- Name: phieu_kiem_ke duy_nhat__phieu_kiem_ke__khoa_yeu_cau; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_kiem_ke
    ADD CONSTRAINT duy_nhat__phieu_kiem_ke__khoa_yeu_cau UNIQUE (khoa_yeu_cau);


--
-- Name: phieu_kiem_ke duy_nhat__phieu_kiem_ke__ma_phieu_kiem_ke; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_kiem_ke
    ADD CONSTRAINT duy_nhat__phieu_kiem_ke__ma_phieu_kiem_ke UNIQUE (ma_phieu_kiem_ke);


--
-- Name: phieu_nhap duy_nhat__phieu_nhap__khoa_yeu_cau; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_nhap
    ADD CONSTRAINT duy_nhat__phieu_nhap__khoa_yeu_cau UNIQUE (khoa_yeu_cau);


--
-- Name: phieu_nhap duy_nhat__phieu_nhap__ma_phieu_nhap; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_nhap
    ADD CONSTRAINT duy_nhat__phieu_nhap__ma_phieu_nhap UNIQUE (ma_phieu_nhap);


--
-- Name: phieu_xuat_huy duy_nhat__phieu_xuat_huy__khoa_yeu_cau; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_xuat_huy
    ADD CONSTRAINT duy_nhat__phieu_xuat_huy__khoa_yeu_cau UNIQUE (khoa_yeu_cau);


--
-- Name: phieu_xuat_huy duy_nhat__phieu_xuat_huy__ma_phieu_xuat_huy; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_xuat_huy
    ADD CONSTRAINT duy_nhat__phieu_xuat_huy__ma_phieu_xuat_huy UNIQUE (ma_phieu_xuat_huy);


--
-- Name: cuoc_tro_chuyen duy_nhat__phong__id_tai_khoan_khach__id_chi_nhanh; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cuoc_tro_chuyen
    ADD CONSTRAINT duy_nhat__phong__id_tai_khoan_khach__id_chi_nhanh UNIQUE (id_tai_khoan_khach, id_chi_nhanh);


--
-- Name: quan_sat_ban_hang duy_nhat__quan_sat__id_nguon_du_lieu__ma_atc_nguon__ngay_ban; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quan_sat_ban_hang
    ADD CONSTRAINT duy_nhat__quan_sat__id_nguon_du_lieu__ma_atc_nguon__ngay_ban UNIQUE (id_nguon_du_lieu, ma_atc_nguon, ngay_ban);


--
-- Name: quy_doi_bao_goi duy_nhat__quy_doi_bao_goi__id_thuoc__ten_quy_doi_bao_goi; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quy_doi_bao_goi
    ADD CONSTRAINT duy_nhat__quy_doi_bao_goi__id_thuoc__ten_quy_doi_bao_goi UNIQUE (id_thuoc, ten_quy_doi_bao_goi);


--
-- Name: quyen_cua_nhom duy_nhat__quyen_cua_nhom__id_nhom_quyen__ma_quyen; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quyen_cua_nhom
    ADD CONSTRAINT duy_nhat__quyen_cua_nhom__id_nhom_quyen__ma_quyen UNIQUE (id_nhom_quyen, ma_quyen);


--
-- Name: quyen_rieng_tai_khoan duy_nhat__quyen_rieng_tai_khoan__id_tai_khoan__ma_quyen; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quyen_rieng_tai_khoan
    ADD CONSTRAINT duy_nhat__quyen_rieng_tai_khoan__id_tai_khoan__ma_quyen UNIQUE (id_tai_khoan, ma_quyen);


--
-- Name: tai_khoan duy_nhat__tai_khoan__email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tai_khoan
    ADD CONSTRAINT duy_nhat__tai_khoan__email UNIQUE (email);


--
-- Name: tai_khoan duy_nhat__tai_khoan__ten_dang_nhap; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tai_khoan
    ADD CONSTRAINT duy_nhat__tai_khoan__ten_dang_nhap UNIQUE (ten_dang_nhap);


--
-- Name: thuoc duy_nhat__thuoc__ma_thuoc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.thuoc
    ADD CONSTRAINT duy_nhat__thuoc__ma_thuoc UNIQUE (ma_thuoc);


--
-- Name: tin_nhan duy_nhat__tin_nhan__id_tai_khoan_gui__ma_tin_nhan; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tin_nhan
    ADD CONSTRAINT duy_nhat__tin_nhan__id_tai_khoan_gui__ma_tin_nhan UNIQUE (id_tai_khoan_gui, ma_tin_nhan);


--
-- Name: tin_tuc duy_nhat__tin_tuc__duong_dan_tin_tuc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tin_tuc
    ADD CONSTRAINT duy_nhat__tin_tuc__duong_dan_tin_tuc UNIQUE (duong_dan_tin_tuc);


--
-- Name: ton_kho duy_nhat__ton_kho__id_chi_nhanh__id_lo_thuoc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ton_kho
    ADD CONSTRAINT duy_nhat__ton_kho__id_chi_nhanh__id_lo_thuoc UNIQUE (id_chi_nhanh, id_lo_thuoc);


--
-- Name: phieu_tra_nha_cung_cap duy_nhat__tra_ncc__khoa_yeu_cau; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_tra_nha_cung_cap
    ADD CONSTRAINT duy_nhat__tra_ncc__khoa_yeu_cau UNIQUE (khoa_yeu_cau);


--
-- Name: phieu_tra_nha_cung_cap duy_nhat__tra_ncc__ma_phieu_tra_nha_cung_cap; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_tra_nha_cung_cap
    ADD CONSTRAINT duy_nhat__tra_ncc__ma_phieu_tra_nha_cung_cap UNIQUE (ma_phieu_tra_nha_cung_cap);


--
-- Name: trang_noi_dung duy_nhat__trang__duong_dan_trang; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trang_noi_dung
    ADD CONSTRAINT duy_nhat__trang__duong_dan_trang UNIQUE (duong_dan_trang);


--
-- Name: phien_xac_thuc duy_nhat__xac_thuc__ma_phien_xac_thuc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phien_xac_thuc
    ADD CONSTRAINT duy_nhat__xac_thuc__ma_phien_xac_thuc UNIQUE (ma_phien_xac_thuc);


--
-- Name: yeu_cau_xuat_hoa_don duy_nhat__xuat_hoa_don__id_don_hang; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.yeu_cau_xuat_hoa_don
    ADD CONSTRAINT duy_nhat__xuat_hoa_don__id_don_hang UNIQUE (id_don_hang);


--
-- Name: anh_chi_nhanh khoa_chinh__anh_chi_nhanh; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anh_chi_nhanh
    ADD CONSTRAINT khoa_chinh__anh_chi_nhanh PRIMARY KEY (id_anh_chi_nhanh);


--
-- Name: anh_noi_dung khoa_chinh__anh_noi_dung; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anh_noi_dung
    ADD CONSTRAINT khoa_chinh__anh_noi_dung PRIMARY KEY (id_anh_noi_dung);


--
-- Name: anh_thuoc khoa_chinh__anh_thuoc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anh_thuoc
    ADD CONSTRAINT khoa_chinh__anh_thuoc PRIMARY KEY (id_anh_thuoc);


--
-- Name: anh_tin_nhan khoa_chinh__anh_tin_nhan; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anh_tin_nhan
    ADD CONSTRAINT khoa_chinh__anh_tin_nhan PRIMARY KEY (id_anh_tin_nhan);


--
-- Name: banner_trang_chu khoa_chinh__banner; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.banner_trang_chu
    ADD CONSTRAINT khoa_chinh__banner PRIMARY KEY (id_banner_trang_chu);


--
-- Name: chi_nhanh khoa_chinh__chi_nhanh; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_nhanh
    ADD CONSTRAINT khoa_chinh__chi_nhanh PRIMARY KEY (id_chi_nhanh);


--
-- Name: chi_tiet_phieu_xuat_huy khoa_chinh__chi_tiet_phieu_xuat_huy; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_phieu_xuat_huy
    ADD CONSTRAINT khoa_chinh__chi_tiet_phieu_xuat_huy PRIMARY KEY (id_chi_tiet_phieu_xuat_huy);


--
-- Name: chi_tiet_phieu_ban khoa_chinh__ct_ban; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_phieu_ban
    ADD CONSTRAINT khoa_chinh__ct_ban PRIMARY KEY (id_chi_tiet_phieu_ban);


--
-- Name: chi_tiet_phieu_dieu_chuyen khoa_chinh__ct_dieu_chuyen; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_phieu_dieu_chuyen
    ADD CONSTRAINT khoa_chinh__ct_dieu_chuyen PRIMARY KEY (id_chi_tiet_phieu_dieu_chuyen);


--
-- Name: chi_tiet_don_hang khoa_chinh__ct_don_hang; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_don_hang
    ADD CONSTRAINT khoa_chinh__ct_don_hang PRIMARY KEY (id_chi_tiet_don_hang);


--
-- Name: chi_tiet_phieu_kiem_ke khoa_chinh__ct_kiem_ke; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_phieu_kiem_ke
    ADD CONSTRAINT khoa_chinh__ct_kiem_ke PRIMARY KEY (id_chi_tiet_phieu_kiem_ke);


--
-- Name: chi_tiet_phieu_nhap khoa_chinh__ct_nhap; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_phieu_nhap
    ADD CONSTRAINT khoa_chinh__ct_nhap PRIMARY KEY (id_chi_tiet_phieu_nhap);


--
-- Name: chi_tiet_phieu_tra_nha_cung_cap khoa_chinh__ct_tra_ncc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_phieu_tra_nha_cung_cap
    ADD CONSTRAINT khoa_chinh__ct_tra_ncc PRIMARY KEY (id_chi_tiet_phieu_tra_nha_cung_cap);


--
-- Name: thong_tin_cua_hang khoa_chinh__cua_hang; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.thong_tin_cua_hang
    ADD CONSTRAINT khoa_chinh__cua_hang PRIMARY KEY (id_thong_tin_cua_hang);


--
-- Name: danh_gia_chi_nhanh khoa_chinh__danh_gia_chi_nhanh; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.danh_gia_chi_nhanh
    ADD CONSTRAINT khoa_chinh__danh_gia_chi_nhanh PRIMARY KEY (id_danh_gia_chi_nhanh);


--
-- Name: danh_gia_thuoc khoa_chinh__danh_gia_thuoc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.danh_gia_thuoc
    ADD CONSTRAINT khoa_chinh__danh_gia_thuoc PRIMARY KEY (id_danh_gia_thuoc);


--
-- Name: danh_muc_san_pham khoa_chinh__danh_muc_san_pham; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.danh_muc_san_pham
    ADD CONSTRAINT khoa_chinh__danh_muc_san_pham PRIMARY KEY (id_danh_muc_san_pham);


--
-- Name: don_hang khoa_chinh__don_hang; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.don_hang
    ADD CONSTRAINT khoa_chinh__don_hang PRIMARY KEY (id_don_hang);


--
-- Name: don_vi_tinh khoa_chinh__don_vi_tinh; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.don_vi_tinh
    ADD CONSTRAINT khoa_chinh__don_vi_tinh PRIMARY KEY (id_don_vi_tinh);


--
-- Name: du_bao_bay_ngay khoa_chinh__du_bao; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.du_bao_bay_ngay
    ADD CONSTRAINT khoa_chinh__du_bao PRIMARY KEY (id_du_bao_bay_ngay);


--
-- Name: ket_qua_mo_hinh khoa_chinh__ket_qua; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ket_qua_mo_hinh
    ADD CONSTRAINT khoa_chinh__ket_qua PRIMARY KEY (id_ket_qua_mo_hinh);


--
-- Name: khuyen_mai khoa_chinh__khuyen_mai; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.khuyen_mai
    ADD CONSTRAINT khoa_chinh__khuyen_mai PRIMARY KEY (id_khuyen_mai);


--
-- Name: kich_ban_thieu_hang khoa_chinh__kich_ban_thieu_hang; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kich_ban_thieu_hang
    ADD CONSTRAINT khoa_chinh__kich_ban_thieu_hang PRIMARY KEY (id_kich_ban_thieu_hang);


--
-- Name: lan_thuc_nghiem khoa_chinh__lan_thuc_nghiem; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lan_thuc_nghiem
    ADD CONSTRAINT khoa_chinh__lan_thuc_nghiem PRIMARY KEY (id_lan_thuc_nghiem);


--
-- Name: lich_su_dieu_kien_lo khoa_chinh__lich_su_dieu_kien_lo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lich_su_dieu_kien_lo
    ADD CONSTRAINT khoa_chinh__lich_su_dieu_kien_lo PRIMARY KEY (id_lich_su_dieu_kien_lo);


--
-- Name: lich_su_don_hang khoa_chinh__lich_su_don_hang; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lich_su_don_hang
    ADD CONSTRAINT khoa_chinh__lich_su_don_hang PRIMARY KEY (id_lich_su_don_hang);


--
-- Name: lo_thuoc khoa_chinh__lo_thuoc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lo_thuoc
    ADD CONSTRAINT khoa_chinh__lo_thuoc PRIMARY KEY (id_lo_thuoc);


--
-- Name: nguon_du_lieu khoa_chinh__nguon_du_lieu; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nguon_du_lieu
    ADD CONSTRAINT khoa_chinh__nguon_du_lieu PRIMARY KEY (id_nguon_du_lieu);


--
-- Name: nha_cung_cap khoa_chinh__nha_cung_cap; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nha_cung_cap
    ADD CONSTRAINT khoa_chinh__nha_cung_cap PRIMARY KEY (id_nha_cung_cap);


--
-- Name: nhan_vien khoa_chinh__nhan_vien; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nhan_vien
    ADD CONSTRAINT khoa_chinh__nhan_vien PRIMARY KEY (id_nhan_vien);


--
-- Name: nhat_ky_email khoa_chinh__nhat_ky_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nhat_ky_email
    ADD CONSTRAINT khoa_chinh__nhat_ky_email PRIMARY KEY (id_nhat_ky_email);


--
-- Name: nhom_atc khoa_chinh__nhom_atc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nhom_atc
    ADD CONSTRAINT khoa_chinh__nhom_atc PRIMARY KEY (id_nhom_atc);


--
-- Name: nhom_quyen khoa_chinh__nhom_quyen; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nhom_quyen
    ADD CONSTRAINT khoa_chinh__nhom_quyen PRIMARY KEY (id_nhom_quyen);


--
-- Name: phan_bo_phieu_ban khoa_chinh__pb_ban; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phan_bo_phieu_ban
    ADD CONSTRAINT khoa_chinh__pb_ban PRIMARY KEY (id_phan_bo_phieu_ban);


--
-- Name: phan_bo_don_hang khoa_chinh__pb_don_hang; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phan_bo_don_hang
    ADD CONSTRAINT khoa_chinh__pb_don_hang PRIMARY KEY (id_phan_bo_don_hang);


--
-- Name: phieu_ban khoa_chinh__phieu_ban; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_ban
    ADD CONSTRAINT khoa_chinh__phieu_ban PRIMARY KEY (id_phieu_ban);


--
-- Name: phieu_dieu_chuyen khoa_chinh__phieu_dieu_chuyen; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_dieu_chuyen
    ADD CONSTRAINT khoa_chinh__phieu_dieu_chuyen PRIMARY KEY (id_phieu_dieu_chuyen);


--
-- Name: phieu_kiem_ke khoa_chinh__phieu_kiem_ke; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_kiem_ke
    ADD CONSTRAINT khoa_chinh__phieu_kiem_ke PRIMARY KEY (id_phieu_kiem_ke);


--
-- Name: phieu_nhap khoa_chinh__phieu_nhap; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_nhap
    ADD CONSTRAINT khoa_chinh__phieu_nhap PRIMARY KEY (id_phieu_nhap);


--
-- Name: phieu_xuat_huy khoa_chinh__phieu_xuat_huy; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_xuat_huy
    ADD CONSTRAINT khoa_chinh__phieu_xuat_huy PRIMARY KEY (id_phieu_xuat_huy);


--
-- Name: cuoc_tro_chuyen khoa_chinh__phong; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cuoc_tro_chuyen
    ADD CONSTRAINT khoa_chinh__phong PRIMARY KEY (id_cuoc_tro_chuyen);


--
-- Name: quan_sat_ban_hang khoa_chinh__quan_sat; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quan_sat_ban_hang
    ADD CONSTRAINT khoa_chinh__quan_sat PRIMARY KEY (id_quan_sat_ban_hang);


--
-- Name: quy_doi_bao_goi khoa_chinh__quy_doi_bao_goi; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quy_doi_bao_goi
    ADD CONSTRAINT khoa_chinh__quy_doi_bao_goi PRIMARY KEY (id_quy_doi_bao_goi);


--
-- Name: quyen_cua_nhom khoa_chinh__quyen_cua_nhom; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quyen_cua_nhom
    ADD CONSTRAINT khoa_chinh__quyen_cua_nhom PRIMARY KEY (id_quyen_cua_nhom);


--
-- Name: quyen_rieng_tai_khoan khoa_chinh__quyen_rieng_tai_khoan; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quyen_rieng_tai_khoan
    ADD CONSTRAINT khoa_chinh__quyen_rieng_tai_khoan PRIMARY KEY (id_quyen_rieng_tai_khoan);


--
-- Name: tai_khoan khoa_chinh__tai_khoan; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tai_khoan
    ADD CONSTRAINT khoa_chinh__tai_khoan PRIMARY KEY (id_tai_khoan);


--
-- Name: thuoc khoa_chinh__thuoc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.thuoc
    ADD CONSTRAINT khoa_chinh__thuoc PRIMARY KEY (id_thuoc);


--
-- Name: tin_nhan khoa_chinh__tin_nhan; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tin_nhan
    ADD CONSTRAINT khoa_chinh__tin_nhan PRIMARY KEY (id_tin_nhan);


--
-- Name: tin_tuc khoa_chinh__tin_tuc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tin_tuc
    ADD CONSTRAINT khoa_chinh__tin_tuc PRIMARY KEY (id_tin_tuc);


--
-- Name: ton_kho khoa_chinh__ton_kho; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ton_kho
    ADD CONSTRAINT khoa_chinh__ton_kho PRIMARY KEY (id_ton_kho);


--
-- Name: phieu_tra_nha_cung_cap khoa_chinh__tra_ncc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_tra_nha_cung_cap
    ADD CONSTRAINT khoa_chinh__tra_ncc PRIMARY KEY (id_phieu_tra_nha_cung_cap);


--
-- Name: trang_noi_dung khoa_chinh__trang; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trang_noi_dung
    ADD CONSTRAINT khoa_chinh__trang PRIMARY KEY (id_trang_noi_dung);


--
-- Name: phien_xac_thuc khoa_chinh__xac_thuc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phien_xac_thuc
    ADD CONSTRAINT khoa_chinh__xac_thuc PRIMARY KEY (id_phien_xac_thuc);


--
-- Name: yeu_cau_xuat_hoa_don khoa_chinh__xuat_hoa_don; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.yeu_cau_xuat_hoa_don
    ADD CONSTRAINT khoa_chinh__xuat_hoa_don PRIMARY KEY (id_yeu_cau_xuat_hoa_don);


--
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);


--
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);


--
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);


--
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);


--
-- Name: chi_muc__anh_chi_nhanh__id_chi_nhanh__thu_tu; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__anh_chi_nhanh__id_chi_nhanh__thu_tu ON public.anh_chi_nhanh USING btree (id_chi_nhanh, thu_tu);


--
-- Name: chi_muc__anh_noi_dung__id_tai_khoan; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__anh_noi_dung__id_tai_khoan ON public.anh_noi_dung USING btree (id_tai_khoan);


--
-- Name: chi_muc__anh_thuoc__id_thuoc__thu_tu; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__anh_thuoc__id_thuoc__thu_tu ON public.anh_thuoc USING btree (id_thuoc, thu_tu);


--
-- Name: chi_muc__chi_nhanh__vi_tri; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__chi_nhanh__vi_tri ON public.chi_nhanh USING gist (vi_tri);


--
-- Name: chi_muc__chi_tiet_phieu_xuat_huy__id_lo_thuoc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__chi_tiet_phieu_xuat_huy__id_lo_thuoc ON public.chi_tiet_phieu_xuat_huy USING btree (id_lo_thuoc);


--
-- Name: chi_muc__chi_tiet_phieu_xuat_huy__id_phieu_xuat_huy; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__chi_tiet_phieu_xuat_huy__id_phieu_xuat_huy ON public.chi_tiet_phieu_xuat_huy USING btree (id_phieu_xuat_huy);


--
-- Name: chi_muc__ct_ban__id_phieu_ban; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__ct_ban__id_phieu_ban ON public.chi_tiet_phieu_ban USING btree (id_phieu_ban);


--
-- Name: chi_muc__ct_ban__id_thuoc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__ct_ban__id_thuoc ON public.chi_tiet_phieu_ban USING btree (id_thuoc);


--
-- Name: chi_muc__ct_dieu_chuyen__id_lo_thuoc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__ct_dieu_chuyen__id_lo_thuoc ON public.chi_tiet_phieu_dieu_chuyen USING btree (id_lo_thuoc);


--
-- Name: chi_muc__ct_dieu_chuyen__id_phieu_dieu_chuyen; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__ct_dieu_chuyen__id_phieu_dieu_chuyen ON public.chi_tiet_phieu_dieu_chuyen USING btree (id_phieu_dieu_chuyen);


--
-- Name: chi_muc__ct_don_hang__id_thuoc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__ct_don_hang__id_thuoc ON public.chi_tiet_don_hang USING btree (id_thuoc);


--
-- Name: chi_muc__ct_kiem_ke__id_lo_thuoc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__ct_kiem_ke__id_lo_thuoc ON public.chi_tiet_phieu_kiem_ke USING btree (id_lo_thuoc);


--
-- Name: chi_muc__ct_nhap__id_lo_thuoc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__ct_nhap__id_lo_thuoc ON public.chi_tiet_phieu_nhap USING btree (id_lo_thuoc);


--
-- Name: chi_muc__ct_nhap__id_phieu_nhap; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__ct_nhap__id_phieu_nhap ON public.chi_tiet_phieu_nhap USING btree (id_phieu_nhap);


--
-- Name: chi_muc__ct_tra_ncc__id_lo_thuoc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__ct_tra_ncc__id_lo_thuoc ON public.chi_tiet_phieu_tra_nha_cung_cap USING btree (id_lo_thuoc);


--
-- Name: chi_muc__ct_tra_ncc__id_phieu_tra_nha_cung_cap; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__ct_tra_ncc__id_phieu_tra_nha_cung_cap ON public.chi_tiet_phieu_tra_nha_cung_cap USING btree (id_phieu_tra_nha_cung_cap);


--
-- Name: chi_muc__danh_gia_chi_nhanh__id_tai_khoan_khach; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__danh_gia_chi_nhanh__id_tai_khoan_khach ON public.danh_gia_chi_nhanh USING btree (id_tai_khoan_khach);


--
-- Name: chi_muc__danh_gia_thuoc__id_tai_khoan_khach; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__danh_gia_thuoc__id_tai_khoan_khach ON public.danh_gia_thuoc USING btree (id_tai_khoan_khach);


--
-- Name: chi_muc__don_hang__id_chi_nhanh; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__don_hang__id_chi_nhanh ON public.don_hang USING btree (id_chi_nhanh);


--
-- Name: chi_muc__don_hang__id_tai_khoan_khach; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__don_hang__id_tai_khoan_khach ON public.don_hang USING btree (id_tai_khoan_khach);


--
-- Name: chi_muc__don_hang__trang_thai__thoi_diem_het_giu; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__don_hang__trang_thai__thoi_diem_het_giu ON public.don_hang USING btree (trang_thai, thoi_diem_het_giu);


--
-- Name: chi_muc__khuyen_mai__id_thuoc__ngay_bat_dau; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__khuyen_mai__id_thuoc__ngay_bat_dau ON public.khuyen_mai USING btree (id_thuoc, ngay_bat_dau);


--
-- Name: chi_muc__kich_ban_thieu_hang__id_du_bao_bay_ngay; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__kich_ban_thieu_hang__id_du_bao_bay_ngay ON public.kich_ban_thieu_hang USING btree (id_du_bao_bay_ngay);


--
-- Name: chi_muc__lan_thuc_nghiem__id_nguon_du_lieu; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__lan_thuc_nghiem__id_nguon_du_lieu ON public.lan_thuc_nghiem USING btree (id_nguon_du_lieu);


--
-- Name: chi_muc__lich_su_dieu_kien_lo__id_lo_thuoc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__lich_su_dieu_kien_lo__id_lo_thuoc ON public.lich_su_dieu_kien_lo USING btree (id_lo_thuoc);


--
-- Name: chi_muc__lich_su_dieu_kien_lo__id_tai_khoan_thuc_hien; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__lich_su_dieu_kien_lo__id_tai_khoan_thuc_hien ON public.lich_su_dieu_kien_lo USING btree (id_tai_khoan_thuc_hien);


--
-- Name: chi_muc__lich_su_don_hang__id_don_hang__thoi_diem_tao; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__lich_su_don_hang__id_don_hang__thoi_diem_tao ON public.lich_su_don_hang USING btree (id_don_hang, thoi_diem_tao);


--
-- Name: chi_muc__lich_su_don_hang__id_tai_khoan_thuc_hien; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__lich_su_don_hang__id_tai_khoan_thuc_hien ON public.lich_su_don_hang USING btree (id_tai_khoan_thuc_hien);


--
-- Name: chi_muc__nhat_ky_email__id_don_hang; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__nhat_ky_email__id_don_hang ON public.nhat_ky_email USING btree (id_don_hang);


--
-- Name: chi_muc__nhat_ky_email__id_tai_khoan; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__nhat_ky_email__id_tai_khoan ON public.nhat_ky_email USING btree (id_tai_khoan);


--
-- Name: chi_muc__nhat_ky_email__thoi_diem_tao; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__nhat_ky_email__thoi_diem_tao ON public.nhat_ky_email USING btree (thoi_diem_tao);


--
-- Name: chi_muc__nhat_ky_email__trang_thai__thoi_diem_tao; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__nhat_ky_email__trang_thai__thoi_diem_tao ON public.nhat_ky_email USING btree (trang_thai, thoi_diem_tao);


--
-- Name: chi_muc__pb_ban__id_ton_kho; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__pb_ban__id_ton_kho ON public.phan_bo_phieu_ban USING btree (id_ton_kho);


--
-- Name: chi_muc__pb_don_hang__id_ton_kho; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__pb_don_hang__id_ton_kho ON public.phan_bo_don_hang USING btree (id_ton_kho);


--
-- Name: chi_muc__phieu_ban__id_chi_nhanh; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__phieu_ban__id_chi_nhanh ON public.phieu_ban USING btree (id_chi_nhanh);


--
-- Name: chi_muc__phieu_ban__id_tai_khoan_lap; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__phieu_ban__id_tai_khoan_lap ON public.phieu_ban USING btree (id_tai_khoan_lap);


--
-- Name: chi_muc__phieu_dieu_chuyen__id_chi_nhanh_dich; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__phieu_dieu_chuyen__id_chi_nhanh_dich ON public.phieu_dieu_chuyen USING btree (id_chi_nhanh_dich);


--
-- Name: chi_muc__phieu_dieu_chuyen__id_chi_nhanh_nguon; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__phieu_dieu_chuyen__id_chi_nhanh_nguon ON public.phieu_dieu_chuyen USING btree (id_chi_nhanh_nguon);


--
-- Name: chi_muc__phieu_dieu_chuyen__id_tai_khoan_lap; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__phieu_dieu_chuyen__id_tai_khoan_lap ON public.phieu_dieu_chuyen USING btree (id_tai_khoan_lap);


--
-- Name: chi_muc__phieu_kiem_ke__id_chi_nhanh; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__phieu_kiem_ke__id_chi_nhanh ON public.phieu_kiem_ke USING btree (id_chi_nhanh);


--
-- Name: chi_muc__phieu_kiem_ke__id_tai_khoan_lap; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__phieu_kiem_ke__id_tai_khoan_lap ON public.phieu_kiem_ke USING btree (id_tai_khoan_lap);


--
-- Name: chi_muc__phieu_nhap__id_chi_nhanh; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__phieu_nhap__id_chi_nhanh ON public.phieu_nhap USING btree (id_chi_nhanh);


--
-- Name: chi_muc__phieu_nhap__id_nha_cung_cap; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__phieu_nhap__id_nha_cung_cap ON public.phieu_nhap USING btree (id_nha_cung_cap);


--
-- Name: chi_muc__phieu_nhap__id_tai_khoan_lap; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__phieu_nhap__id_tai_khoan_lap ON public.phieu_nhap USING btree (id_tai_khoan_lap);


--
-- Name: chi_muc__phieu_xuat_huy__id_chi_nhanh; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__phieu_xuat_huy__id_chi_nhanh ON public.phieu_xuat_huy USING btree (id_chi_nhanh);


--
-- Name: chi_muc__phieu_xuat_huy__id_tai_khoan_lap; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__phieu_xuat_huy__id_tai_khoan_lap ON public.phieu_xuat_huy USING btree (id_tai_khoan_lap);


--
-- Name: chi_muc__phong__id_chi_nhanh__id_tin_nhan_cuoi; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__phong__id_chi_nhanh__id_tin_nhan_cuoi ON public.cuoc_tro_chuyen USING btree (id_chi_nhanh, id_tin_nhan_cuoi DESC);


--
-- Name: chi_muc__phong__id_tai_khoan_danh_dau_xong; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__phong__id_tai_khoan_danh_dau_xong ON public.cuoc_tro_chuyen USING btree (id_tai_khoan_danh_dau_xong);


--
-- Name: chi_muc__phong__id_tai_khoan_khach__id_tin_nhan_cuoi; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__phong__id_tai_khoan_khach__id_tin_nhan_cuoi ON public.cuoc_tro_chuyen USING btree (id_tai_khoan_khach, id_tin_nhan_cuoi DESC);


--
-- Name: chi_muc__phong__id_tin_nhan_cuoi; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__phong__id_tin_nhan_cuoi ON public.cuoc_tro_chuyen USING btree (id_tin_nhan_cuoi);


--
-- Name: chi_muc__phong__id_tin_nhan_khach_da_doc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__phong__id_tin_nhan_khach_da_doc ON public.cuoc_tro_chuyen USING btree (id_tin_nhan_khach_da_doc);


--
-- Name: chi_muc__phong__id_tin_nhan_nha_thuoc_da_doc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__phong__id_tin_nhan_nha_thuoc_da_doc ON public.cuoc_tro_chuyen USING btree (id_tin_nhan_nha_thuoc_da_doc);


--
-- Name: chi_muc__tai_khoan__id_chi_nhanh; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__tai_khoan__id_chi_nhanh ON public.tai_khoan USING btree (id_chi_nhanh);


--
-- Name: chi_muc__tai_khoan__id_nhom_quyen; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__tai_khoan__id_nhom_quyen ON public.tai_khoan USING btree (id_nhom_quyen);


--
-- Name: chi_muc__thuoc__id_danh_muc_san_pham; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__thuoc__id_danh_muc_san_pham ON public.thuoc USING btree (id_danh_muc_san_pham);


--
-- Name: chi_muc__thuoc__id_don_vi_tinh; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__thuoc__id_don_vi_tinh ON public.thuoc USING btree (id_don_vi_tinh);


--
-- Name: chi_muc__thuoc__id_nhom_atc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__thuoc__id_nhom_atc ON public.thuoc USING btree (id_nhom_atc);


--
-- Name: chi_muc__tin_nhan__id_cuoc_tro_chuyen__id_tin_nhan; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__tin_nhan__id_cuoc_tro_chuyen__id_tin_nhan ON public.tin_nhan USING btree (id_cuoc_tro_chuyen, id_tin_nhan DESC);


--
-- Name: chi_muc__tin_nhan__id_don_hang; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__tin_nhan__id_don_hang ON public.tin_nhan USING btree (id_don_hang);


--
-- Name: chi_muc__tin_nhan__id_thuoc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__tin_nhan__id_thuoc ON public.tin_nhan USING btree (id_thuoc);


--
-- Name: chi_muc__tin_tuc__id_tai_khoan_viet; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__tin_tuc__id_tai_khoan_viet ON public.tin_tuc USING btree (id_tai_khoan_viet);


--
-- Name: chi_muc__ton_kho__id_lo_thuoc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__ton_kho__id_lo_thuoc ON public.ton_kho USING btree (id_lo_thuoc);


--
-- Name: chi_muc__tra_ncc__id_phieu_nhap; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__tra_ncc__id_phieu_nhap ON public.phieu_tra_nha_cung_cap USING btree (id_phieu_nhap);


--
-- Name: chi_muc__tra_ncc__id_tai_khoan_lap; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__tra_ncc__id_tai_khoan_lap ON public.phieu_tra_nha_cung_cap USING btree (id_tai_khoan_lap);


--
-- Name: chi_muc__xac_thuc__dia_chi_ip__thoi_diem_tao; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__xac_thuc__dia_chi_ip__thoi_diem_tao ON public.phien_xac_thuc USING btree (dia_chi_ip, thoi_diem_tao);


--
-- Name: chi_muc__xac_thuc__email__thoi_diem_tao; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__xac_thuc__email__thoi_diem_tao ON public.phien_xac_thuc USING btree (email, thoi_diem_tao);


--
-- Name: chi_muc__xac_thuc__id_tai_khoan; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__xac_thuc__id_tai_khoan ON public.phien_xac_thuc USING btree (id_tai_khoan);


--
-- Name: chi_muc__xuat_hoa_don__id_tai_khoan_xu_ly; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chi_muc__xuat_hoa_don__id_tai_khoan_xu_ly ON public.yeu_cau_xuat_hoa_don USING btree (id_tai_khoan_xu_ly);


--
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date);


--
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);


--
-- Name: duy_nhat__xuat_hoa_don__ky_hieu_hoa_don__so_hoa_don; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX duy_nhat__xuat_hoa_don__ky_hieu_hoa_don__so_hoa_don ON public.yeu_cau_xuat_hoa_don USING btree (ky_hieu_hoa_don, so_hoa_don) WHERE ((trang_thai = 'da_xuat'::text) AND (NOT (ky_hieu_hoa_don = ''::text)));


--
-- Name: thuoc chan_doi_don_vi_thuoc; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER chan_doi_don_vi_thuoc BEFORE UPDATE OF id_don_vi_tinh ON public.thuoc FOR EACH ROW EXECUTE FUNCTION public.chan_doi_don_vi_thuoc_da_co_lo();


--
-- Name: lo_thuoc chan_doi_ma_lo; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER chan_doi_ma_lo BEFORE UPDATE OF id_thuoc, ma_lo_thuoc ON public.lo_thuoc FOR EACH ROW EXECUTE FUNCTION public.chan_doi_ma_lo_da_co_ton();


--
-- Name: chi_tiet_phieu_dieu_chuyen chan_sua_chung_tu; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER chan_sua_chung_tu BEFORE DELETE OR UPDATE ON public.chi_tiet_phieu_dieu_chuyen FOR EACH ROW EXECUTE FUNCTION public.chan_sua_chung_tu_kho();


--
-- Name: chi_tiet_phieu_kiem_ke chan_sua_chung_tu; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER chan_sua_chung_tu BEFORE DELETE OR UPDATE ON public.chi_tiet_phieu_kiem_ke FOR EACH ROW EXECUTE FUNCTION public.chan_sua_chung_tu_kho();


--
-- Name: chi_tiet_phieu_nhap chan_sua_chung_tu; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER chan_sua_chung_tu BEFORE DELETE OR UPDATE ON public.chi_tiet_phieu_nhap FOR EACH ROW EXECUTE FUNCTION public.chan_sua_chung_tu_kho();


--
-- Name: chi_tiet_phieu_tra_nha_cung_cap chan_sua_chung_tu; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER chan_sua_chung_tu BEFORE DELETE OR UPDATE ON public.chi_tiet_phieu_tra_nha_cung_cap FOR EACH ROW EXECUTE FUNCTION public.chan_sua_chung_tu_kho();


--
-- Name: chi_tiet_phieu_xuat_huy chan_sua_chung_tu; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER chan_sua_chung_tu BEFORE DELETE OR UPDATE ON public.chi_tiet_phieu_xuat_huy FOR EACH ROW EXECUTE FUNCTION public.chan_sua_chung_tu_kho();


--
-- Name: lich_su_dieu_kien_lo chan_sua_chung_tu; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER chan_sua_chung_tu BEFORE DELETE OR UPDATE ON public.lich_su_dieu_kien_lo FOR EACH ROW EXECUTE FUNCTION public.chan_sua_chung_tu_kho();


--
-- Name: phieu_dieu_chuyen chan_sua_chung_tu; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER chan_sua_chung_tu BEFORE DELETE OR UPDATE ON public.phieu_dieu_chuyen FOR EACH ROW EXECUTE FUNCTION public.chan_sua_chung_tu_kho();


--
-- Name: phieu_kiem_ke chan_sua_chung_tu; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER chan_sua_chung_tu BEFORE DELETE OR UPDATE ON public.phieu_kiem_ke FOR EACH ROW EXECUTE FUNCTION public.chan_sua_chung_tu_kho();


--
-- Name: phieu_nhap chan_sua_chung_tu; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER chan_sua_chung_tu BEFORE DELETE OR UPDATE ON public.phieu_nhap FOR EACH ROW EXECUTE FUNCTION public.chan_sua_chung_tu_kho();


--
-- Name: phieu_tra_nha_cung_cap chan_sua_chung_tu; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER chan_sua_chung_tu BEFORE DELETE OR UPDATE ON public.phieu_tra_nha_cung_cap FOR EACH ROW EXECUTE FUNCTION public.chan_sua_chung_tu_kho();


--
-- Name: phieu_xuat_huy chan_sua_chung_tu; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER chan_sua_chung_tu BEFORE DELETE OR UPDATE ON public.phieu_xuat_huy FOR EACH ROW EXECUTE FUNCTION public.chan_sua_chung_tu_kho();


--
-- Name: phieu_dieu_chuyen ghi_nhan_chung_tu_moi; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER ghi_nhan_chung_tu_moi AFTER INSERT ON public.phieu_dieu_chuyen FOR EACH ROW EXECUTE FUNCTION public.ghi_nhan_chung_tu_moi();


--
-- Name: phieu_kiem_ke ghi_nhan_chung_tu_moi; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER ghi_nhan_chung_tu_moi AFTER INSERT ON public.phieu_kiem_ke FOR EACH ROW EXECUTE FUNCTION public.ghi_nhan_chung_tu_moi();


--
-- Name: phieu_nhap ghi_nhan_chung_tu_moi; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER ghi_nhan_chung_tu_moi AFTER INSERT ON public.phieu_nhap FOR EACH ROW EXECUTE FUNCTION public.ghi_nhan_chung_tu_moi();


--
-- Name: phieu_tra_nha_cung_cap ghi_nhan_chung_tu_moi; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER ghi_nhan_chung_tu_moi AFTER INSERT ON public.phieu_tra_nha_cung_cap FOR EACH ROW EXECUTE FUNCTION public.ghi_nhan_chung_tu_moi();


--
-- Name: phieu_xuat_huy ghi_nhan_chung_tu_moi; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER ghi_nhan_chung_tu_moi AFTER INSERT ON public.phieu_xuat_huy FOR EACH ROW EXECUTE FUNCTION public.ghi_nhan_chung_tu_moi();


--
-- Name: auth_group_permissions auth_group_permissio_permission_id_84c5c92e_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_permission auth_permission_content_type_id_2f476e4b_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: anh_chi_nhanh khoa_ngoai__anh_chi_nhanh__id_chi_nhanh; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anh_chi_nhanh
    ADD CONSTRAINT khoa_ngoai__anh_chi_nhanh__id_chi_nhanh FOREIGN KEY (id_chi_nhanh) REFERENCES public.chi_nhanh(id_chi_nhanh) ON DELETE RESTRICT;


--
-- Name: anh_noi_dung khoa_ngoai__anh_noi_dung__id_tai_khoan; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anh_noi_dung
    ADD CONSTRAINT khoa_ngoai__anh_noi_dung__id_tai_khoan FOREIGN KEY (id_tai_khoan) REFERENCES public.tai_khoan(id_tai_khoan) ON DELETE RESTRICT;


--
-- Name: anh_thuoc khoa_ngoai__anh_thuoc__id_thuoc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anh_thuoc
    ADD CONSTRAINT khoa_ngoai__anh_thuoc__id_thuoc FOREIGN KEY (id_thuoc) REFERENCES public.thuoc(id_thuoc) ON DELETE RESTRICT;


--
-- Name: anh_tin_nhan khoa_ngoai__anh_tin_nhan__id_tin_nhan; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anh_tin_nhan
    ADD CONSTRAINT khoa_ngoai__anh_tin_nhan__id_tin_nhan FOREIGN KEY (id_tin_nhan) REFERENCES public.tin_nhan(id_tin_nhan) ON DELETE RESTRICT;


--
-- Name: chi_tiet_phieu_xuat_huy khoa_ngoai__chi_tiet_phieu_xuat_huy__id_lo_thuoc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_phieu_xuat_huy
    ADD CONSTRAINT khoa_ngoai__chi_tiet_phieu_xuat_huy__id_lo_thuoc FOREIGN KEY (id_lo_thuoc) REFERENCES public.lo_thuoc(id_lo_thuoc) ON DELETE RESTRICT;


--
-- Name: chi_tiet_phieu_xuat_huy khoa_ngoai__chi_tiet_phieu_xuat_huy__id_phieu_xuat_huy; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_phieu_xuat_huy
    ADD CONSTRAINT khoa_ngoai__chi_tiet_phieu_xuat_huy__id_phieu_xuat_huy FOREIGN KEY (id_phieu_xuat_huy) REFERENCES public.phieu_xuat_huy(id_phieu_xuat_huy) ON DELETE RESTRICT;


--
-- Name: chi_tiet_phieu_ban khoa_ngoai__ct_ban__id_phieu_ban; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_phieu_ban
    ADD CONSTRAINT khoa_ngoai__ct_ban__id_phieu_ban FOREIGN KEY (id_phieu_ban) REFERENCES public.phieu_ban(id_phieu_ban) ON DELETE RESTRICT;


--
-- Name: chi_tiet_phieu_ban khoa_ngoai__ct_ban__id_thuoc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_phieu_ban
    ADD CONSTRAINT khoa_ngoai__ct_ban__id_thuoc FOREIGN KEY (id_thuoc) REFERENCES public.thuoc(id_thuoc) ON DELETE RESTRICT;


--
-- Name: chi_tiet_phieu_dieu_chuyen khoa_ngoai__ct_dieu_chuyen__id_lo_thuoc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_phieu_dieu_chuyen
    ADD CONSTRAINT khoa_ngoai__ct_dieu_chuyen__id_lo_thuoc FOREIGN KEY (id_lo_thuoc) REFERENCES public.lo_thuoc(id_lo_thuoc) ON DELETE RESTRICT;


--
-- Name: chi_tiet_phieu_dieu_chuyen khoa_ngoai__ct_dieu_chuyen__id_phieu_dieu_chuyen; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_phieu_dieu_chuyen
    ADD CONSTRAINT khoa_ngoai__ct_dieu_chuyen__id_phieu_dieu_chuyen FOREIGN KEY (id_phieu_dieu_chuyen) REFERENCES public.phieu_dieu_chuyen(id_phieu_dieu_chuyen) ON DELETE RESTRICT;


--
-- Name: chi_tiet_don_hang khoa_ngoai__ct_don_hang__id_don_hang; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_don_hang
    ADD CONSTRAINT khoa_ngoai__ct_don_hang__id_don_hang FOREIGN KEY (id_don_hang) REFERENCES public.don_hang(id_don_hang) ON DELETE RESTRICT;


--
-- Name: chi_tiet_don_hang khoa_ngoai__ct_don_hang__id_thuoc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_don_hang
    ADD CONSTRAINT khoa_ngoai__ct_don_hang__id_thuoc FOREIGN KEY (id_thuoc) REFERENCES public.thuoc(id_thuoc) ON DELETE RESTRICT;


--
-- Name: chi_tiet_phieu_kiem_ke khoa_ngoai__ct_kiem_ke__id_lo_thuoc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_phieu_kiem_ke
    ADD CONSTRAINT khoa_ngoai__ct_kiem_ke__id_lo_thuoc FOREIGN KEY (id_lo_thuoc) REFERENCES public.lo_thuoc(id_lo_thuoc) ON DELETE RESTRICT;


--
-- Name: chi_tiet_phieu_kiem_ke khoa_ngoai__ct_kiem_ke__id_phieu_kiem_ke; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_phieu_kiem_ke
    ADD CONSTRAINT khoa_ngoai__ct_kiem_ke__id_phieu_kiem_ke FOREIGN KEY (id_phieu_kiem_ke) REFERENCES public.phieu_kiem_ke(id_phieu_kiem_ke) ON DELETE RESTRICT;


--
-- Name: chi_tiet_phieu_nhap khoa_ngoai__ct_nhap__id_lo_thuoc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_phieu_nhap
    ADD CONSTRAINT khoa_ngoai__ct_nhap__id_lo_thuoc FOREIGN KEY (id_lo_thuoc) REFERENCES public.lo_thuoc(id_lo_thuoc) ON DELETE RESTRICT;


--
-- Name: chi_tiet_phieu_nhap khoa_ngoai__ct_nhap__id_phieu_nhap; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_phieu_nhap
    ADD CONSTRAINT khoa_ngoai__ct_nhap__id_phieu_nhap FOREIGN KEY (id_phieu_nhap) REFERENCES public.phieu_nhap(id_phieu_nhap) ON DELETE RESTRICT;


--
-- Name: chi_tiet_phieu_tra_nha_cung_cap khoa_ngoai__ct_tra_ncc__id_lo_thuoc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_phieu_tra_nha_cung_cap
    ADD CONSTRAINT khoa_ngoai__ct_tra_ncc__id_lo_thuoc FOREIGN KEY (id_lo_thuoc) REFERENCES public.lo_thuoc(id_lo_thuoc) ON DELETE RESTRICT;


--
-- Name: chi_tiet_phieu_tra_nha_cung_cap khoa_ngoai__ct_tra_ncc__id_phieu_tra_nha_cung_cap; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chi_tiet_phieu_tra_nha_cung_cap
    ADD CONSTRAINT khoa_ngoai__ct_tra_ncc__id_phieu_tra_nha_cung_cap FOREIGN KEY (id_phieu_tra_nha_cung_cap) REFERENCES public.phieu_tra_nha_cung_cap(id_phieu_tra_nha_cung_cap) ON DELETE RESTRICT;


--
-- Name: danh_gia_chi_nhanh khoa_ngoai__danh_gia_chi_nhanh__id_chi_nhanh; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.danh_gia_chi_nhanh
    ADD CONSTRAINT khoa_ngoai__danh_gia_chi_nhanh__id_chi_nhanh FOREIGN KEY (id_chi_nhanh) REFERENCES public.chi_nhanh(id_chi_nhanh) ON DELETE RESTRICT;


--
-- Name: danh_gia_chi_nhanh khoa_ngoai__danh_gia_chi_nhanh__id_tai_khoan_khach; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.danh_gia_chi_nhanh
    ADD CONSTRAINT khoa_ngoai__danh_gia_chi_nhanh__id_tai_khoan_khach FOREIGN KEY (id_tai_khoan_khach) REFERENCES public.tai_khoan(id_tai_khoan) ON DELETE RESTRICT;


--
-- Name: danh_gia_thuoc khoa_ngoai__danh_gia_thuoc__id_tai_khoan_khach; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.danh_gia_thuoc
    ADD CONSTRAINT khoa_ngoai__danh_gia_thuoc__id_tai_khoan_khach FOREIGN KEY (id_tai_khoan_khach) REFERENCES public.tai_khoan(id_tai_khoan) ON DELETE RESTRICT;


--
-- Name: danh_gia_thuoc khoa_ngoai__danh_gia_thuoc__id_thuoc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.danh_gia_thuoc
    ADD CONSTRAINT khoa_ngoai__danh_gia_thuoc__id_thuoc FOREIGN KEY (id_thuoc) REFERENCES public.thuoc(id_thuoc) ON DELETE RESTRICT;


--
-- Name: don_hang khoa_ngoai__don_hang__id_chi_nhanh; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.don_hang
    ADD CONSTRAINT khoa_ngoai__don_hang__id_chi_nhanh FOREIGN KEY (id_chi_nhanh) REFERENCES public.chi_nhanh(id_chi_nhanh) ON DELETE RESTRICT;


--
-- Name: don_hang khoa_ngoai__don_hang__id_tai_khoan_khach; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.don_hang
    ADD CONSTRAINT khoa_ngoai__don_hang__id_tai_khoan_khach FOREIGN KEY (id_tai_khoan_khach) REFERENCES public.tai_khoan(id_tai_khoan) ON DELETE RESTRICT;


--
-- Name: du_bao_bay_ngay khoa_ngoai__du_bao__id_ket_qua_mo_hinh; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.du_bao_bay_ngay
    ADD CONSTRAINT khoa_ngoai__du_bao__id_ket_qua_mo_hinh FOREIGN KEY (id_ket_qua_mo_hinh) REFERENCES public.ket_qua_mo_hinh(id_ket_qua_mo_hinh) ON DELETE RESTRICT;


--
-- Name: ket_qua_mo_hinh khoa_ngoai__ket_qua__id_lan_thuc_nghiem; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ket_qua_mo_hinh
    ADD CONSTRAINT khoa_ngoai__ket_qua__id_lan_thuc_nghiem FOREIGN KEY (id_lan_thuc_nghiem) REFERENCES public.lan_thuc_nghiem(id_lan_thuc_nghiem) ON DELETE RESTRICT;


--
-- Name: khuyen_mai khoa_ngoai__khuyen_mai__id_thuoc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.khuyen_mai
    ADD CONSTRAINT khoa_ngoai__khuyen_mai__id_thuoc FOREIGN KEY (id_thuoc) REFERENCES public.thuoc(id_thuoc) ON DELETE RESTRICT;


--
-- Name: kich_ban_thieu_hang khoa_ngoai__kich_ban_thieu_hang__id_du_bao_bay_ngay; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kich_ban_thieu_hang
    ADD CONSTRAINT khoa_ngoai__kich_ban_thieu_hang__id_du_bao_bay_ngay FOREIGN KEY (id_du_bao_bay_ngay) REFERENCES public.du_bao_bay_ngay(id_du_bao_bay_ngay) ON DELETE RESTRICT;


--
-- Name: lan_thuc_nghiem khoa_ngoai__lan_thuc_nghiem__id_nguon_du_lieu; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lan_thuc_nghiem
    ADD CONSTRAINT khoa_ngoai__lan_thuc_nghiem__id_nguon_du_lieu FOREIGN KEY (id_nguon_du_lieu) REFERENCES public.nguon_du_lieu(id_nguon_du_lieu) ON DELETE RESTRICT;


--
-- Name: lich_su_dieu_kien_lo khoa_ngoai__lich_su_dieu_kien_lo__id_lo_thuoc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lich_su_dieu_kien_lo
    ADD CONSTRAINT khoa_ngoai__lich_su_dieu_kien_lo__id_lo_thuoc FOREIGN KEY (id_lo_thuoc) REFERENCES public.lo_thuoc(id_lo_thuoc) ON DELETE RESTRICT;


--
-- Name: lich_su_dieu_kien_lo khoa_ngoai__lich_su_dieu_kien_lo__id_tai_khoan_thuc_hien; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lich_su_dieu_kien_lo
    ADD CONSTRAINT khoa_ngoai__lich_su_dieu_kien_lo__id_tai_khoan_thuc_hien FOREIGN KEY (id_tai_khoan_thuc_hien) REFERENCES public.tai_khoan(id_tai_khoan) ON DELETE RESTRICT;


--
-- Name: lich_su_don_hang khoa_ngoai__lich_su_don_hang__id_don_hang; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lich_su_don_hang
    ADD CONSTRAINT khoa_ngoai__lich_su_don_hang__id_don_hang FOREIGN KEY (id_don_hang) REFERENCES public.don_hang(id_don_hang) ON DELETE RESTRICT;


--
-- Name: lich_su_don_hang khoa_ngoai__lich_su_don_hang__id_tai_khoan_thuc_hien; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lich_su_don_hang
    ADD CONSTRAINT khoa_ngoai__lich_su_don_hang__id_tai_khoan_thuc_hien FOREIGN KEY (id_tai_khoan_thuc_hien) REFERENCES public.tai_khoan(id_tai_khoan) ON DELETE RESTRICT;


--
-- Name: lo_thuoc khoa_ngoai__lo_thuoc__id_thuoc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lo_thuoc
    ADD CONSTRAINT khoa_ngoai__lo_thuoc__id_thuoc FOREIGN KEY (id_thuoc) REFERENCES public.thuoc(id_thuoc) ON DELETE RESTRICT;


--
-- Name: nhan_vien khoa_ngoai__nhan_vien__id_tai_khoan; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nhan_vien
    ADD CONSTRAINT khoa_ngoai__nhan_vien__id_tai_khoan FOREIGN KEY (id_tai_khoan) REFERENCES public.tai_khoan(id_tai_khoan) ON DELETE RESTRICT;


--
-- Name: nhat_ky_email khoa_ngoai__nhat_ky_email__id_don_hang; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nhat_ky_email
    ADD CONSTRAINT khoa_ngoai__nhat_ky_email__id_don_hang FOREIGN KEY (id_don_hang) REFERENCES public.don_hang(id_don_hang) ON DELETE RESTRICT;


--
-- Name: nhat_ky_email khoa_ngoai__nhat_ky_email__id_tai_khoan; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nhat_ky_email
    ADD CONSTRAINT khoa_ngoai__nhat_ky_email__id_tai_khoan FOREIGN KEY (id_tai_khoan) REFERENCES public.tai_khoan(id_tai_khoan) ON DELETE RESTRICT;


--
-- Name: phan_bo_phieu_ban khoa_ngoai__pb_ban__id_chi_tiet_phieu_ban; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phan_bo_phieu_ban
    ADD CONSTRAINT khoa_ngoai__pb_ban__id_chi_tiet_phieu_ban FOREIGN KEY (id_chi_tiet_phieu_ban) REFERENCES public.chi_tiet_phieu_ban(id_chi_tiet_phieu_ban) ON DELETE RESTRICT;


--
-- Name: phan_bo_phieu_ban khoa_ngoai__pb_ban__id_ton_kho; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phan_bo_phieu_ban
    ADD CONSTRAINT khoa_ngoai__pb_ban__id_ton_kho FOREIGN KEY (id_ton_kho) REFERENCES public.ton_kho(id_ton_kho) ON DELETE RESTRICT;


--
-- Name: phan_bo_don_hang khoa_ngoai__pb_don_hang__id_chi_tiet_don_hang; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phan_bo_don_hang
    ADD CONSTRAINT khoa_ngoai__pb_don_hang__id_chi_tiet_don_hang FOREIGN KEY (id_chi_tiet_don_hang) REFERENCES public.chi_tiet_don_hang(id_chi_tiet_don_hang) ON DELETE RESTRICT;


--
-- Name: phan_bo_don_hang khoa_ngoai__pb_don_hang__id_ton_kho; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phan_bo_don_hang
    ADD CONSTRAINT khoa_ngoai__pb_don_hang__id_ton_kho FOREIGN KEY (id_ton_kho) REFERENCES public.ton_kho(id_ton_kho) ON DELETE RESTRICT;


--
-- Name: phieu_ban khoa_ngoai__phieu_ban__id_chi_nhanh; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_ban
    ADD CONSTRAINT khoa_ngoai__phieu_ban__id_chi_nhanh FOREIGN KEY (id_chi_nhanh) REFERENCES public.chi_nhanh(id_chi_nhanh) ON DELETE RESTRICT;


--
-- Name: phieu_ban khoa_ngoai__phieu_ban__id_don_hang; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_ban
    ADD CONSTRAINT khoa_ngoai__phieu_ban__id_don_hang FOREIGN KEY (id_don_hang) REFERENCES public.don_hang(id_don_hang) ON DELETE RESTRICT;


--
-- Name: phieu_ban khoa_ngoai__phieu_ban__id_tai_khoan_lap; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_ban
    ADD CONSTRAINT khoa_ngoai__phieu_ban__id_tai_khoan_lap FOREIGN KEY (id_tai_khoan_lap) REFERENCES public.tai_khoan(id_tai_khoan) ON DELETE RESTRICT;


--
-- Name: phieu_dieu_chuyen khoa_ngoai__phieu_dieu_chuyen__id_chi_nhanh_dich; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_dieu_chuyen
    ADD CONSTRAINT khoa_ngoai__phieu_dieu_chuyen__id_chi_nhanh_dich FOREIGN KEY (id_chi_nhanh_dich) REFERENCES public.chi_nhanh(id_chi_nhanh) ON DELETE RESTRICT;


--
-- Name: phieu_dieu_chuyen khoa_ngoai__phieu_dieu_chuyen__id_chi_nhanh_nguon; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_dieu_chuyen
    ADD CONSTRAINT khoa_ngoai__phieu_dieu_chuyen__id_chi_nhanh_nguon FOREIGN KEY (id_chi_nhanh_nguon) REFERENCES public.chi_nhanh(id_chi_nhanh) ON DELETE RESTRICT;


--
-- Name: phieu_dieu_chuyen khoa_ngoai__phieu_dieu_chuyen__id_tai_khoan_lap; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_dieu_chuyen
    ADD CONSTRAINT khoa_ngoai__phieu_dieu_chuyen__id_tai_khoan_lap FOREIGN KEY (id_tai_khoan_lap) REFERENCES public.tai_khoan(id_tai_khoan) ON DELETE RESTRICT;


--
-- Name: phieu_kiem_ke khoa_ngoai__phieu_kiem_ke__id_chi_nhanh; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_kiem_ke
    ADD CONSTRAINT khoa_ngoai__phieu_kiem_ke__id_chi_nhanh FOREIGN KEY (id_chi_nhanh) REFERENCES public.chi_nhanh(id_chi_nhanh) ON DELETE RESTRICT;


--
-- Name: phieu_kiem_ke khoa_ngoai__phieu_kiem_ke__id_tai_khoan_lap; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_kiem_ke
    ADD CONSTRAINT khoa_ngoai__phieu_kiem_ke__id_tai_khoan_lap FOREIGN KEY (id_tai_khoan_lap) REFERENCES public.tai_khoan(id_tai_khoan) ON DELETE RESTRICT;


--
-- Name: phieu_nhap khoa_ngoai__phieu_nhap__id_chi_nhanh; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_nhap
    ADD CONSTRAINT khoa_ngoai__phieu_nhap__id_chi_nhanh FOREIGN KEY (id_chi_nhanh) REFERENCES public.chi_nhanh(id_chi_nhanh) ON DELETE RESTRICT;


--
-- Name: phieu_nhap khoa_ngoai__phieu_nhap__id_nha_cung_cap; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_nhap
    ADD CONSTRAINT khoa_ngoai__phieu_nhap__id_nha_cung_cap FOREIGN KEY (id_nha_cung_cap) REFERENCES public.nha_cung_cap(id_nha_cung_cap) ON DELETE RESTRICT;


--
-- Name: phieu_nhap khoa_ngoai__phieu_nhap__id_tai_khoan_lap; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_nhap
    ADD CONSTRAINT khoa_ngoai__phieu_nhap__id_tai_khoan_lap FOREIGN KEY (id_tai_khoan_lap) REFERENCES public.tai_khoan(id_tai_khoan) ON DELETE RESTRICT;


--
-- Name: phieu_xuat_huy khoa_ngoai__phieu_xuat_huy__id_chi_nhanh; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_xuat_huy
    ADD CONSTRAINT khoa_ngoai__phieu_xuat_huy__id_chi_nhanh FOREIGN KEY (id_chi_nhanh) REFERENCES public.chi_nhanh(id_chi_nhanh) ON DELETE RESTRICT;


--
-- Name: phieu_xuat_huy khoa_ngoai__phieu_xuat_huy__id_tai_khoan_lap; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_xuat_huy
    ADD CONSTRAINT khoa_ngoai__phieu_xuat_huy__id_tai_khoan_lap FOREIGN KEY (id_tai_khoan_lap) REFERENCES public.tai_khoan(id_tai_khoan) ON DELETE RESTRICT;


--
-- Name: cuoc_tro_chuyen khoa_ngoai__phong__id_chi_nhanh; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cuoc_tro_chuyen
    ADD CONSTRAINT khoa_ngoai__phong__id_chi_nhanh FOREIGN KEY (id_chi_nhanh) REFERENCES public.chi_nhanh(id_chi_nhanh) ON DELETE RESTRICT;


--
-- Name: cuoc_tro_chuyen khoa_ngoai__phong__id_tai_khoan_danh_dau_xong; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cuoc_tro_chuyen
    ADD CONSTRAINT khoa_ngoai__phong__id_tai_khoan_danh_dau_xong FOREIGN KEY (id_tai_khoan_danh_dau_xong) REFERENCES public.tai_khoan(id_tai_khoan) ON DELETE RESTRICT;


--
-- Name: cuoc_tro_chuyen khoa_ngoai__phong__id_tai_khoan_khach; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cuoc_tro_chuyen
    ADD CONSTRAINT khoa_ngoai__phong__id_tai_khoan_khach FOREIGN KEY (id_tai_khoan_khach) REFERENCES public.tai_khoan(id_tai_khoan) ON DELETE RESTRICT;


--
-- Name: cuoc_tro_chuyen khoa_ngoai__phong__id_tin_nhan_cuoi; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cuoc_tro_chuyen
    ADD CONSTRAINT khoa_ngoai__phong__id_tin_nhan_cuoi FOREIGN KEY (id_tin_nhan_cuoi) REFERENCES public.tin_nhan(id_tin_nhan) ON DELETE RESTRICT;


--
-- Name: cuoc_tro_chuyen khoa_ngoai__phong__id_tin_nhan_khach_da_doc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cuoc_tro_chuyen
    ADD CONSTRAINT khoa_ngoai__phong__id_tin_nhan_khach_da_doc FOREIGN KEY (id_tin_nhan_khach_da_doc) REFERENCES public.tin_nhan(id_tin_nhan) ON DELETE RESTRICT;


--
-- Name: cuoc_tro_chuyen khoa_ngoai__phong__id_tin_nhan_nha_thuoc_da_doc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cuoc_tro_chuyen
    ADD CONSTRAINT khoa_ngoai__phong__id_tin_nhan_nha_thuoc_da_doc FOREIGN KEY (id_tin_nhan_nha_thuoc_da_doc) REFERENCES public.tin_nhan(id_tin_nhan) ON DELETE RESTRICT;


--
-- Name: quan_sat_ban_hang khoa_ngoai__quan_sat__id_nguon_du_lieu; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quan_sat_ban_hang
    ADD CONSTRAINT khoa_ngoai__quan_sat__id_nguon_du_lieu FOREIGN KEY (id_nguon_du_lieu) REFERENCES public.nguon_du_lieu(id_nguon_du_lieu) ON DELETE RESTRICT;


--
-- Name: quy_doi_bao_goi khoa_ngoai__quy_doi_bao_goi__id_thuoc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quy_doi_bao_goi
    ADD CONSTRAINT khoa_ngoai__quy_doi_bao_goi__id_thuoc FOREIGN KEY (id_thuoc) REFERENCES public.thuoc(id_thuoc) ON DELETE RESTRICT;


--
-- Name: quyen_cua_nhom khoa_ngoai__quyen_cua_nhom__id_nhom_quyen; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quyen_cua_nhom
    ADD CONSTRAINT khoa_ngoai__quyen_cua_nhom__id_nhom_quyen FOREIGN KEY (id_nhom_quyen) REFERENCES public.nhom_quyen(id_nhom_quyen) ON DELETE RESTRICT;


--
-- Name: quyen_rieng_tai_khoan khoa_ngoai__quyen_rieng_tai_khoan__id_tai_khoan; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quyen_rieng_tai_khoan
    ADD CONSTRAINT khoa_ngoai__quyen_rieng_tai_khoan__id_tai_khoan FOREIGN KEY (id_tai_khoan) REFERENCES public.tai_khoan(id_tai_khoan) ON DELETE RESTRICT;


--
-- Name: tai_khoan khoa_ngoai__tai_khoan__id_chi_nhanh; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tai_khoan
    ADD CONSTRAINT khoa_ngoai__tai_khoan__id_chi_nhanh FOREIGN KEY (id_chi_nhanh) REFERENCES public.chi_nhanh(id_chi_nhanh) ON DELETE RESTRICT;


--
-- Name: tai_khoan khoa_ngoai__tai_khoan__id_nhom_quyen; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tai_khoan
    ADD CONSTRAINT khoa_ngoai__tai_khoan__id_nhom_quyen FOREIGN KEY (id_nhom_quyen) REFERENCES public.nhom_quyen(id_nhom_quyen) ON DELETE RESTRICT;


--
-- Name: thuoc khoa_ngoai__thuoc__id_danh_muc_san_pham; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.thuoc
    ADD CONSTRAINT khoa_ngoai__thuoc__id_danh_muc_san_pham FOREIGN KEY (id_danh_muc_san_pham) REFERENCES public.danh_muc_san_pham(id_danh_muc_san_pham) ON DELETE RESTRICT;


--
-- Name: thuoc khoa_ngoai__thuoc__id_don_vi_tinh; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.thuoc
    ADD CONSTRAINT khoa_ngoai__thuoc__id_don_vi_tinh FOREIGN KEY (id_don_vi_tinh) REFERENCES public.don_vi_tinh(id_don_vi_tinh) ON DELETE RESTRICT;


--
-- Name: thuoc khoa_ngoai__thuoc__id_nhom_atc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.thuoc
    ADD CONSTRAINT khoa_ngoai__thuoc__id_nhom_atc FOREIGN KEY (id_nhom_atc) REFERENCES public.nhom_atc(id_nhom_atc) ON DELETE RESTRICT;


--
-- Name: tin_nhan khoa_ngoai__tin_nhan__id_cuoc_tro_chuyen; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tin_nhan
    ADD CONSTRAINT khoa_ngoai__tin_nhan__id_cuoc_tro_chuyen FOREIGN KEY (id_cuoc_tro_chuyen) REFERENCES public.cuoc_tro_chuyen(id_cuoc_tro_chuyen) ON DELETE RESTRICT;


--
-- Name: tin_nhan khoa_ngoai__tin_nhan__id_don_hang; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tin_nhan
    ADD CONSTRAINT khoa_ngoai__tin_nhan__id_don_hang FOREIGN KEY (id_don_hang) REFERENCES public.don_hang(id_don_hang) ON DELETE RESTRICT;


--
-- Name: tin_nhan khoa_ngoai__tin_nhan__id_tai_khoan_gui; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tin_nhan
    ADD CONSTRAINT khoa_ngoai__tin_nhan__id_tai_khoan_gui FOREIGN KEY (id_tai_khoan_gui) REFERENCES public.tai_khoan(id_tai_khoan) ON DELETE RESTRICT;


--
-- Name: tin_nhan khoa_ngoai__tin_nhan__id_thuoc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tin_nhan
    ADD CONSTRAINT khoa_ngoai__tin_nhan__id_thuoc FOREIGN KEY (id_thuoc) REFERENCES public.thuoc(id_thuoc) ON DELETE RESTRICT;


--
-- Name: tin_tuc khoa_ngoai__tin_tuc__id_tai_khoan_viet; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tin_tuc
    ADD CONSTRAINT khoa_ngoai__tin_tuc__id_tai_khoan_viet FOREIGN KEY (id_tai_khoan_viet) REFERENCES public.tai_khoan(id_tai_khoan) ON DELETE RESTRICT;


--
-- Name: ton_kho khoa_ngoai__ton_kho__id_chi_nhanh; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ton_kho
    ADD CONSTRAINT khoa_ngoai__ton_kho__id_chi_nhanh FOREIGN KEY (id_chi_nhanh) REFERENCES public.chi_nhanh(id_chi_nhanh) ON DELETE RESTRICT;


--
-- Name: ton_kho khoa_ngoai__ton_kho__id_lo_thuoc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ton_kho
    ADD CONSTRAINT khoa_ngoai__ton_kho__id_lo_thuoc FOREIGN KEY (id_lo_thuoc) REFERENCES public.lo_thuoc(id_lo_thuoc) ON DELETE RESTRICT;


--
-- Name: phieu_tra_nha_cung_cap khoa_ngoai__tra_ncc__id_phieu_nhap; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_tra_nha_cung_cap
    ADD CONSTRAINT khoa_ngoai__tra_ncc__id_phieu_nhap FOREIGN KEY (id_phieu_nhap) REFERENCES public.phieu_nhap(id_phieu_nhap) ON DELETE RESTRICT;


--
-- Name: phieu_tra_nha_cung_cap khoa_ngoai__tra_ncc__id_tai_khoan_lap; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phieu_tra_nha_cung_cap
    ADD CONSTRAINT khoa_ngoai__tra_ncc__id_tai_khoan_lap FOREIGN KEY (id_tai_khoan_lap) REFERENCES public.tai_khoan(id_tai_khoan) ON DELETE RESTRICT;


--
-- Name: phien_xac_thuc khoa_ngoai__xac_thuc__id_tai_khoan; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phien_xac_thuc
    ADD CONSTRAINT khoa_ngoai__xac_thuc__id_tai_khoan FOREIGN KEY (id_tai_khoan) REFERENCES public.tai_khoan(id_tai_khoan) ON DELETE RESTRICT;


--
-- Name: yeu_cau_xuat_hoa_don khoa_ngoai__xuat_hoa_don__id_don_hang; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.yeu_cau_xuat_hoa_don
    ADD CONSTRAINT khoa_ngoai__xuat_hoa_don__id_don_hang FOREIGN KEY (id_don_hang) REFERENCES public.don_hang(id_don_hang) ON DELETE RESTRICT;


--
-- Name: yeu_cau_xuat_hoa_don khoa_ngoai__xuat_hoa_don__id_tai_khoan_xu_ly; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.yeu_cau_xuat_hoa_don
    ADD CONSTRAINT khoa_ngoai__xuat_hoa_don__id_tai_khoan_xu_ly FOREIGN KEY (id_tai_khoan_xu_ly) REFERENCES public.tai_khoan(id_tai_khoan) ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--
