// Tiện ích bản đồ dùng chung: nền OSM, biểu tượng nhà thuốc, ghim người dùng và lộ trình OSRM.
window.taoBanDoNhaThuoc = (phanTu, viTri = [10.77, 106.7], mucPhong = 12, tuyChon) => {
  const banDo = L.map(phanTu, tuyChon).setView(viTri, mucPhong);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
    referrerPolicy: 'strict-origin-when-cross-origin',
  }).addTo(banDo);
  return banDo;
};

// Ghim hình giọt nước có biểu tượng cửa hàng; vẽ bằng SVG nên không phụ thuộc tệp ảnh của Leaflet.
const CUA_HANG = '<path d="m2 7 4.41-4.41A2 2 0 0 1 7.83 2h8.34a2 2 0 0 1 1.42.59L22 7"/><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><path d="M15 22v-4a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2v4"/><path d="M2 7h20"/><path d="M22 7v3a2 2 0 0 1-2 2a2.7 2.7 0 0 1-1.59-.63.7.7 0 0 0-.82 0A2.7 2.7 0 0 1 16 12a2.7 2.7 0 0 1-1.59-.63.7.7 0 0 0-.82 0A2.7 2.7 0 0 1 12 12a2.7 2.7 0 0 1-1.59-.63.7.7 0 0 0-.82 0A2.7 2.7 0 0 1 8 12a2.7 2.7 0 0 1-1.59-.63.7.7 0 0 0-.82 0A2.7 2.7 0 0 1 4 12a2 2 0 0 1-2-2V7"/>';
window.bieuTuongNhaThuoc = ({ noiBat = false, mo = false } = {}) => L.divIcon({
  className: 'ghim-nha-thuoc' + (noiBat ? ' noi-bat' : '') + (mo ? ' mo' : ''),
  html: `<span class="than-ghim"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${CUA_HANG}</svg></span>`,
  iconSize: [38, 46],
  iconAnchor: [19, 44],
  popupAnchor: [0, -40],
});
window.bieuTuongNguoiDung = (nhan = 'Bạn ở đây') => L.divIcon({
  className: 'ghim-nguoi-dung',
  html: `<span class="cham"></span><span class="nhan">${nhan}</span>`,
  iconSize: [18, 18],
  iconAnchor: [9, 9],
});

// Tốc độ trung bình trong đô thị dùng ước tính thời gian khi OSRM chỉ có hồ sơ ô tô.
const TOC_DO_XE_MAY_KM_GIO = 28;
window.dinhDangKm = (met) => (met / 1000).toLocaleString('vi-VN', { maximumFractionDigits: met < 10000 ? 1 : 0 }) + ' km';
window.dinhDangPhut = (giay) => {
  const phut = Math.max(1, Math.round(giay / 60));
  return phut < 60 ? `${phut} phút` : `${Math.floor(phut / 60)} giờ ${phut % 60} phút`;
};
window.thoiGianTheoPhuongTien = (duong, phuongTien) => {
  return phuongTien === 'xe_may' ? duong.distance / 1000 / TOC_DO_XE_MAY_KM_GIO * 3600 : duong.duration;
};

// Lấy lộ trình đường bộ giữa hai điểm [lat, lng]; trả {geometry, distance, duration} hoặc ném lỗi.
window.layLoTrinh = async (mayChu, tu, den, tinHieu) => {
  const toaDo = [tu, den].map(([lat, lng]) => `${lng},${lat}`).join(';');
  const url = `${mayChu.replace(/\/$/, '')}/route/v1/driving/${toaDo}?overview=full&geometries=geojson`;
  const phanHoi = await fetch(url, {
    signal: tinHieu, credentials: 'omit', referrerPolicy: 'strict-origin-when-cross-origin',
  });
  const duLieu = await phanHoi.json();
  const duong = duLieu.routes?.[0];
  if (!phanHoi.ok || duLieu.code !== 'Ok' || !duong ||
      duong.geometry?.type !== 'LineString' ||
      !Array.isArray(duong.geometry.coordinates) || duong.geometry.coordinates.length < 2 ||
      !Number.isFinite(duong.distance) || duong.distance < 0 ||
      !Number.isFinite(duong.duration) || duong.duration < 0) {
    throw new Error('khong_co_lo_trinh');
  }
  return duong;
};
