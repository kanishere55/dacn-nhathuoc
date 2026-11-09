# Khởi tạo hoặc sửa kết nối CSDL của project trên PostgreSQL 18 cài bằng bộ cài Windows.
# Chạy lại được: chỉ tạo phần còn thiếu, không xóa dữ liệu đang có.
#   powershell -ExecutionPolicy Bypass -File cong_cu\khoi_tao_csdl_windows.ps1
# Mật khẩu chỉ nhập từ bàn phím hoặc đọc từ .env, không in ra màn hình.

$ErrorActionPreference = 'Continue'
$goc = Split-Path -Parent $PSScriptRoot

$laAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $laAdmin) {
    Write-Host 'Cần quyền Administrator để bật dịch vụ PostgreSQL và cài PostGIS. Đang mở cửa sổ mới...'
    Start-Process powershell -Verb RunAs -ArgumentList @(
        '-NoExit', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"")
    exit
}

Set-Location $goc
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = New-Object Text.UTF8Encoding $false
$env:PGCLIENTENCODING = 'UTF8'
$env:PYTHONUTF8 = '1'

$python = Join-Path $goc '.venv\Scripts\python.exe'
$tepEnv = Join-Path $goc '.env'
$pg = 'C:\Program Files\PostgreSQL\18'
$psql = Join-Path $pg 'bin\psql.exe'
$boPostgis = Join-Path $goc '.venv\cong_cu\postgis\postgis-bundle-pg18-3.6.2x64'
$redis = Join-Path $goc '.venv\cong_cu\redis\Redis-8.10.3-Windows-x64-msys2\redis-server.exe'

function Dung([string]$loi) {
    Write-Host "LỖI: $loi" -ForegroundColor Red
    Write-Host 'Chụp màn hình cửa sổ này gửi lại để được hỗ trợ.'
    exit 1
}
function Buoc([string]$noiDung) { Write-Host "`n== $noiDung" -ForegroundColor Cyan }

