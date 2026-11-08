(() => {
  const khung = document.querySelector('[data-webgis]');
  const form = khung.querySelector('form');
  const bao = khung.querySelector('[data-thong-bao]');
  const ketQua = document.querySelector('[data-ket-qua]');
  const banDo = L.map('ban-do').setView([10.77, 106.7], 12);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(banDo);
  const diem = L.layerGroup().addTo(banDo);
  let lopDuong = null;
  let lanTim = 0;
  let lanDuong = 0;
  let boTim;
  let boDuong;

  const csrf = () => form.querySelector('[name=csrfmiddlewaretoken]').value;
  const nhuCau = () => Array.from(form.querySelectorAll('.nhu-cau'), dong => ({
    id_thuoc: Number(dong.querySelector('select').value),
    so_luong: Number(dong.querySelector('input').value),
  }));

  khung.querySelector('[data-them-thuoc]').addEventListener('click', () => {
    if (form.querySelectorAll('.nhu-cau').length >= 30) return;
    const dong = form.querySelector('.nhu-cau').cloneNode(true);
    dong.querySelector('select').value = '';
    dong.querySelector('input').value = 1;
    form.querySelector('[data-nhu-cau]').append(dong);
  });
  form.addEventListener('click', suKien => {
    if (suKien.target.matches('[data-xoa-thuoc]') && form.querySelectorAll('.nhu-cau').length > 1) {
      suKien.target.closest('.nhu-cau').remove();
    }
  });
  khung.querySelector('[data-dinh-vi]').addEventListener('click', () => {
    if (!navigator.geolocation) {
      bao.textContent = 'Trình duyệt không hỗ trợ định vị.';
      return;
    }
    navigator.geolocation.getCurrentPosition(
      viTri => {
        form.elements.kinh_do.value = viTri.coords.longitude;
        form.elements.vi_do.value = viTri.coords.latitude;
        bao.textContent = 'Đã cập nhật vị trí.';
      },
      () => { bao.textContent = 'Không lấy được vị trí. Bạn có thể nhập tọa độ.'; },
      {timeout: 8000},
    );
  });

  async function goiApi(url, duLieu, signal) {
    const phanHoi = await fetch(url, {
      method: 'POST', signal,
      headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf()},
      body: JSON.stringify(duLieu),
    });
    if (phanHoi.status === 403) throw new Error('Cần đăng nhập tài khoản khách hàng.');
    const ketQua = await phanHoi.json();
    if (!phanHoi.ok) throw new Error(ketQua.loi?.join(' ') || 'Thông tin gửi lên chưa hợp lệ.');
    return ketQua;
  }

  function xoaDuong() {
    boDuong?.abort();
    if (lopDuong) banDo.removeLayer(lopDuong);
    lopDuong = null;
  }

  async function chon(chiNhanh, yeuCau, lan) {
    xoaDuong();
    boDuong = new AbortController();
    const phieu = ++lanDuong;
    const boHienTai = boDuong;
    const henGio = setTimeout(() => boHienTai.abort(), 12000);
    bao.textContent = 'Đang lấy lộ trình OSRM…';
    try {
      const dau = [yeuCau.kinh_do, yeuCau.vi_do].join(',');
      const cuoi = [chiNhanh.kinh_do, chiNhanh.vi_do].join(',');
      const url = khung.dataset.osrm + '/route/v1/driving/' + dau + ';' + cuoi + '?overview=full&geometries=geojson';
      const phanHoi = await fetch(url, {signal: boHienTai.signal});
      const ketQua = await phanHoi.json();
      if (lan !== lanTim || phieu !== lanDuong) return;
      if (!phanHoi.ok || ketQua.code !== 'Ok' || !ketQua.routes?.length) throw new Error();
      const duong = ketQua.routes[0];
      lopDuong = L.geoJSON(duong.geometry, {style: {color: '#116b54', weight: 5}}).addTo(banDo);
      banDo.fitBounds(lopDuong.getBounds());
      bao.textContent = 'Lộ trình ' + (duong.distance / 1000).toFixed(1) + ' km.';
    } catch {
      if (lan === lanTim && phieu === lanDuong) {
        bao.textContent = 'Không lấy được đường đi. Vị trí chi nhánh vẫn hiển thị trên bản đồ.';
      }
    } finally {
      clearTimeout(henGio);
    }
  }

  function themChiNhanh(chiNhanh, yeuCau, lan) {
    const ten = document.createElement('h2');
    ten.textContent = chiNhanh.ten_chi_nhanh;
    const diaChi = document.createElement('p');
    diaChi.textContent = chiNhanh.dia_chi + ' · ' + (chiNhanh.khoang_cach_met / 1000).toFixed(2) + ' km';
    const moc = L.marker([chiNhanh.vi_do, chiNhanh.kinh_do]).bindPopup(ten.cloneNode(true)).addTo(diem);
    const xemDuong = () => chon(chiNhanh, yeuCau, lan);
    moc.on('click', xemDuong);
    const nutDuong = document.createElement('button');
    nutDuong.type = 'button';
    nutDuong.className = 'nut nut-phu';
    nutDuong.textContent = 'Xem đường';
    nutDuong.addEventListener('click', xemDuong);
    const dong = document.createElement('article');
    dong.className = 'ket-qua-chi-nhanh';
    dong.append(ten, diaChi, nutDuong);
    if (khung.dataset.urlGiu) {
      const nutGiu = document.createElement('button');
      nutGiu.type = 'button';
      nutGiu.className = 'nut';
      nutGiu.textContent = 'Đặt giữ 24 giờ';
      nutGiu.addEventListener('click', async () => {
        nutGiu.disabled = true;
        try {
          const don = await goiApi(khung.dataset.urlGiu, {
            id_chi_nhanh: chiNhanh.id_chi_nhanh, cac_thuoc: yeuCau.cac_thuoc,
          });
          window.location.assign(don.duong_dan);
        } catch (loi) {
          bao.textContent = loi.message;
          nutGiu.disabled = false;
        }
      });
      dong.append(nutGiu);
    }
    ketQua.append(dong);
  }

  form.addEventListener('submit', async suKien => {
    suKien.preventDefault();
    boTim?.abort();
    boTim = new AbortController();
    const lan = ++lanTim;
    const yeuCau = {
      kinh_do: Number(form.elements.kinh_do.value),
      vi_do: Number(form.elements.vi_do.value),
      ban_kinh_met: Number(form.elements.ban_kinh_met.value),
      cac_thuoc: nhuCau(),
    };
    xoaDuong();
    diem.clearLayers();
    ketQua.replaceChildren();
    bao.textContent = 'Đang tìm chi nhánh…';
    try {
      const ketQuaTim = await goiApi(khung.dataset.urlTim, yeuCau, boTim.signal);
      if (lan !== lanTim) return;
      const danhSach = ketQuaTim.ket_qua;
      bao.textContent = danhSach.length
        ? 'Tìm thấy ' + danhSach.length + ' chi nhánh.'
        : 'Không có chi nhánh trong phạm vi còn đủ toàn bộ thuốc.';
      const viTri = [yeuCau.vi_do, yeuCau.kinh_do];
      L.circleMarker(viTri, {radius: 7, color: '#265ea0'}).bindPopup('Điểm xuất phát').addTo(diem);
      danhSach.forEach(chiNhanh => themChiNhanh(chiNhanh, yeuCau, lan));
      banDo.setView(viTri, 12);
    } catch (loi) {
      if (loi.name !== 'AbortError' && lan === lanTim) bao.textContent = loi.message;
    }
  });
})();
