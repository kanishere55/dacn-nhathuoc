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

// Nội dung popup một nhà thuốc: ảnh trượt (nút ‹ ›), tên, trạng thái mở cửa, địa chỉ, điện thoại và các nút
// trang truyền vào. `cn` theo du_lieu_ban_do_chi_nhanh (danh_muc/selectors.py).
window.noiDungPopupNhaThuoc = (cn, tacVu = []) => {
  const tao = (the, lop, chu) => {
    const el = document.createElement(the);
    if (lop) el.className = lop;
    if (chu !== undefined) el.textContent = chu;
    return el;
  };
  const khung = tao('div', 'noi-dung-popup');
  const cacAnh = cn.cac_anh?.length ? cn.cac_anh : (cn.anh ? [cn.anh] : []);
  if (cacAnh.length) {
    const boAnh = tao('div', 'bo-anh bo-anh-phu-kin bo-anh-popup');
    boAnh.dataset.boAnh = '';
    const chinh = tao('div', 'splide bo-anh-chinh');
    chinh.setAttribute('aria-label', 'Ảnh ' + cn.ten_chi_nhanh);
    const ray = tao('div', 'splide__track');
    const dsAnh = tao('ul', 'splide__list');
    cacAnh.forEach((url, so) => {
      const o = tao('li', 'splide__slide');
      const img = tao('img');
      img.src = url;
      img.alt = `${cn.ten_chi_nhanh} – ảnh ${so + 1}`;
      if (so) img.loading = 'lazy';
      const khungAnh = tao('div', 'khung-anh-mo');
      khungAnh.append(img);
      o.append(khungAnh);
      dsAnh.append(o);
    });
    ray.append(dsAnh);
    chinh.append(ray);
    if (cacAnh.length > 1) {
      const dem = tao('span', 'dem-anh');
      dem.setAttribute('aria-hidden', 'true');
      const so = tao('span', '', '1');
      so.dataset.soAnh = '';
      dem.append(so, ` / ${cacAnh.length}`);
      chinh.append(dem);
    }
    boAnh.append(chinh);
    khung.append(boAnh);
  }
  const than = tao('div', 'than-popup');
  const ten = tao('a', 'ten-popup', cn.ten_chi_nhanh);
  ten.href = cn.duong_dan;
  const trangThai = tao('p', 'trang-thai-popup');
  trangThai.append(
    tao('span', cn.dang_mo_cua ? 'nhan-dang-mo' : 'nhan-da-dong', cn.dang_mo_cua ? 'Đang mở cửa' : 'Đã đóng cửa'),
    tao('span', '', `${cn.gio_mo_cua}–${cn.gio_dong_cua}`),
  );
  if (cn.diem_sao) trangThai.append(tao('span', 'sao-popup', `★ ${cn.diem_sao} (${cn.so_danh_gia})`));
  const dong = (bieuTuong, noiDung) => {
    const p = tao('p', 'dong-popup');
    const i = tao('i');
    i.dataset.lucide = bieuTuong;
    i.setAttribute('aria-hidden', 'true');
    p.append(i, noiDung);
    return p;
  };
  than.append(ten, trangThai, dong('map-pin', cn.dia_chi));
  if (cn.so_dien_thoai) {
    const tel = tao('a', '', cn.so_dien_thoai);
    tel.href = 'tel:' + cn.so_dien_thoai;
    than.append(dong('phone', tel));
  }
  if (cn.khoang_cach_met !== null && cn.khoang_cach_met !== undefined) {
    than.append(dong('navigation', `Cách bạn ${window.dinhDangKm(cn.khoang_cach_met)} (đường chim bay)`));
  }
  if (tacVu.length) {
    const hang = tao('div', 'tac-vu-popup');
    hang.append(...tacVu);
    than.append(hang);
  }
  khung.append(than);
  return khung;
};

// Popup nhà thuốc trên một bản đồ: rê chuột vào ghim thì xem nhanh, rời chuột thì ẩn; bấm (hoặc Enter) thì
// popup được ghim lại, có nút X ở góc để đóng. Mỗi bản đồ ghim tối đa một popup.
// Dùng: const ganPopup = taoPopupNhaThuoc(banDo); const p = ganPopup(moc, () => noiDung); p.mo(true).
window.taoPopupNhaThuoc = (banDo) => {
  let dangGhim = null;
  return (moc, taoNoiDung) => {
    let popup = null;
    let hen = 0;
    const giu = () => clearTimeout(hen);
    const an = () => {
      if (popup && popup !== dangGhim) popup.remove();
    };
    const anSau = () => {
      giu();
      hen = setTimeout(() => {
        if (!popup?.getElement()?.matches(':hover')) an();
      }, 200);
    };
    const tao = () => {
      if (popup) return;
      popup = L.popup({
        className: 'popup-nha-thuoc', minWidth: 272, maxWidth: 272, offset: [0, -34], autoPan: false,
      }).setLatLng(moc.getLatLng()).setContent(taoNoiDung());
      popup.on('add', () => {
        const el = popup.getElement();
        el.classList.toggle('da-ghim', popup === dangGhim);
        if (!el.dataset.daGan) {
          el.dataset.daGan = '1';
          el.addEventListener('mouseenter', giu);
          el.addEventListener('mouseleave', anSau);
          el.querySelector('.leaflet-popup-close-button')?.setAttribute('aria-label', 'Đóng thông tin nhà thuốc');
        }
        if (el.querySelector('i[data-lucide]')) window.lucide?.createIcons();
        el.querySelectorAll('[data-bo-anh]').forEach((k) => window.ganBoAnh?.(k)?.refresh());
      });
      popup.on('remove', () => {
        if (dangGhim === popup) dangGhim = null;
      });
    };
    const mo = (ghim) => {
      tao();
      giu();
      if (ghim) {
        if (dangGhim && dangGhim !== popup) dangGhim.remove();
        dangGhim = popup;
      }
      popup.options.autoClose = popup !== dangGhim;
      popup.options.autoPan = popup === dangGhim;
      if (!banDo.hasLayer(popup)) popup.openOn(banDo);
      else if (ghim) popup.update();
      popup.getElement()?.classList.toggle('da-ghim', popup === dangGhim);
    };
    const dong = () => {
      giu();
      if (popup) {
        if (dangGhim === popup) dangGhim = null;
        popup.remove();
      }
    };
    moc.on('mouseover', () => mo(false));
    moc.on('mouseout', anSau);
    moc.on('click', () => mo(true));
    moc.on('keypress', (e) => {
      if (e.originalEvent.key === 'Enter') mo(true);
    });
    moc.on('remove', dong);
    return { mo, dong, anSau };
  };
};
