(() => {
  const form = document.querySelector('[data-nhiet]');
  const bao = form.querySelector('[data-trang-thai]');
  const bang = document.querySelector('[data-so-lieu]');
  const banDo = L.map('ban-do').setView([10.77, 106.7], 12);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(banDo);

  let lopNhiet;
  let dangTai;
  form.addEventListener('submit', async suKien => {
    suKien.preventDefault();
    dangTai?.abort();
    const luot = new AbortController();
    dangTai = luot;
    const donVi = form.elements.don_vi_tinh.selectedOptions[0]?.text;
    const thamSo = new URLSearchParams(new FormData(form));
    bao.textContent = 'Đang cập nhật…';

    try {
      const phanHoi = await fetch(form.dataset.url + '?' + thamSo, {signal: luot.signal});
      if (!phanHoi.ok) throw new Error();
      const {ket_qua: cacDiem} = await phanHoi.json();
      if (luot !== dangTai) return;

      const max = cacDiem.reduce((lonNhat, diem) => Math.max(lonNhat, diem.so_luong), 0);
      const coHang = cacDiem.filter(diem => diem.so_luong > 0);
      lopNhiet?.remove();
      lopNhiet = L.heatLayer(
        coHang.map(diem => [diem.vi_do, diem.kinh_do, diem.so_luong]),
        {radius: 35, max: max || 1},
      ).addTo(banDo);

      bang.replaceChildren(...cacDiem.map(diem => {
        const dong = document.createElement('p');
        dong.textContent = `${diem.ten_chi_nhanh}: ${diem.so_luong} ${donVi}`;
        return dong;
      }));
      bao.textContent = max
        ? `Thang nhiệt 0 đến ${max} ${donVi}. Cập nhật ${new Date().toLocaleTimeString('vi-VN')}.`
        : 'Không có tồn khả dụng trong nhóm và đơn vị đã chọn.';
    } catch (loi) {
      if (luot === dangTai && loi.name !== 'AbortError') {
        bao.textContent = 'Không tải được dữ liệu bản đồ nhiệt.';
      }
    }
  });
})();