function Doc-Env {
    $ketQua = @{}
    foreach ($dong in Get-Content $tepEnv -Encoding UTF8) {
        if ($dong -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$') { $ketQua[$matches[1]] = $matches[2].Trim() }
    }
    $ketQua
}
function Ghi-Env([string]$khoa, [string]$giaTri) {
    $cacDong = @(Get-Content $tepEnv -Encoding UTF8)
    $daCo = $false
    $moi = foreach ($dong in $cacDong) {
        if ($dong -match "^\s*$khoa\s*=") { $daCo = $true; "$khoa=$giaTri" } else { $dong }
    }
    if (-not $daCo) { $moi = @($moi) + "$khoa=$giaTri" }
    [IO.File]::WriteAllLines($tepEnv, [string[]]$moi, (New-Object Text.UTF8Encoding $false))
}
function Sql([string]$csdl, [string]$lenh) {
    $ra = $lenh | & $psql -h 127.0.0.1 -p 5432 -U postgres -d $csdl -v ON_ERROR_STOP=1 -q -t -A -f - 2>&1
    $script:maThoat = $LASTEXITCODE
    ($ra | Out-String).Trim()
}
function Chuoi-Sql([string]$s) { "'" + $s.Replace("'", "''") + "'" }
function Ten-Sql([string]$s) { '"' + $s.Replace('"', '""') + '"' }

if (-not (Test-Path $python)) { Dung 'Không thấy .venv\Scripts\python.exe. Tạo môi trường ảo theo README trước.' }
if (-not (Test-Path $psql)) { Dung "Không thấy $psql. Script này dành cho PostgreSQL 18 cài bằng bộ cài Windows." }
if (-not (Test-Path $tepEnv)) { Copy-Item (Join-Path $goc '.env.example') $tepEnv }

Buoc 'Bật dịch vụ PostgreSQL'
$dichVu = Get-Service 'postgresql-x64-18' -ErrorAction SilentlyContinue
if ($null -eq $dichVu) { Dung 'Không có dịch vụ postgresql-x64-18.' }
if ($dichVu.Status -ne 'Running') { Start-Service $dichVu.Name; $dichVu.WaitForStatus('Running', '00:00:30') }
Set-Service $dichVu.Name -StartupType Automatic
Write-Host 'Dịch vụ đang chạy ở cổng 5432 và tự bật cùng Windows.'

function Ra-Chu($an) {
    [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($an))
}
function Cho-San-Sang {
    for ($i = 0; $i -lt 20; $i++) {
        $null = Sql 'postgres' 'SELECT 1;'
        if ($maThoat -eq 0) { return }
        Start-Sleep -Seconds 1
    }
}
function Dat-Lai-Mat-Khau-Postgres {
    # Tạm cho tài khoản postgres đăng nhập không mật khẩu từ chính máy này, đặt mật khẩu mới,
    # rồi khôi phục nguyên trạng pg_hba.conf.
    $hba = Join-Path $pg 'data\pg_hba.conf'
    if (-not (Test-Path $hba)) { Dung "Không thấy $hba." }
    do {
        $mk1 = Ra-Chu (Read-Host 'Đặt mật khẩu MỚI cho tài khoản postgres' -AsSecureString)
        $mk2 = Ra-Chu (Read-Host 'Nhập lại mật khẩu mới' -AsSecureString)
        if (-not $mk1 -or $mk1 -ne $mk2) { Write-Host 'Hai lần nhập không khớp hoặc để trống.' -ForegroundColor Yellow }
    } while (-not $mk1 -or $mk1 -ne $mk2)
    $saoLuu = "$hba.truoc_dat_lai"
    Copy-Item $hba $saoLuu -Force
    try {
        $tam = "host all postgres 127.0.0.1/32 trust`r`nhost all postgres ::1/128 trust`r`n" +
            [IO.File]::ReadAllText($hba)
        [IO.File]::WriteAllText($hba, $tam, (New-Object Text.UTF8Encoding $false))
        Restart-Service 'postgresql-x64-18'
        Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
        Cho-San-Sang
        $ra = Sql 'postgres' "ALTER ROLE postgres WITH PASSWORD $(Chuoi-Sql $mk1);"
        if ($maThoat -ne 0) { throw $ra }
    } finally {
        Copy-Item $saoLuu $hba -Force
        Remove-Item $saoLuu -Force
        Restart-Service 'postgresql-x64-18'
    }
    $env:PGPASSWORD = $mk1
    Cho-San-Sang
    Write-Host 'Đã đặt mật khẩu mới cho postgres. Hãy ghi nhớ mật khẩu này.' -ForegroundColor Green
}

Buoc 'Đăng nhập PostgreSQL bằng tài khoản postgres'
for ($lan = 1; $lan -le 4; $lan++) {
    $mk = Ra-Chu (Read-Host 'Mật khẩu tài khoản postgres (quên thì để trống và bấm Enter)' -AsSecureString)
    if (-not $mk) { Dat-Lai-Mat-Khau-Postgres } else { $env:PGPASSWORD = $mk }
    $thu = Sql 'postgres' 'SELECT 1;'
    if ($maThoat -eq 0) { break }
    Write-Host 'Sai mật khẩu hoặc không kết nối được.' -ForegroundColor Yellow
    if ($lan -eq 4) { Dung $thu }
}

$cauHinh = Doc-Env
$tenCsdl = if ($cauHinh['POSTGRES_DB']) { $cauHinh['POSTGRES_DB'] } else { 'dacn_nhathuoc' }
$tenVaiTro = if ($cauHinh['POSTGRES_USER']) { $cauHinh['POSTGRES_USER'] } else { 'dacn_ung_dung' }
$matKhau = $cauHinh['POSTGRES_PASSWORD']
if (-not $matKhau) {
    $kyTu = [char[]]'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
    $matKhau = -join (1..24 | ForEach-Object { $kyTu | Get-Random })
    Ghi-Env 'POSTGRES_PASSWORD' $matKhau
    Write-Host 'Đã tạo mật khẩu ngẫu nhiên cho CSDL và ghi vào .env.'
}

Buoc "Tài khoản CSDL $tenVaiTro"
$coVaiTro = Sql 'postgres' "SELECT 1 FROM pg_roles WHERE rolname = $(Chuoi-Sql $tenVaiTro);"
if ($coVaiTro -eq '1') {
    $ra = Sql 'postgres' "ALTER ROLE $(Ten-Sql $tenVaiTro) WITH LOGIN PASSWORD $(Chuoi-Sql $matKhau);"
    Write-Host 'Đã có; đặt lại mật khẩu cho khớp .env.'
} else {
    $ra = Sql 'postgres' "CREATE ROLE $(Ten-Sql $tenVaiTro) LOGIN PASSWORD $(Chuoi-Sql $matKhau);"
    Write-Host 'Đã tạo mới.'
}
if ($maThoat -ne 0) { Dung $ra }

Buoc "CSDL $tenCsdl"
$coCsdl = Sql 'postgres' "SELECT 1 FROM pg_database WHERE datname = $(Chuoi-Sql $tenCsdl);"
if ($coCsdl -eq '1') {
    Write-Host 'Đã có, giữ nguyên dữ liệu.'
} else {
    $ra = Sql 'postgres' ("CREATE DATABASE $(Ten-Sql $tenCsdl) OWNER $(Ten-Sql $tenVaiTro) " +
        "ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C' TEMPLATE template0;")
    if ($maThoat -ne 0) { Dung $ra }
    Write-Host 'Đã tạo mới.'
}

Buoc 'PostGIS'
$coPostgis = Sql $tenCsdl "SELECT 1 FROM pg_extension WHERE extname = 'postgis';"
if ($coPostgis -ne '1') {
    $sanCo = Sql 'postgres' "SELECT 1 FROM pg_available_extensions WHERE name = 'postgis';"
    if ($sanCo -ne '1') {
        if (-not (Test-Path $boPostgis)) { Dung "PostgreSQL chưa có PostGIS và không thấy bộ cài ở $boPostgis." }
        Write-Host 'Chép PostGIS vào PostgreSQL 18 (chỉ thêm tệp còn thiếu)...'
        foreach ($muc in 'bin', 'lib', 'share', 'gdal-data') {
            $nguon = Join-Path $boPostgis $muc
            if (Test-Path $nguon) {
                robocopy $nguon (Join-Path $pg $muc) /E /XC /XN /XO /NFL /NDL /NJH /NJS /NP | Out-Null
                if ($LASTEXITCODE -ge 8) { Dung "Chép $muc thất bại (robocopy $LASTEXITCODE)." }
            }
        }
    }
    $ra = Sql $tenCsdl 'CREATE EXTENSION IF NOT EXISTS postgis;'
    if ($maThoat -ne 0) { Dung $ra }
}
Write-Host ('PostGIS ' + (Sql $tenCsdl 'SELECT extversion FROM pg_extension WHERE extname = ''postgis'';'))
Remove-Item Env:PGPASSWORD

Buoc 'Cập nhật .env'
Ghi-Env 'POSTGRES_HOST' '127.0.0.1'
Ghi-Env 'POSTGRES_PORT' '5432'
Write-Host 'POSTGRES_HOST=127.0.0.1, POSTGRES_PORT=5432'

Buoc 'Redis'
$redisChay = Get-NetTCPConnection -State Listen -LocalPort 6379 -ErrorAction SilentlyContinue
if ($redisChay) {
    Write-Host 'Đang chạy ở cổng 6379.'
} elseif (Test-Path $redis) {
    Start-Process $redis -ArgumentList '--bind', '127.0.0.1', '--port', '6379', '--save', '""', '--appendonly', 'no' -WindowStyle Minimized
    Write-Host 'Đã bật Redis trong cửa sổ thu nhỏ (cần cho trò chuyện trực tuyến).'
} else {
    Write-Host 'Không thấy redis-server.exe; web vẫn chạy, riêng trò chuyện cần Redis.' -ForegroundColor Yellow
}

Buoc 'Migrate'
& $python manage.py migrate
if ($LASTEXITCODE -ne 0) { Dung 'migrate thất bại.' }

Buoc 'Dữ liệu chạy thử'
$kiemTra = 'from ung_dung.danh_muc.models import NhaCungCap as N; from ung_dung.tai_khoan.models import TaiKhoan as T; ' +
    'q = T.objects.filter(la_quan_tri_he_thong=True, dang_hoat_dong=True).order_by("pk").first(); ' +
    'print(int(N.objects.exists()), q.ten_dang_nhap if q else "")'
function Trang-Thai {
    $dong = & $python manage.py shell -c $kiemTra | Select-Object -Last 1
    if ($LASTEXITCODE -ne 0 -or -not $dong) { Dung 'Không đọc được dữ liệu sau migrate.' }
    @($dong.Trim().Split(' '))
}
$trangThai = Trang-Thai
if ($trangThai[0] -ne '1') {
    $quanTri = if ($trangThai.Count -gt 1) { $trangThai[1] } else { '' }
    if (-not $quanTri) {
        Write-Host 'Tạo tài khoản quản trị chuỗi để đăng nhập khu quản lý:'
        & $python manage.py createsuperuser
        if ($LASTEXITCODE -ne 0) { Dung 'createsuperuser thất bại.' }
        $sau = Trang-Thai
        $quanTri = if ($sau.Count -gt 1) { $sau[1] } else { '' }
        if (-not $quanTri) { Dung 'Chưa có tài khoản quản trị.' }
    }
    Write-Host "Sinh chi nhánh, nhà cung cấp và tài khoản mẫu (quản trị: $quanTri)."
    Write-Host 'Mật khẩu nhập tiếp theo dùng chung cho mp_quan_ly, mp_nhan_vien, mp_khach...'
    & $python manage.py tao_du_lieu_mo_phong --quan-tri $quanTri --kem-tai-khoan
    if ($LASTEXITCODE -ne 0) { Dung 'tao_du_lieu_mo_phong thất bại.' }
} else {
    Write-Host 'Đã có dữ liệu, bỏ qua bước sinh dữ liệu mô phỏng.'
}

& $python manage.py nap_thuoc_thuc_te
if ($LASTEXITCODE -ne 0) { Dung 'nap_thuoc_thuc_te thất bại.' }
& $python manage.py tao_noi_dung_website
if ($LASTEXITCODE -ne 0) { Dung 'tao_noi_dung_website thất bại.' }

Buoc 'Xong'
Write-Host 'Mở web: http://127.0.0.1:8000/  ·  Khu quản lý: http://127.0.0.1:8000/quan-ly/' -ForegroundColor Green
Write-Host 'Đang chạy web. Bấm Ctrl+C để dừng; lần sau chỉ cần: python manage.py runserver 127.0.0.1:8000'
& $python manage.py runserver 127.0.0.1:8000
