from django.db import migrations

# Migration giữ nguyên tập ký tự của chính nó, không nhập hằng số có thể đổi về sau.
TAO_HAM = r"""
CREATE FUNCTION public.khong_rong(van_ban text)
RETURNS boolean
LANGUAGE sql
IMMUTABLE STRICT PARALLEL SAFE
AS $ham$
    SELECT char_length(translate(
        van_ban,
        U&'\0009\000A\000B\000C\000D\0020\0085\00A0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000\200B\FEFF',
        ''
    )) > 0;
$ham$;

COMMENT ON FUNCTION public.khong_rong(text) IS
'Đúng khi có ký tự ngoài 27 ký tự khoảng trắng của quy ước project mục 7.1; không phụ thuộc locale. NULL trả NULL, cột bắt buộc vẫn cần NOT NULL. Sửa hàm không tự kiểm lại dữ liệu cũ; phải kiểm tra và xác thực lại CHECK trong migration mới.';

CREATE FUNCTION public.da_cat_khoang_trang(van_ban text)
RETURNS boolean
LANGUAGE sql
IMMUTABLE STRICT PARALLEL SAFE
AS $ham$
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
$ham$;

COMMENT ON FUNCTION public.da_cat_khoang_trang(text) IS
'Đúng khi đầu và cuối không thuộc 27 ký tự khoảng trắng ở mục 7.1; chuỗi rỗng hợp lệ với riêng quy tắc cắt khoảng trắng, cột bắt buộc thêm khong_rong. Yêu cầu database UTF8 để ascii trả mã Unicode. NULL trả NULL. Sửa hàm không tự kiểm lại dữ liệu cũ; phải kiểm tra và xác thực lại CHECK trong migration mới.';

CREATE FUNCTION public.la_mot_dong(van_ban text)
RETURNS boolean
LANGUAGE sql
IMMUTABLE STRICT PARALLEL SAFE
AS $ham$
    SELECT char_length(translate(
        van_ban,
        U&'\0001\0002\0003\0004\0005\0006\0007\0008\0009\000A\000B\000C\000D\000E\000F\0010\0011\0012\0013\0014\0015\0016\0017\0018\0019\001A\001B\001C\001D\001E\001F\007F\0080\0081\0082\0083\0084\0085\0086\0087\0088\0089\008A\008B\008C\008D\008E\008F\0090\0091\0092\0093\0094\0095\0096\0097\0098\0099\009A\009B\009C\009D\009E\009F\2028\2029',
        ''
    )) = char_length(van_ban);
$ham$;

COMMENT ON FUNCTION public.la_mot_dong(text) IS
'Đúng khi không chứa U+0001 đến U+001F, U+007F đến U+009F, U+2028 hoặc U+2029. Không dùng lớp ký tự phụ thuộc locale. PostgreSQL text không chứa được U+0000. NULL trả NULL. Sửa hàm không tự kiểm lại dữ liệu cũ; phải kiểm tra và xác thực lại CHECK trong migration mới.';
"""

XOA_HAM = """
DROP FUNCTION public.la_mot_dong(text);
DROP FUNCTION public.da_cat_khoang_trang(text);
DROP FUNCTION public.khong_rong(text);
"""


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [migrations.RunSQL(sql=TAO_HAM, reverse_sql=XOA_HAM)]
