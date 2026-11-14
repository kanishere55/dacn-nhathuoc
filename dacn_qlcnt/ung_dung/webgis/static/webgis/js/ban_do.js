// Trang tìm nhà thuốc: chọn vị trí (định vị, địa chỉ đã lưu, tìm địa chỉ, bấm bản đồ), xem chi nhánh
// gần nhất theo khoảng cách PostGIS, xem đường đi theo phương tiện; lọc theo thuốc là tùy chọn.
(() => {
  const khung = document.querySelector('[data-webgis]');
  if (!khung) return;
  const form = khung.querySelector('[data-tim-kiem]');
  const csrf = form.elements.csrfmiddlewaretoken.value;
  const baoViTri = khung.querySelector('[data-vi-tri]');
  const baoKetQua = khung.querySelector('[data-thong-bao]');
  const danhSachEl = khung.querySelector('[data-ket-qua]');
  const demEl = khung.querySelector('[data-dem]');
  const oBanKinh = khung.querySelector('[data-ban-kinh]');
  const bangLoTrinh = khung.querySelector('[data-bang-lo-trinh]');
  const docJson = (id) => JSON.parse(document.getElementById(id).textContent || 'null');
  const diaChiMacDinh = docJson('du-lieu-dia-chi-mac-dinh');
  const banDo = window.taoBanDoNhaThuoc(khung.querySelector('[data-ban-do]'));

  let cacChiNhanh = docJson('du-lieu-chi-nhanh') || [];
  let viTri = null; // [lat, lng]
  let locThuoc = null; // tập id chi nhánh còn đủ thuốc, null = không lọc
  let dangChon = null;
  let phuongTien = 'xe_may';
  let chiNhanhLoTrinh = null;
  let boDuong = null;
  let lanYeuCauDiBo = -Infinity;
  const cacLoTrinh = new Map();
  const cacMoc = new Map();
  const lopMoc = L.layerGroup().addTo(banDo);
  let mocNguoiDung = null;
  let lopDuong = null;

  const chu = (the, lop, noiDung) => {
    const el = document.createElement(the);
    if (lop) el.className = lop;
    if (noiDung !== undefined) el.textContent = noiDung;
    return el;
  };

  // ---------------------------------------------------------------- Vẽ danh sách và mốc bản đồ
  function veMoc() {
    lopMoc.clearLayers();
    cacMoc.clear();
    hienThi().forEach((cn, so) => {
      const moc = L.marker([cn.vi_do, cn.kinh_do], {
        icon: window.bieuTuongNhaThuoc({ noiBat: viTri && so === 0, mo: cn.id_chi_nhanh === dangChon }),
        alt: cn.ten_chi_nhanh,
        title: cn.ten_chi_nhanh,
      });
      const popup = chu('div', 'popup-nha-thuoc');
      const ten = chu('strong', '', cn.ten_chi_nhanh);
      const dc = chu('span', '', cn.dia_chi);
      const nut = chu('button', 'nut nut-phu', 'Xem đường đi');
      nut.type = 'button';
      nut.addEventListener('click', () => chonChiNhanh(cn));
      popup.append(ten, dc, nut);
      moc.bindPopup(popup);
      moc.on('click', () => chonChiNhanh(cn, false));
      moc.addTo(lopMoc);
      cacMoc.set(cn.id_chi_nhanh, moc);
    });
  }

  const hienThi = () => cacChiNhanh.filter((cn) => !locThuoc || locThuoc.has(cn.id_chi_nhanh));

  function veDanhSach() {
    const ds = hienThi();
    demEl.textContent = ds.length;
    danhSachEl.replaceChildren();
    if (!ds.length) {
      danhSachEl.append(chu('p', 'ghi-chu-khach', locThuoc
        ? 'Không có chi nhánh nào còn đủ thuốc đã chọn trong phạm vi này.'
        : 'Không có chi nhánh nào trong phạm vi đã chọn. Hãy mở rộng phạm vi.'));
    }
    ds.forEach((cn, so) => {
      const the = chu('article', 'the-nha-thuoc' + (cn.id_chi_nhanh === dangChon ? ' dang-chon' : ''));
      const anh = chu('div', 'anh-nha-thuoc');
      if (cn.anh) {
        const img = chu('img');
        img.src = cn.anh;
        img.alt = '';
        img.loading = 'lazy';
        anh.append(img);
      } else {
        anh.innerHTML = '<i data-lucide="store" aria-hidden="true"></i>';
      }
      const noiDung = chu('div', 'noi-dung-nha-thuoc');
      const dau = chu('div', 'dau-the-nha-thuoc');
      const ten = chu('h3');
      const link = chu('a', '', cn.ten_chi_nhanh);
      link.href = cn.duong_dan;
      ten.append(link);
      dau.append(ten);
      if (cn.khoang_cach_met !== null && cn.khoang_cach_met !== undefined) {
        dau.append(chu('span', 'nhan-khoang-cach' + (so === 0 ? ' gan-nhat' : ''),
          (so === 0 ? 'Gần nhất · ' : '') + window.dinhDangKm(cn.khoang_cach_met)));
      }
      const diaChi = chu('p', 'dia-chi-nha-thuoc', cn.dia_chi);
      const meta = chu('p', 'meta-nha-thuoc');
      meta.append(
        chu('span', cn.dang_mo_cua ? 'nhan-dang-mo' : 'nhan-da-dong', cn.dang_mo_cua ? 'Đang mở cửa' : 'Đã đóng cửa'),
        chu('span', '', `${cn.gio_mo_cua}–${cn.gio_dong_cua}`),
      );
      if (cn.so_dien_thoai) {
        const tel = chu('a', '', cn.so_dien_thoai);
        tel.href = 'tel:' + cn.so_dien_thoai;
        meta.append(tel);
      }
      if (cn.diem_sao) meta.append(chu('span', 'sao', `★ ${cn.diem_sao} (${cn.so_danh_gia})`));
      const tacVu = chu('div', 'tac-vu-nha-thuoc');
      const nutDuong = chu('button', 'nut nut-phu', 'Đường đi');
      nutDuong.type = 'button';
      nutDuong.addEventListener('click', () => chonChiNhanh(cn));
      const chiTiet = chu('a', 'nut nut-phu', 'Chi tiết');
      chiTiet.href = cn.duong_dan;
      const datHang = chu('a', 'nut', 'Đặt hàng tại đây');
      datHang.href = `${khung.dataset.urlDatHang}?${new URLSearchParams({ hinh_thuc_nhan: 'nhan_tai_quay', chi_nhanh: cn.id_chi_nhanh })}`;
      tacVu.append(nutDuong, chiTiet, datHang);
      noiDung.append(dau, diaChi, meta, tacVu);
      the.append(anh, noiDung);
      the.addEventListener('mouseenter', () => cacMoc.get(cn.id_chi_nhanh)?.openPopup());
      danhSachEl.append(the);
    });
    if (window.lucide) window.lucide.createIcons();
  }

  function veLai({ vuaKhung = false } = {}) {
    veDanhSach();
    veMoc();
    if (vuaKhung) {
      const ds = hienThi();
      const diem = [...ds.slice(0, viTri ? 5 : ds.length).map((cn) => [cn.vi_do, cn.kinh_do]), ...(viTri ? [viTri] : [])];
      if (diem.length) banDo.fitBounds(diem, { padding: [36, 36], maxZoom: 15 });
    }
  }

  // ---------------------------------------------------------------- Vị trí người xem
  async function napTheoViTri() {
    const banKinh = Number(oBanKinh.value);
    if (!viTri) {
      baoKetQua.textContent = 'Chọn vị trí để sắp xếp theo khoảng cách.';
      return;
    }
    baoKetQua.textContent = 'Đang tính khoảng cách…';
    const thamSo = new URLSearchParams({ vi_do: viTri[0], kinh_do: viTri[1] });
    if (banKinh) thamSo.set('ban_kinh_met', banKinh);
    try {
      const phanHoi = await fetch(`${khung.dataset.urlGan}?${thamSo}`, { headers: { Accept: 'application/json' } });
      if (!phanHoi.ok) throw new Error();
      cacChiNhanh = (await phanHoi.json()).ket_qua;
      const ds = hienThi();
      baoKetQua.textContent = ds.length
        ? `Gần bạn nhất: ${ds[0].ten_chi_nhanh} (${window.dinhDangKm(ds[0].khoang_cach_met)} theo đường chim bay).`
        : 'Không có chi nhánh phù hợp trong phạm vi đã chọn.';
      veLai({ vuaKhung: true });
    } catch {
      baoKetQua.textContent = 'Chưa tính được khoảng cách, vui lòng thử lại.';
    }
  }

  function datViTri(lat, lng, moTa) {
    viTri = [lat, lng];
    if (!mocNguoiDung) {
      mocNguoiDung = L.marker(viTri, { icon: window.bieuTuongNguoiDung(), draggable: true, zIndexOffset: 1000 }).addTo(banDo);
      mocNguoiDung.on('dragend', () => {
        const p = mocNguoiDung.getLatLng();
        datViTri(p.lat, p.lng, 'điểm đã kéo trên bản đồ');
      });
    } else {
      mocNguoiDung.setLatLng(viTri);
    }
    baoViTri.textContent = `Đang dùng ${moTa}. Có thể kéo chấm xanh để chỉnh.`;
    xoaLoTrinh();
    napTheoViTri();
  }

  banDo.on('click', (e) => datViTri(e.latlng.lat, e.latlng.lng, 'điểm bạn chọn trên bản đồ'));
  oBanKinh.addEventListener('change', () => (viTri ? napTheoViTri() : (baoKetQua.textContent = 'Phạm vi chỉ áp dụng khi đã chọn vị trí.')));

  khung.querySelector('[data-dinh-vi]').addEventListener('click', () => {
    if (!navigator.geolocation) {
      baoViTri.textContent = 'Trình duyệt không hỗ trợ định vị. Hãy bấm lên bản đồ.';
      return;
    }
    baoViTri.textContent = 'Đang lấy vị trí của bạn…';
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => datViTri(coords.latitude, coords.longitude, 'vị trí hiện tại của bạn'),
      () => { baoViTri.textContent = 'Không lấy được vị trí (chưa cho phép định vị). Hãy tìm địa chỉ hoặc bấm lên bản đồ.'; },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  });
  khung.querySelector('[data-dia-chi-mac-dinh]')?.addEventListener('click', () => {
    datViTri(diaChiMacDinh.vi_do, diaChiMacDinh.kinh_do, `địa chỉ đã lưu: ${diaChiMacDinh.dia_chi}`);
  });

  // Tìm địa chỉ qua máy chủ (Nominatim), chỉ khi đã đăng nhập.
  const oTuKhoa = khung.querySelector('[data-tu-khoa]');
  const ketQuaDiaChi = khung.querySelector('[data-ket-qua-dia-chi]');
  async function timDiaChi() {
    const tuKhoa = oTuKhoa.value.trim();
    ketQuaDiaChi.replaceChildren();
    if (tuKhoa.length < 3) { baoViTri.textContent = 'Nhập ít nhất 3 ký tự để tìm địa chỉ.'; return; }
    baoViTri.textContent = 'Đang tìm địa chỉ…';
    try {
      const phanHoi = await fetch(`${khung.dataset.urlTimDiaChi}?q=${encodeURIComponent(tuKhoa)}`, { headers: { Accept: 'application/json' } });
      const duLieu = await phanHoi.json();
      if (!phanHoi.ok) throw new Error((duLieu.loi || []).join(' '));
      if (!duLieu.ket_qua.length) { baoViTri.textContent = 'Không thấy địa chỉ phù hợp. Hãy thử chỉ gõ tên đường, hoặc bấm lên bản đồ.'; return; }
      baoViTri.textContent = duLieu.gan_dung ? 'Chưa thấy đúng số nhà này. Chọn con đường gần đúng:' : 'Chọn một kết quả:';
      duLieu.ket_qua.forEach((muc) => {
        const nut = chu('button', '', muc.dia_chi);
        nut.type = 'button';
        nut.addEventListener('click', () => {
          ketQuaDiaChi.replaceChildren();
          datViTri(muc.vi_do, muc.kinh_do, `địa chỉ: ${muc.dia_chi}`);
        });
        ketQuaDiaChi.append(nut);
      });
    } catch (loi) {
      baoViTri.textContent = loi.message || 'Chưa tìm được địa chỉ, hãy thử lại.';
    }
  }
  khung.querySelector('[data-tim-dia-chi]')?.addEventListener('click', timDiaChi);
  oTuKhoa?.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); timDiaChi(); } });

  // ---------------------------------------------------------------- Lộ trình
  function xoaLoTrinh() {
    boDuong?.abort();
    boDuong = null;
    lopDuong?.remove();
    lopDuong = null;
    chiNhanhLoTrinh = null;
    cacLoTrinh.clear();
    bangLoTrinh.hidden = true;
  }

  function chonChiNhanh(cn, moPopup = true) {
    if (dangChon !== cn.id_chi_nhanh) cacLoTrinh.clear();
    dangChon = cn.id_chi_nhanh;
    veLai();
    if (!viTri) {
      banDo.setView([cn.vi_do, cn.kinh_do], 16);
      if (moPopup) cacMoc.get(cn.id_chi_nhanh)?.openPopup();
      baoViTri.textContent = 'Chọn vị trí của bạn để xem đường đi tới chi nhánh này.';
      return;
    }
    banDo.closePopup();
    chiNhanhLoTrinh = cn;
    veLoTrinh(cn);
    if (moPopup) {
      bangLoTrinh.querySelector('[data-ten-dich]').focus({ preventScroll: true });
      bangLoTrinh.scrollIntoView({ block: 'nearest' });
    }
  }

  async function veLoTrinh(cn) {
    boDuong?.abort();
    const luot = new AbortController();
    boDuong = luot;
    const diBo = phuongTien === 'di_bo';
    const hoSo = diBo ? 'di_bo' : 'o_to';
    const mayChu = diBo ? khung.dataset.osrmDiBo : khung.dataset.osrm;
    const den = [cn.vi_do, cn.kinh_do];
    const baoDuong = bangLoTrinh.querySelector('[data-quang-duong]');
    const baoThoiGian = bangLoTrinh.querySelector('[data-thoi-gian]');
    const ghiChu = bangLoTrinh.querySelector('[data-ghi-chu-lo-trinh]');
    lopDuong?.remove();
    lopDuong = null;
    bangLoTrinh.hidden = false;
    bangLoTrinh.querySelector('[data-ten-dich]').textContent = cn.ten_chi_nhanh;
    bangLoTrinh.querySelector('[data-nguon-di-bo]').hidden = !diBo;
    baoDuong.textContent = 'Đang tính…';
    baoThoiGian.textContent = '—';
    ghiChu.textContent = '';
    const hen = setTimeout(() => luot.abort(), 12000);
    try {
      let duong = cacLoTrinh.get(hoSo);
      if (!duong) {
        if (diBo) {
          // Máy chủ công cộng dành cho đi bộ giới hạn một yêu cầu mỗi giây.
          const cho = Math.max(0, lanYeuCauDiBo + 1000 - performance.now());
          if (cho) await new Promise((xong) => setTimeout(xong, cho));
          if (boDuong !== luot) return;
          lanYeuCauDiBo = performance.now();
        }
        duong = await window.layLoTrinh(mayChu, viTri, den, luot.signal);
        if (boDuong !== luot) return;
        cacLoTrinh.set(hoSo, duong);
      }
      lopDuong = L.geoJSON(duong.geometry, { style: { color: '#116b54', weight: 6, opacity: 0.85 } }).addTo(banDo);
      banDo.fitBounds(lopDuong.getBounds(), { padding: [40, 40], maxZoom: 16 });
      baoDuong.textContent = window.dinhDangKm(duong.distance);
      baoThoiGian.textContent = window.dinhDangPhut(window.thoiGianTheoPhuongTien(duong, phuongTien));
      ghiChu.textContent = {
        di_bo: 'Quãng đường và thời gian theo tuyến đi bộ.',
        o_to: 'Thời gian theo tuyến ô tô, chưa tính kẹt xe.',
        xe_may: 'Thời gian xe máy ước tính trên tuyến ô tô.',
      }[phuongTien];
    } catch {
      if (boDuong !== luot) return;
      lopDuong = L.polyline([viTri, den], { color: '#116b54', dashArray: '6 8', weight: 4 }).addTo(banDo);
      banDo.fitBounds(lopDuong.getBounds(), { padding: [40, 40], maxZoom: 16 });
      baoDuong.textContent = window.dinhDangKm(banDo.distance(viTri, den)) + ' (đường chim bay)';
      ghiChu.textContent = diBo
        ? 'Chưa lấy được tuyến đi bộ. Đường nét đứt là khoảng cách thẳng.'
        : 'Chưa lấy được lộ trình đường bộ. Đường nét đứt là khoảng cách thẳng.';
    } finally {
      clearTimeout(hen);
    }
  }
  bangLoTrinh.querySelectorAll('[data-phuong-tien]').forEach((nut) => nut.addEventListener('click', () => {
    phuongTien = nut.dataset.phuongTien;
    bangLoTrinh.querySelectorAll('[data-phuong-tien]').forEach((n) => n.setAttribute('aria-pressed', String(n === nut)));
    if (chiNhanhLoTrinh) veLoTrinh(chiNhanhLoTrinh);
  }));
  bangLoTrinh.querySelector('[data-dong-lo-trinh]').addEventListener('click', () => {
    xoaLoTrinh();
    dangChon = null;
    veLai();
  });

  // ---------------------------------------------------------------- Lọc theo thuốc (tùy chọn)
  const danhMucThuoc = new Map(Array.from(form.querySelectorAll('[data-goi-y] option'), (o) => [o.value, o.dataset]));
  const cacDong = () => Array.from(form.querySelectorAll('[data-dong-thuoc]'));
  const nutThem = form.querySelector('[data-them-thuoc]');
  if (nutThem) {
    const gioiHan = Number(khung.dataset.gioiHan);
    const capNhatNut = () => {
      const ds = cacDong();
      ds.forEach((d) => { d.querySelector('[data-xoa-thuoc]').hidden = ds.length === 1; });
      nutThem.disabled = ds.length >= gioiHan;
    };
    nutThem.addEventListener('click', () => {
      const dong = cacDong()[0].cloneNode(true);
      dong.querySelector('[data-thuoc]').value = '';
      dong.querySelector('[data-so-luong]').value = '1';
      dong.querySelector('[data-don-vi]').textContent = '';
      form.querySelector('[data-nhu-cau]').append(dong);
      capNhatNut();
      dong.querySelector('[data-thuoc]').focus();
    });
    form.addEventListener('click', (e) => {
      const nutXoa = e.target.closest('[data-xoa-thuoc]');
      if (nutXoa && cacDong().length > 1) { nutXoa.closest('[data-dong-thuoc]').remove(); capNhatNut(); }
    });
    form.addEventListener('input', (e) => {
      if (!e.target.matches('[data-thuoc]')) return;
      e.target.setCustomValidity('');
      const donVi = danhMucThuoc.get(e.target.value)?.donVi;
      e.target.closest('[data-dong-thuoc]').querySelector('[data-don-vi]').textContent = donVi ? ' · ' + donVi : '';
    });
    capNhatNut();
  }

  function layNhuCau() {
    const nhuCau = [];
    for (const dong of cacDong()) {
      const oThuoc = dong.querySelector('[data-thuoc]');
      const thuoc = oThuoc ? danhMucThuoc.get(oThuoc.value) : dong.dataset;
      if (!thuoc) {
        oThuoc.setCustomValidity('Chọn thuốc trong danh sách gợi ý.');
        oThuoc.reportValidity();
        return null;
      }
      const soLuong = dong.querySelector('input[data-so-luong]')?.value ?? dong.dataset.soLuong;
      nhuCau.push({ id_thuoc: Number(thuoc.idThuoc), so_luong: Number(soLuong) || 1 });
    }
    return nhuCau;
  }

  async function apDungLocThuoc() {
    const nhuCau = layNhuCau();
    if (!nhuCau || !nhuCau.length) return;
    baoKetQua.textContent = 'Đang kiểm tra tồn kho các chi nhánh…';
    const goc = viTri || [10.7769, 106.7009];
    try {
      const phanHoi = await fetch(khung.dataset.urlTim, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify({ kinh_do: goc[1], vi_do: goc[0], ban_kinh_met: 50000, cac_thuoc: nhuCau }),
      });
      if (!phanHoi.ok) throw new Error();
      const { ket_qua: ketQua } = await phanHoi.json();
      locThuoc = new Set(ketQua.map((cn) => cn.id_chi_nhanh));
      form.querySelector('[data-bo-loc-thuoc]')?.removeAttribute('hidden');
      baoKetQua.textContent = locThuoc.size
        ? `${locThuoc.size} chi nhánh còn đủ thuốc đã chọn.`
        : 'Không chi nhánh nào còn đủ toàn bộ thuốc đã chọn.';
      veLai({ vuaKhung: true });
    } catch {
      baoKetQua.textContent = 'Chưa kiểm tra được tồn kho, vui lòng thử lại.';
    }
  }
  form.querySelector('[data-ap-dung-thuoc]')?.addEventListener('click', apDungLocThuoc);
  form.querySelector('[data-bo-loc-thuoc]')?.addEventListener('click', (e) => {
    locThuoc = null;
    e.currentTarget.hidden = true;
    baoKetQua.textContent = 'Đã bỏ lọc thuốc, hiển thị mọi chi nhánh.';
    veLai({ vuaKhung: true });
  });
  form.addEventListener('submit', (e) => e.preventDefault());

  veLai({ vuaKhung: true });
  // Đến từ giỏ hàng hoặc từ trang thuốc: lọc ngay theo thuốc đó.
  if (khung.hasAttribute('data-tu-gio') || form.querySelector('[data-thuoc]')?.value) apDungLocThuoc();
})();
