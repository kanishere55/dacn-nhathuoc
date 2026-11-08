(() => {
  const khung = document.querySelector('[data-webgis]');
  const form = khung.querySelector('[data-tim-kiem]');
  const bao = khung.querySelector('[data-thong-bao]');
  const baoViTri = khung.querySelector('[data-vi-tri]');
  const baoDuong = khung.querySelector('[data-lo-trinh]');
  const ketQua = khung.querySelector('[data-ket-qua]');
  const danhMuc = new Map(Array.from(form.querySelectorAll('[data-goi-y] option'), muc => [muc.value, muc.dataset]));
  const banDo = window.taoBanDoNhaThuoc(khung.querySelector('[data-ban-do]'));

  const diem = L.layerGroup().addTo(banDo);
  const diemDau = L.circleMarker([0, 0], {
    radius: 8, color: '#245ba4', fillOpacity: 0.8, interactive: false,
  });
  let viTri = null;
  let lopDuong;
  let boTim;
  let boDuong;
  let lanChonViTri = 0;

  function xoaDuong() {
    boDuong?.abort();
    boDuong = null;
    lopDuong?.remove();
    lopDuong = null;
    baoDuong.textContent = 'Chọn một chi nhánh trong kết quả để xem đường đi.';
  }

  function xoaKetQua() {
    boTim?.abort();
    boTim = null;
    xoaDuong();
    diem.clearLayers();
    ketQua.replaceChildren();
  }

  function chonViTri(diemChon, nguon) {
    lanChonViTri++;
    viTri = diemChon;
    xoaKetQua();
    diemDau.setLatLng(viTri).addTo(banDo);
    baoViTri.textContent = 'Đã chọn điểm xuất phát ' + nguon + '.';
    bao.textContent = 'Bấm Tìm chi nhánh để cập nhật kết quả.';
  }

  banDo.on('click', suKien => chonViTri(suKien.latlng, 'trên bản đồ'));
  khung.querySelector('[data-tam-ban-do]').addEventListener('click', () => {
    chonViTri(banDo.getCenter(), 'tại tâm bản đồ');
  });
  khung.querySelector('[data-dinh-vi]').addEventListener('click', () => {
    if (!navigator.geolocation) {
      baoViTri.textContent = 'Trình duyệt không hỗ trợ định vị. Hãy bấm vào bản đồ.';
      return;
    }
    const lan = ++lanChonViTri;
    baoViTri.textContent = 'Đang lấy vị trí của bạn…';
    navigator.geolocation.getCurrentPosition(
      viTriMoi => {
        if (lan !== lanChonViTri) return;
        const diemChon = L.latLng(viTriMoi.coords.latitude, viTriMoi.coords.longitude);
        chonViTri(diemChon, 'bằng định vị');
        banDo.setView(diemChon, 14);
      },
      () => {
        if (lan === lanChonViTri) baoViTri.textContent = 'Không lấy được vị trí. Hãy bấm vào bản đồ.';
      },
      {timeout: 8000},
    );
  });

  const cacDong = () => Array.from(form.querySelectorAll('[data-dong-thuoc]'));
  const nutThem = form.querySelector('[data-them-thuoc]');
  if (nutThem) {
    const gioiHan = Number(khung.dataset.gioiHan);
    function capNhatNut() {
      const danhSach = cacDong();
      danhSach.forEach(dong => { dong.querySelector('[data-xoa-thuoc]').hidden = danhSach.length === 1; });
      nutThem.disabled = danhSach.length >= gioiHan;
    }
    nutThem.addEventListener('click', () => {
      const dong = cacDong()[0].cloneNode(true);
      const oThuoc = dong.querySelector('[data-thuoc]');
      oThuoc.value = '';
      dong.querySelector('[data-so-luong]').value = '1';
      dong.querySelector('[data-don-vi]').textContent = '';
      form.querySelector('[data-nhu-cau]').append(dong);
      capNhatNut();
      oThuoc.focus();
    });
    form.addEventListener('click', suKien => {
      const nutXoa = suKien.target.closest('[data-xoa-thuoc]');
      if (nutXoa && cacDong().length > 1) {
        nutXoa.closest('[data-dong-thuoc]').remove();
        capNhatNut();
        nutThem.focus();
      }
    });
    form.addEventListener('input', suKien => {
      if (!suKien.target.matches('[data-thuoc]')) return;
      const oThuoc = suKien.target;
      oThuoc.setCustomValidity('');
      const donVi = danhMuc.get(oThuoc.value)?.donVi;
      oThuoc.closest('[data-dong-thuoc]').querySelector('[data-don-vi]').textContent = donVi ? ' · ' + donVi : '';
    });
    capNhatNut();
  }

  function layNhuCau() {
    const nhuCau = [];
    for (const dong of cacDong()) {
      const oThuoc = dong.querySelector('[data-thuoc]');
      const thuoc = oThuoc ? danhMuc.get(oThuoc.value) : dong.dataset;
      if (!thuoc) {
        oThuoc.setCustomValidity('Chọn thuốc trong danh sách gợi ý.');
        oThuoc.reportValidity();
        return [];
      }
      const soLuong = dong.querySelector('input[data-so-luong]')?.value ?? dong.dataset.soLuong;
      nhuCau.push({id_thuoc: Number(thuoc.idThuoc), so_luong: Number(soLuong)});
    }
    return nhuCau;
  }

  async function timDuong(chiNhanh, diemXuatPhat, luotTim) {
    if (boTim !== luotTim) return;
    xoaDuong();
    const luot = new AbortController();
    boDuong = luot;
    const henGio = setTimeout(() => luot.abort(), 12000);
    baoDuong.textContent = 'Đang lấy lộ trình…';
    try {
      const dau = [diemXuatPhat.lng, diemXuatPhat.lat].join(',');
      const cuoi = [chiNhanh.kinh_do, chiNhanh.vi_do].join(',');
      const url = khung.dataset.osrm.replace(/\/$/, '') + '/route/v1/driving/' + dau + ';' + cuoi + '?overview=full&geometries=geojson';
      const phanHoi = await fetch(url, {signal: luot.signal});
      const duLieu = await phanHoi.json();
      if (boDuong !== luot) return;
      if (!phanHoi.ok || duLieu.code !== 'Ok' || !duLieu.routes?.length) throw new Error();
      const duong = duLieu.routes[0];
      lopDuong = L.geoJSON(duong.geometry, {style: {color: '#116b54', weight: 5}}).addTo(banDo);
      banDo.fitBounds(lopDuong.getBounds(), {padding: [22, 22], maxZoom: 16});
      baoDuong.textContent = 'Lộ trình đến ' + chiNhanh.ten_chi_nhanh + ' · ' + (duong.distance / 1000).toLocaleString('vi-VN', {maximumFractionDigits: 1}) + ' km.';
    } catch {
      if (boDuong === luot) baoDuong.textContent = 'Chưa lấy được lộ trình. Vị trí chi nhánh vẫn hiển thị trên bản đồ.';
    } finally {
      clearTimeout(henGio);
    }
  }

  function hienChiNhanh(chiNhanh, diemXuatPhat, luotTim) {
    const ten = document.createElement('h3');
    const link = document.createElement('a');
    link.href = chiNhanh.duong_dan;
    link.textContent = chiNhanh.ten_chi_nhanh;
    ten.append(link);
    const diaChi = document.createElement('p');
    diaChi.textContent = chiNhanh.dia_chi + ' · ' + (chiNhanh.khoang_cach_met / 1000).toLocaleString('vi-VN', {maximumFractionDigits: 2}) + ' km theo đường thẳng';
    const moc = L.marker([chiNhanh.vi_do, chiNhanh.kinh_do], {alt: chiNhanh.ten_chi_nhanh})
      .bindPopup(link.cloneNode(true)).addTo(diem);
    moc.on('click', () => timDuong(chiNhanh, diemXuatPhat, luotTim));
    const nutDuong = document.createElement('button');
    nutDuong.type = 'button';
    nutDuong.className = 'nut nut-phu';
    nutDuong.textContent = 'Xem đường';
    nutDuong.addEventListener('click', () => {
      moc.openPopup();
      timDuong(chiNhanh, diemXuatPhat, luotTim);
    });
    const tacVu = document.createElement('div');
    tacVu.className = 'nut-vi-tri';
    tacVu.append(nutDuong);
    if (khung.dataset.urlGio) {
      const linkGio = document.createElement('a');
      linkGio.className = 'nut';
      linkGio.href = khung.dataset.urlGio + '?' + new URLSearchParams({hinh_thuc_nhan: 'nhan_tai_quay', chi_nhanh: chiNhanh.id_chi_nhanh});
      linkGio.textContent = 'Chọn nhận tại đây';
      tacVu.append(linkGio);
    }
    const the = document.createElement('article');
    the.className = 'the-khach the-ket-qua-ban-do';
    the.append(ten, diaChi, tacVu);
    ketQua.append(the);
  }

  form.addEventListener('submit', async suKien => {
    suKien.preventDefault();
    if (!viTri) {
      baoViTri.textContent = 'Hãy chọn điểm xuất phát trước khi tìm kiếm.';
      return;
    }
    const nhuCau = layNhuCau();
    if (!nhuCau.length) return;
    xoaKetQua();
    const luot = new AbortController();
    boTim = luot;
    const diemXuatPhat = viTri.wrap();
    bao.textContent = 'Đang kiểm tra tồn tại các chi nhánh…';
    try {
      const phanHoi = await fetch(khung.dataset.urlTim, {
        method: 'POST',
        signal: luot.signal,
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': form.elements.csrfmiddlewaretoken.value},
        body: JSON.stringify({
          kinh_do: diemXuatPhat.lng,
          vi_do: diemXuatPhat.lat,
          ban_kinh_met: Number(form.elements.ban_kinh_met.value),
          cac_thuoc: nhuCau,
        }),
      });
      if (!phanHoi.ok) throw new Error();
      const {ket_qua: danhSach} = await phanHoi.json();
      if (boTim !== luot) return;
      bao.textContent = danhSach.length
        ? 'Tìm thấy ' + danhSach.length + ' chi nhánh còn đủ thuốc.'
        : 'Không có chi nhánh nào còn đủ toàn bộ thuốc trong phạm vi đã chọn.';
      danhSach.forEach(cn => hienChiNhanh(cn, diemXuatPhat, luot));
      if (danhSach.length) {
        banDo.fitBounds([viTri, ...danhSach.map(cn => [cn.vi_do, cn.kinh_do])], {
          padding: [24, 24], maxZoom: 15,
        });
      }
    } catch {
      if (boTim === luot) bao.textContent = 'Chưa tìm được chi nhánh. Vui lòng thử lại.';
    }
  });
})();
