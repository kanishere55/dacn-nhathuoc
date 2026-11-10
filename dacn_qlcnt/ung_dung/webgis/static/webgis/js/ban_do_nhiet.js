(() => {
  const khung = document.querySelector('[data-khung-nhiet]');
  const banDo = window.taoBanDoNhaThuoc(khung.querySelector('[data-ban-do-nhiet]'));
  const form = khung.querySelector('[data-nhiet]');
  if (!form) return;
  const bao = khung.querySelector('[data-trang-thai]');
  const bang = khung.querySelector('[data-so-lieu]');
  const chiNhanh = L.layerGroup().addTo(banDo);

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
      chiNhanh.clearLayers();
      lopNhiet = L.heatLayer(
        coHang.map(diem => [diem.vi_do, diem.kinh_do, diem.so_luong]),
        {radius: 35, max: max || 1},
      ).addTo(banDo);

      bang.replaceChildren(...cacDiem.map(diem => {
        const dong = document.createElement('li');
        const ten = document.createElement('strong');
        const luong = document.createElement('span');
        const nhan = document.createElement('span');
        ten.textContent = diem.ten_chi_nhanh;
        luong.textContent = diem.so_luong.toLocaleString('vi-VN') + ' ' + donVi.toLocaleLowerCase('vi-VN');
        dong.append(ten, luong);
        nhan.textContent = ten.textContent + ' · ' + luong.textContent;
        L.marker([diem.vi_do, diem.kinh_do], {
          icon: window.bieuTuongNhaThuoc({noiBat: diem.so_luong === 0}), title: diem.ten_chi_nhanh,
        }).bindPopup(nhan).addTo(chiNhanh);
        return dong;
      }));
      if (cacDiem.length) {
        banDo.fitBounds(cacDiem.map(diem => [diem.vi_do, diem.kinh_do]), {padding: [26, 26], maxZoom: 15});
      }
      bao.textContent = max
        ? `Thang nhiệt 0 đến ${max} ${donVi}. Cập nhật ${new Date().toLocaleTimeString('vi-VN')}.`
        : 'Không có tồn khả dụng trong nhóm và đơn vị đã chọn.';
    } catch (loi) {
      if (luot === dangTai && loi.name !== 'AbortError') {
        bao.textContent = 'Không tải được dữ liệu bản đồ nhiệt.';
      }
    }
  });
  form.requestSubmit();
})();
