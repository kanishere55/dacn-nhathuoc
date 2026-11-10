(() => {
  // Cùng thang màu với dải chú giải .chu-giai-nhiet trong phan_tich.css.
  const THANG_MAU = {0.4: '#3b4cc0', 0.6: '#3ba8c4', 0.7: '#7fd36b', 0.8: '#f2d43a', 1: '#e8452c'};
  const khung = document.querySelector('[data-khung-nhiet]');
  const banDo = window.taoBanDoNhaThuoc(khung.querySelector('[data-ban-do-nhiet]'));
  const form = khung.querySelector('[data-nhiet]');
  if (!form) return;
  const bao = khung.querySelector('[data-trang-thai]');
  const bang = khung.querySelector('[data-so-lieu]');
  const chuGiai = khung.querySelector('[data-chu-giai]');
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
        // Leaflet.heat giảm cường độ theo 2^(maxZoom − zoom); mặc định maxZoom của bản đồ là 19
        // nên ở mức xem cả thành phố vệt nhiệt gần như mất. Chốt maxZoom thấp để giữ đúng thang.
        {radius: 40, blur: 28, max: max || 1, maxZoom: 10, gradient: THANG_MAU},
      ).addTo(banDo);

      const tong = cacDiem.reduce((cong, diem) => cong + diem.so_luong, 0);
      const donViThuong = donVi.toLocaleLowerCase('vi-VN');
      // Sắp chi nhánh nhiều hàng lên trước; thanh ngang cho thấy tỷ lệ so với chi nhánh cao nhất.
      const xep = [...cacDiem].sort((a, b) => b.so_luong - a.so_luong);
      bang.replaceChildren(...xep.map(diem => {
        const dong = document.createElement('li');
        dong.className = 'co-thanh';
        const ten = document.createElement('strong');
        const luong = document.createElement('span');
        const thanh = document.createElement('span');
        const phan = document.createElement('span');
        ten.textContent = diem.ten_chi_nhanh;
        const tyLe = tong ? Math.round((diem.so_luong / tong) * 100) : 0;
        luong.textContent = `${diem.so_luong.toLocaleString('vi-VN')} ${donViThuong} · ${tyLe}%`;
        thanh.className = 'thanh-ty-le';
        phan.style.width = `${max ? (diem.so_luong / max) * 100 : 0}%`;
        if (diem.so_luong === 0) phan.className = 'het-hang';
        thanh.append(phan);
        dong.append(ten, luong, thanh);
        L.marker([diem.vi_do, diem.kinh_do], {
          icon: window.bieuTuongNhaThuoc({noiBat: diem.so_luong === 0}), title: diem.ten_chi_nhanh,
        }).bindPopup(Object.assign(document.createElement('span'), {
          textContent: `${diem.ten_chi_nhanh} · ${luong.textContent}`,
        })).addTo(chiNhanh);
        return dong;
      }));
      chuGiai.hidden = !max;
      chuGiai.querySelector('[data-max]').textContent = `${max.toLocaleString('vi-VN')} ${donViThuong}`;
      if (cacDiem.length) {
        banDo.fitBounds(cacDiem.map(diem => [diem.vi_do, diem.kinh_do]), {padding: [26, 26], maxZoom: 15});
      }
      bao.textContent = max
        ? `Toàn chuỗi còn ${tong.toLocaleString('vi-VN')} ${donViThuong} khả dụng. Cập nhật ${new Date().toLocaleTimeString('vi-VN')}.`
        : 'Không có tồn khả dụng trong nhóm và đơn vị đã chọn.';
    } catch (loi) {
      if (luot === dangTai && loi.name !== 'AbortError') {
        bao.textContent = 'Không tải được dữ liệu bản đồ nhiệt.';
      }
    }
  });
  form.requestSubmit();
})();
