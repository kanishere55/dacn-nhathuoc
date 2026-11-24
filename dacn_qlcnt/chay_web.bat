@echo off
chcp 65001 >nul
rem Chay web o cong 8001. Lan dau chay ..\csdl\khoi_tao_csdl_windows.ps1 de tao CSDL va du lieu mau.
cd /d "%~dp0"
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
    echo Không thấy môi trường Python .venv trong thư mục dacn_qlcnt. Tạo theo README trước.
    pause
    exit /b 1
)
set "REDIS=.venv\cong_cu\redis\Redis-8.10.3-Windows-x64-msys2\redis-server.exe"
netstat -ano | findstr /r /c:":6379 .*LISTENING" >nul
if errorlevel 1 (
    if exist "%REDIS%" (
        start "Redis" /min "%REDIS%" --bind 127.0.0.1 --port 6379 --save "" --appendonly no
        echo Đã bật Redis trong cửa sổ thu nhỏ - cần cho trò chuyện.
    ) else (
        echo Không thấy redis-server.exe: web vẫn chạy, riêng trò chuyện cần Redis.
    )
)
echo.
echo Web đang chạy. Mở trình duyệt:
echo   Website khách : http://127.0.0.1:8001/
echo   Khu quản lý   : http://127.0.0.1:8001/quan-ly/
echo Đóng cửa sổ này hoặc bấm Ctrl+C để tắt web.
echo.
"%PY%" manage.py runserver 127.0.0.1:8001
pause
