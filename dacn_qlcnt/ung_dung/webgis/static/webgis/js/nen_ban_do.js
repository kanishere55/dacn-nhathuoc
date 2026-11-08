window.taoBanDoNhaThuoc = (phanTu, viTri = [10.77, 106.7], mucPhong = 12) => {
  const banDo = L.map(phanTu).setView(viTri, mucPhong);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
    referrerPolicy: 'strict-origin-when-cross-origin',
  }).addTo(banDo);
  return banDo;
};
