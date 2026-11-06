"""Tải tài nguyên giao diện đã khóa phiên bản; không cần Node hoặc CDN khi chạy web."""

import hashlib
import urllib.request
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
NGUON = {
    "htmx/htmx.min.js": "https://unpkg.com/htmx.org@2.0.8/dist/htmx.min.js",
    "htmx/LICENSE": "https://raw.githubusercontent.com/bigskysoftware/htmx/v2.0.8/LICENSE",
    "alpine/alpine.min.js": "https://unpkg.com/alpinejs@3.14.9/dist/cdn.min.js",
    "alpine/LICENSE": "https://raw.githubusercontent.com/alpinejs/alpine/v3.14.9/LICENSE.md",
    "lucide/lucide.min.js": "https://unpkg.com/lucide@0.468.0/dist/umd/lucide.min.js",
    "lucide/LICENSE": "https://raw.githubusercontent.com/lucide-icons/lucide/0.468.0/LICENSE",
    "be_vietnam_pro/BeVietnamPro-Regular.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/bevietnampro/BeVietnamPro-Regular.ttf",
    "be_vietnam_pro/BeVietnamPro-SemiBold.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/bevietnampro/BeVietnamPro-SemiBold.ttf",
    "be_vietnam_pro/BeVietnamPro-Bold.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/bevietnampro/BeVietnamPro-Bold.ttf",
    "be_vietnam_pro/OFL.txt": "https://raw.githubusercontent.com/google/fonts/main/ofl/bevietnampro/OFL.txt",
}
MA_BAM = {
    "htmx/htmx.min.js": "22283ef68cb7545914f0a88a1bdedc7256a703d1d580c1d255217d0a50d31313",
    "htmx/LICENSE": "d3d2456f76414f2456104660ebd65aff1c04cd7966b942bdabd63f3cdb316a38",
    "alpine/alpine.min.js": "3ed1eed252488921df65e363d6715deb04d7f92aaedb9e52199fdf73cb1e0ad3",
    "alpine/LICENSE": "5f05c4925dd3edf049a70b4b403ac0dd43b20f72501d9359911ddd25d5ac657d",
    "lucide/lucide.min.js": "3411692820cb8d47543f69496aa25fd603a358f4498046f41c508a5a3342210e",
    "lucide/LICENSE": "1e7290b35280a048667bbf0ebabac1c7fd52a75300e8b2946ac165715997f2bc",
    "be_vietnam_pro/BeVietnamPro-Regular.ttf": "cd1ef6e9d7db28ad5cdb88a65ccbe693870e60d340b791f349d248342b4fe4c3",
    "be_vietnam_pro/BeVietnamPro-SemiBold.ttf": "bd8e27eb02720b9d91e59e4f10a90878643219f25ce6a8d9a4f06a8a88d3bb71",
    "be_vietnam_pro/BeVietnamPro-Bold.ttf": "7f738fe5c43c8872807b20e2d30d42163618de8a4daf7f48a939adac32c16847",
    "be_vietnam_pro/OFL.txt": "6b7f8f73609a25ea78c891e34cf37b06f8a676b7ea986e941e43b009110f2a85",
}
MA_BAM_TAILWIND = "ad84612696f3be102fa005d4827f0df84c7b4570d31c06865ce5fde0311478af"


def tai(url, dich, ma_bam_mong_doi):
    dich.parent.mkdir(parents=True, exist_ok=True)
    if dich.exists() and hashlib.sha256(dich.read_bytes()).hexdigest() == ma_bam_mong_doi:
        return ma_bam_mong_doi
    with urllib.request.urlopen(url, timeout=90) as phan_hoi:
        noi_dung = phan_hoi.read()
    if hashlib.sha256(noi_dung).hexdigest() != ma_bam_mong_doi:
        raise ValueError(f"Nội dung tải về không khớp SHA-256 đã review: {dich.name}")
    dich.write_bytes(noi_dung)
    return ma_bam_mong_doi


def main():
    muc_luc = [
        "# Thư viện giao diện cục bộ",
        "",
        "Tải bằng `python cong_cu/tai_thu_vien.py`. Không gọi CDN từ trình duyệt.",
        "",
        "| Tệp | Nguồn | SHA-256 |",
        "| --- | --- | --- |",
    ]
    for ten, url in NGUON.items():
        dich = GOC / "static/vendor" / ten
        ma_bam = tai(url, dich, MA_BAM[ten])
        muc_luc.append(f"| `{ten}` | {url} | `{ma_bam}` |")
        print(ten)
    (GOC / "static/vendor/THU_VIEN.md").write_text(
        "\n".join(muc_luc) + "\n", encoding="utf-8", newline="\n"
    )
    tai(
        "https://github.com/tailwindlabs/tailwindcss/releases/download/v4.3.4/tailwindcss-windows-x64.exe",
        GOC / ".venv/cong_cu/tailwindcss.exe",
        MA_BAM_TAILWIND,
    )


if __name__ == "__main__":
    main()
