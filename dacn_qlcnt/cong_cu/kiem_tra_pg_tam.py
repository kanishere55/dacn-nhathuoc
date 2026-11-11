"""Chạy toàn bộ kiểm tra bằng cluster PostgreSQL/PostGIS riêng ở thư mục tạm ngoài project."""

import argparse
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]


def chay(lenh, moi_truong):
    # pg_ctl có tiến trình con giữ stdout nên không dùng PIPE khi khởi động server.
    with tempfile.TemporaryFile() as dau_ra:
        ket_qua = subprocess.run(
            [str(muc) for muc in lenh],
            cwd=GOC,
            env=moi_truong,
            stdout=dau_ra,
            stderr=subprocess.STDOUT,
            timeout=900,  # bộ test đầy đủ đã khoảng 280 giây, 300 giây dễ bị cắt khi máy bận
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        dau_ra.seek(0)
        print(dau_ra.read().decode("utf-8", errors="replace"), end="", flush=True)
    if ket_qua.returncode:
        raise subprocess.CalledProcessError(ket_qua.returncode, lenh)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    tham_so = argparse.ArgumentParser(description=__doc__)
    tham_so.add_argument(
        "--pg-bin", type=Path, required=True, help="Thư mục bin của PostgreSQL có PostGIS."
    )
    tham_so.add_argument(
        "--test",
        nargs="*",
        default=[],
        help="Giới hạn nhãn test khi phát triển; bỏ trống để chạy toàn bộ.",
    )
    tham_so.add_argument(
        "--salesdaily",
        type=Path,
        help="Nạp và chạy thử đủ năm mô hình với CSV nguồn ngoài project.",
    )
    dau_vao = tham_so.parse_args()
    pg_bin = dau_vao.pg_bin.resolve()
    hau_to = ".exe" if os.name == "nt" else ""
    for ten in ("initdb", "pg_ctl", "psql"):
        if not (pg_bin / (ten + hau_to)).is_file():
            tham_so.error(f"Không tìm thấy {ten} trong --pg-bin.")
    if os.name == "nt":
        cac_gdal = sorted(pg_bin.glob("libgdal-*.dll"))
        if not cac_gdal or not (pg_bin / "libgeos_c.dll").is_file():
            tham_so.error("Cần GDAL và GEOS của PostGIS trong --pg-bin.")

    thu_muc_tam = Path(tempfile.mkdtemp(prefix="dacn_kiem_tra_")).resolve()
    du_lieu = thu_muc_tam / "cluster"
    tep_mat_khau = thu_muc_tam / "mat_khau_khoi_tao"
    mat_khau = secrets.token_urlsafe(32)
    tep_mat_khau.write_text(mat_khau, encoding="ascii")
    with socket.socket() as cong_tam:
        cong_tam.bind(("127.0.0.1", 0))
        cong = cong_tam.getsockname()[1]
    moi_truong = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        "PGCLIENTENCODING": "UTF8",
        "PGPASSWORD": mat_khau,
        "POSTGRES_DB": "dacn_kiem_tra",
        "POSTGRES_USER": "kiem_tra_dacn",
        "POSTGRES_PASSWORD": mat_khau,
        "POSTGRES_HOST": "127.0.0.1",
        "POSTGRES_PORT": str(cong),
        "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
        "DJANGO_DEBUG": "False",
        "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1,testserver",
        "DJANGO_SETTINGS_MODULE": "cau_hinh.settings",
        "PATH": str(pg_bin) + os.pathsep + os.environ.get("PATH", ""),
    }
    if os.name == "nt":
        moi_truong["GDAL_LIBRARY_PATH"] = str(cac_gdal[0])
        moi_truong["GEOS_LIBRARY_PATH"] = str(pg_bin / "libgeos_c.dll")
        moi_truong["GDAL_DATA"] = str(pg_bin.parent / "gdal-data")

    da_khoi_dong = False
    try:
        chay(
            [
                pg_bin / f"initdb{hau_to}",
                "-D",
                du_lieu,
                "-U",
                "kiem_tra_dacn",
                "--encoding=UTF8",
                "--locale=C",
                "--auth=scram-sha-256",
                "--pwfile",
                tep_mat_khau,
            ],
            moi_truong,
        )
        chay(
            [
                pg_bin / f"pg_ctl{hau_to}",
                "-D",
                du_lieu,
                "-l",
                thu_muc_tam / "postgres.log",
                "-o",
                f"-h 127.0.0.1 -p {cong}",
                "-w",
                "start",
            ],
            moi_truong,
        )
        da_khoi_dong = True
        psql = [
            pg_bin / f"psql{hau_to}",
            "-X",
            "-h",
            "127.0.0.1",
            "-p",
            str(cong),
            "-U",
            "kiem_tra_dacn",
            "-v",
            "ON_ERROR_STOP=1",
        ]
        chay(
            [
                *psql,
                "-d",
                "postgres",
                "-c",
                "CREATE DATABASE dacn_kiem_tra ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C' TEMPLATE template0;",
            ],
            moi_truong,
        )
        chay(
            [
                *psql,
                "-d",
                "dacn_kiem_tra",
                "-c",
                "CREATE EXTENSION postgis; SELECT version(), postgis_full_version();",
            ],
            moi_truong,
        )
        for lenh in (
            ["check"],
            ["kiem_tra_luu_tru"],
            ["makemigrations", "--check", "--dry-run"],
            ["migrate", "--noinput"],
            ["kiem_tra_csdl"],
            ["test", *dau_vao.test, "--verbosity", "1", "--noinput"],
            ["migrate", "tai_khoan", "zero", "--noinput"],
            ["migrate", "chung", "zero", "--noinput"],
            ["migrate", "--noinput"],
            ["kiem_tra_csdl"],
        ):
            print("\n> manage.py " + " ".join(lenh), flush=True)
            chay([sys.executable, GOC / "manage.py", *lenh], moi_truong)
        if dau_vao.salesdaily:
            for lenh in (["nap_pharma_sales", str(dau_vao.salesdaily.resolve())], ["chay_du_bao"]):
                print("\n> manage.py " + " ".join(lenh), flush=True)
                chay([sys.executable, GOC / "manage.py", *lenh], moi_truong)
            chay(
                [
                    *psql,
                    "-d",
                    "dacn_kiem_tra",
                    "-c",
                    "SELECT count(*) AS so_ket_qua, count(*) FILTER (WHERE duoc_chon) AS so_nhom_da_chon FROM ket_qua_mo_hinh;",
                ],
                moi_truong,
            )
        chay(
            [
                *psql,
                "-d",
                "dacn_kiem_tra",
                "-c",
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;",
            ],
            moi_truong,
        )
        print(
            "\nĐẠT: kiểm tra cấu hình, lưu trữ, migrations, tests và đảo/áp dụng lại migration.",
            flush=True,
        )
        return 0
    finally:
        co_the_xoa = True
        if da_khoi_dong or (du_lieu / "postmaster.pid").exists():
            try:
                chay(
                    [pg_bin / f"pg_ctl{hau_to}", "-D", du_lieu, "-m", "fast", "-w", "stop"],
                    moi_truong,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                co_the_xoa = False
                print(f"Không xóa thư mục vì chưa xác nhận server đã dừng: {thu_muc_tam}")
        if (
            co_the_xoa
            and thu_muc_tam.parent == Path(tempfile.gettempdir()).resolve()
            and thu_muc_tam.name.startswith("dacn_kiem_tra_")
        ):
            shutil.rmtree(thu_muc_tam)


if __name__ == "__main__":
    raise SystemExit(main())
