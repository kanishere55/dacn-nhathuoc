// Ô chọn vị trí trên bản đồ: tìm địa chỉ qua máy chủ (Nominatim), ghim và kéo trên bản đồ.
(() => {
  const TAM_MAC_DINH = [10.7769, 106.7009];

  const docJson = async (duongDan) => {
    const phanHoi = await fetch(duongDan, { headers: { Accept: 'application/json' } });
    const duLieu = await phanHoi.json().catch(() => ({}));
    if (!phanHoi.ok) throw new Error((duLieu.loi || ['Không tìm được địa chỉ.']).join(' '));
    return duLieu;
  };

  const khoiTao = (khung) => {
    const oViDo = khung.querySelector('[name="vi_do"]');
    const oKinhDo = khung.querySelector('[name="kinh_do"]');
    const oDiaChi = document.getElementById(khung.dataset.oDiaChi);
    const oTim = khung.querySelector('[data-tu-khoa]');
    const nutTim = khung.querySelector('[data-tim]');
    const danhSach = khung.querySelector('[data-ket-qua]');
    const trangThai = khung.querySelector('[data-trang-thai]');
    const viDo = parseFloat(oViDo.value);
    const kinhDo = parseFloat(oKinhDo.value);
    const daCo = Number.isFinite(viDo) && Number.isFinite(kinhDo);
    const banDo = window.taoBanDoNhaThuoc(
      khung.querySelector('[data-ban-do]'), daCo ? [viDo, kinhDo] : TAM_MAC_DINH, daCo ? 17 : 12,
    );
    let ghim = null;

    const baoTrangThai = (chu) => { trangThai.textContent = chu; };

    const dienDiaChiTuToaDo = async (lat, lng) => {
      baoTrangThai('Đang tìm địa chỉ gần điểm ghim…');
      try {
        const duLieu = await docJson(`${khung.dataset.urlNguoc}?vi_do=${lat}&kinh_do=${lng}`);
        if (duLieu.dia_chi && oDiaChi && !oDiaChi.value.trim()) oDiaChi.value = duLieu.dia_chi;
        baoTrangThai(duLieu.dia_chi ? `Gần: ${duLieu.dia_chi}` : 'Đã ghim vị trí.');
      } catch (loi) {
        baoTrangThai('Đã ghim vị trí. Hãy tự nhập địa chỉ chi tiết.');
      }
    };

    const datGhim = (lat, lng, hoiDiaChi) => {
      oViDo.value = lat.toFixed(6);
      oKinhDo.value = lng.toFixed(6);
      if (!ghim) {
        const tuyChon = { draggable: true, autoPan: true };
        if (khung.dataset.bieuTuong === 'nha-thuoc') tuyChon.icon = window.bieuTuongNhaThuoc({ noiBat: true });
        ghim = L.marker([lat, lng], tuyChon).addTo(banDo);
        ghim.on('dragend', () => {
          const p = ghim.getLatLng();
          datGhim(p.lat, p.lng, true);
        });
      } else {
        ghim.setLatLng([lat, lng]);
      }
      const oToaDo = khung.querySelector('[data-toa-do]');
      if (oToaDo) oToaDo.textContent = `Tọa độ: ${lat.toFixed(6)}, ${lng.toFixed(6)} (WGS84)`;
      if (hoiDiaChi) dienDiaChiTuToaDo(lat, lng);
    };

    if (daCo) datGhim(viDo, kinhDo, false);
    banDo.on('click', (e) => datGhim(e.latlng.lat, e.latlng.lng, true));

    const tim = async () => {
      const tuKhoa = oTim.value.trim();
      danhSach.replaceChildren();
      if (tuKhoa.length < 3) { baoTrangThai('Nhập ít nhất 3 ký tự để tìm.'); return; }
      nutTim.disabled = true;
      baoTrangThai('Đang tìm…');
      try {
        const { ket_qua: ketQua, gan_dung: ganDung } = await docJson(`${khung.dataset.urlTim}?q=${encodeURIComponent(tuKhoa)}`);
        if (!ketQua.length) baoTrangThai('Không thấy địa chỉ phù hợp. Hãy thử chỉ gõ tên đường, hoặc bấm trực tiếp lên bản đồ.');
        else if (ganDung) baoTrangThai('Chưa thấy đúng số nhà này. Chọn con đường gần đúng bên dưới rồi kéo ghim tới đúng nhà:');
        else if (ketQua.length === 1) baoTrangThai('Tìm thấy 1 kết quả, bấm để ghim:');
        else baoTrangThai(`Chọn một trong ${ketQua.length} kết quả:`);
        ketQua.forEach((muc) => {
          const nut = document.createElement('button');
          nut.type = 'button';
          nut.textContent = muc.dia_chi;
          nut.addEventListener('click', () => {
            datGhim(muc.vi_do, muc.kinh_do, false);
            banDo.setView([muc.vi_do, muc.kinh_do], 17);
            // Kết quả gần đúng chỉ là con đường: giữ địa chỉ người dùng đã gõ (có số nhà).
            if (oDiaChi) oDiaChi.value = ganDung ? (oDiaChi.value.trim() || tuKhoa) : muc.dia_chi;
            danhSach.replaceChildren();
            baoTrangThai(ganDung ? 'Đã ghim theo tên đường. Kéo ghim tới đúng nhà và kiểm tra lại ô Địa chỉ.' : 'Đã ghim. Có thể kéo ghim tới đúng cổng nhà.');
          });
          danhSach.append(nut);
        });
      } catch (loi) {
        baoTrangThai(loi.message);
      } finally {
        nutTim.disabled = false;
      }
    };

    nutTim.addEventListener('click', tim);
    oTim.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); tim(); }
    });
    khung.querySelector('[data-dinh-vi]')?.addEventListener('click', () => {
      if (!navigator.geolocation) { baoTrangThai('Trình duyệt không hỗ trợ định vị.'); return; }
      baoTrangThai('Đang lấy vị trí hiện tại…');
      navigator.geolocation.getCurrentPosition(
        ({ coords }) => {
          banDo.setView([coords.latitude, coords.longitude], 17);
          datGhim(coords.latitude, coords.longitude, true);
        },
        () => baoTrangThai('Không lấy được vị trí. Hãy cho phép định vị hoặc tìm theo địa chỉ.'),
        { enableHighAccuracy: true, timeout: 10000 },
      );
    });
  };

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-chon-vi-tri]').forEach(khoiTao);
  });
})();
