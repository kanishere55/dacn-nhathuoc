// Màn bán tại quầy: tìm thuốc → thêm dòng → tính tổng, kiểm tồn, mở phần đơn thuốc khi cần.
// Các dòng được ghi ra input ẩn đúng tên formset (form-N-thuoc...) để server xử lý như cũ.
(() => {
  const form = document.querySelector('[data-quay-ban]');
  if (!form) return;
  const {thuoc: dsThuoc, ton} = JSON.parse(document.getElementById('du-lieu-quay').textContent);
  const theoId = new Map(dsThuoc.map(t => [t.id, t]));
  const cacDong = JSON.parse(document.getElementById('dong-ban-dau').textContent)
    .filter(d => theoId.has(d.thuoc));

  const oTim = form.querySelector('[data-o-tim]');
  const goiY = form.querySelector('[data-goi-y]');
  const than = form.querySelector('[data-cac-dong]');
  const dongAn = form.querySelector('[data-dong-an]');
  const nutHoanTat = form.querySelector('[data-nut-hoan-tat]');
  const canhBao = form.querySelector('[data-canh-bao]');
  const khachDua = form.querySelector('[data-khach-dua]');
  const donThuoc = form.querySelector('[data-don-thuoc]');
  const chonChiNhanh = form.elements.chi_nhanh;
  const tien = so => Math.round(so).toLocaleString('vi-VN') + ' đ';
  const boDau = chu => chu.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/gi, 'd').toLowerCase();
  const chiMuc = new Map(dsThuoc.map(t => [t.id, boDau(`${t.ten} ${t.ma} ${t.hoat_chat}`)]));
  const tao = (the, lop, chu) => {
    const phanTu = document.createElement(the);
    if (lop) phanTu.className = lop;
    if (chu != null) phanTu.textContent = chu;
    return phanTu;
  };

  const tonCua = idThuoc => (ton[chonChiNhanh?.value] || {})[idThuoc] || 0;
  const heSo = dong => theoId.get(dong.thuoc).bao_goi.find(b => b.id === dong.bao_goi)?.he_so || 1;
  const thanhTien = dong => dong.so_luong * heSo(dong) * theoId.get(dong.thuoc).don_gia;

  // ---- Tìm thuốc ----
  let ketQua = [];
  let viTri = -1;
  function goiYTimKiem() {
    const tuKhoa = boDau(oTim.value.trim());
    if (!tuKhoa) {
      dongGoiY();
      return;
    }
    const cacTu = tuKhoa.split(/\s+/);
    ketQua = dsThuoc.filter(t => cacTu.every(tu => chiMuc.get(t.id).includes(tu))).slice(0, 8);
    viTri = ketQua.length ? 0 : -1;
    veGoiY();
  }
  function veGoiY() {
    goiY.replaceChildren(
      ...(ketQua.length
        ? ketQua.map((t, i) => {
            const muc = tao('li', 'muc-goi-y');
            muc.id = `goi-y-${t.id}`;
            muc.setAttribute('role', 'option');
            muc.setAttribute('aria-selected', String(i === viTri));
            const trai = tao('span', 'ten-goi-y');
            trai.append(tao('strong', '', t.ten), tao('small', '', `${t.ma}${t.hoat_chat ? ' · ' + t.hoat_chat : ''}`));
            const phai = tao('span', 'gia-goi-y');
            const conLai = tonCua(t.id);
            phai.append(
              tao('strong', '', `${tien(t.don_gia)} / ${t.don_vi.toLowerCase()}`),
              tao('small', conLai ? '' : 'het', conLai ? `Còn ${conLai.toLocaleString('vi-VN')}` : 'Hết hàng'),
            );
            if (t.ke_don) trai.querySelector('strong').append(tao('span', 'nhan-ke-don', 'Kê đơn'));
            muc.append(trai, phai);
            muc.addEventListener('mousedown', suKien => {
              suKien.preventDefault();
              themThuoc(t.id);
            });
            return muc;
          })
        : [tao('li', 'khong-thay', 'Không tìm thấy thuốc phù hợp.')]),
    );
    goiY.hidden = false;
    oTim.setAttribute('aria-expanded', 'true');
    oTim.setAttribute('aria-activedescendant', viTri >= 0 ? `goi-y-${ketQua[viTri].id}` : '');
  }
  function dongGoiY() {
    goiY.hidden = true;
    ketQua = [];
    viTri = -1;
    oTim.setAttribute('aria-expanded', 'false');
  }
  oTim.addEventListener('input', goiYTimKiem);
  oTim.addEventListener('blur', () => setTimeout(dongGoiY, 120));
  oTim.addEventListener('keydown', suKien => {
    if (suKien.key === 'ArrowDown' || suKien.key === 'ArrowUp') {
      if (!ketQua.length) return;
      suKien.preventDefault();
      viTri = (viTri + (suKien.key === 'ArrowDown' ? 1 : -1) + ketQua.length) % ketQua.length;
      veGoiY();
    } else if (suKien.key === 'Enter') {
      suKien.preventDefault();
      if (viTri >= 0) themThuoc(ketQua[viTri].id);
    } else if (suKien.key === 'Escape') {
      dongGoiY();
    }
  });

  function themThuoc(id) {
    const daCo = cacDong.find(d => d.thuoc === id && !d.bao_goi);
    if (daCo) daCo.so_luong += 1;
    else cacDong.push({thuoc: id, so_luong: 1, bao_goi: null});
    oTim.value = '';
    dongGoiY();
    ve();
    oTim.focus();
  }

  // ---- Bảng dòng bán ----
  function ve() {
    than.replaceChildren(...cacDong.map((dong, i) => veDong(dong, i)));
    form.querySelector('[data-gio-trong]').hidden = cacDong.length > 0;
    than.closest('table').hidden = cacDong.length === 0;
    ghiInputAn();
    tinhTong();
    window.lucide?.createIcons();
  }

  function veDong(dong, i) {
    const t = theoId.get(dong.thuoc);
    const hang = tao('tr');
    const coSo = dong.so_luong * heSo(dong);
    const conLai = tonCua(t.id);
    const vuot = coSo > conLai;
    if (vuot) hang.className = 'dong-vuot-ton';

    const oTen = tao('th');
    oTen.scope = 'row';
    oTen.append(tao('strong', '', t.ten));
    if (t.ke_don) oTen.querySelector('strong').append(tao('span', 'nhan-ke-don', 'Kê đơn'));
    oTen.append(tao('small', vuot ? 'het' : '', vuot
      ? `Không đủ hàng: cần ${coSo.toLocaleString('vi-VN')}, còn ${conLai.toLocaleString('vi-VN')} ${t.don_vi.toLowerCase()}`
      : `Còn ${conLai.toLocaleString('vi-VN')} ${t.don_vi.toLowerCase()} · ${t.ma}`));

    const oDonVi = tao('td');
    if (t.bao_goi.length) {
      const chon = tao('select');
      chon.setAttribute('data-khong-tim', '');
      chon.setAttribute('aria-label', `Đơn vị bán ${t.ten}`);
      chon.append(new Option(t.don_vi, ''));
      t.bao_goi.forEach(b => chon.append(new Option(`${b.ten} (${b.he_so} ${t.don_vi.toLowerCase()})`, b.id)));
      chon.value = dong.bao_goi ?? '';
      chon.addEventListener('change', () => {
        dong.bao_goi = chon.value ? Number(chon.value) : null;
        ve();
      });
      oDonVi.append(chon);
    } else {
      oDonVi.textContent = t.don_vi;
    }

    const oSoLuong = tao('td', 'o-so');
    const nhom = tao('div', 'buoc-so-luong');
    const giam = tao('button', '', '−');
    const tang = tao('button', '', '+');
    const nhap = tao('input');
    giam.type = tang.type = 'button';
    giam.setAttribute('aria-label', `Giảm số lượng ${t.ten}`);
    tang.setAttribute('aria-label', `Tăng số lượng ${t.ten}`);
    nhap.type = 'number';
    nhap.min = '1';
    nhap.inputMode = 'numeric';
    nhap.value = dong.so_luong;
    nhap.setAttribute('aria-label', `Số lượng ${t.ten}`);
    giam.addEventListener('click', () => {
      if (dong.so_luong > 1) dong.so_luong -= 1;
      ve();
    });
    tang.addEventListener('click', () => {
      dong.so_luong += 1;
      ve();
    });
    nhap.addEventListener('change', () => {
      dong.so_luong = Math.max(1, Math.floor(Number(nhap.value) || 1));
      ve();
    });
    nhom.append(giam, nhap, tang);
    oSoLuong.append(nhom);

    const donGia = tao('td', 'o-so', tien(t.don_gia * heSo(dong)));
    if (t.don_gia < t.gia_goc) donGia.append(tao('small', 'gia-cu', tien(t.gia_goc * heSo(dong))));
    const oBo = tao('td', 'o-bo');
    const bo = tao('button', 'nut-bo-dong');
    bo.type = 'button';
    bo.setAttribute('aria-label', `Bỏ ${t.ten} khỏi phiếu`);
    bo.innerHTML = '<i data-lucide="x" aria-hidden="true"></i>';
    bo.addEventListener('click', () => {
      cacDong.splice(i, 1);
      ve();
      oTim.focus();
    });
    oBo.append(bo);
    hang.append(oTen, oDonVi, oSoLuong, donGia, tao('td', 'o-so thanh-tien', tien(thanhTien(dong))), oBo);
    return hang;
  }

  function ghiInputAn() {
    dongAn.replaceChildren();
    cacDong.forEach((dong, i) => {
      [['thuoc', dong.thuoc], ['so_luong', dong.so_luong], ['quy_doi_bao_goi', dong.bao_goi ?? '']]
        .forEach(([ten, giaTri]) => {
          const o = tao('input');
          o.type = 'hidden';
          o.name = `form-${i}-${ten}`;
          o.value = giaTri;
          dongAn.append(o);
        });
    });
    form.elements['form-TOTAL_FORMS'].value = String(cacDong.length);
    form.elements['form-INITIAL_FORMS'].value = '0';
  }

  // ---- Tổng tiền, thanh toán, đơn thuốc ----
  function tinhTong() {
    const tong = cacDong.reduce((cong, dong) => cong + thanhTien(dong), 0);
    form.querySelector('[data-tong-tien]').textContent = tien(tong);
    form.querySelector('[data-so-mat-hang]').textContent = cacDong.length;
    const coKeDon = cacDong.some(d => theoId.get(d.thuoc).ke_don);
    if (coKeDon) donThuoc.open = true;
    donThuoc.classList.toggle('bat-buoc', coKeDon);
    form.querySelector('[data-nhan-don]').textContent = coKeDon
      ? '(bắt buộc: phiếu có thuốc kê đơn)'
      : '(chỉ cần khi có thuốc kê đơn)';
    const vuotTon = cacDong.filter(d => d.so_luong * heSo(d) > tonCua(d.thuoc));
    canhBao.hidden = !vuotTon.length;
    canhBao.textContent = vuotTon.length
      ? `Có ${vuotTon.length} thuốc không đủ hàng. Giảm số lượng hoặc bỏ dòng đó để hoàn tất.`
      : '';
    nutHoanTat.disabled = !cacDong.length || vuotTon.length > 0;
    tinhTienThoi(tong);
  }

  function tinhTienThoi(tong = cacDong.reduce((cong, dong) => cong + thanhTien(dong), 0)) {
    const dua = Number(khachDua.value);
    const thoi = form.querySelector('[data-tien-thoi]');
    if (!khachDua.value || !tong) thoi.textContent = '–';
    else if (dua < tong) thoi.textContent = `Còn thiếu ${tien(tong - dua)}`;
    else thoi.textContent = tien(dua - tong);
  }
  khachDua.addEventListener('input', () => tinhTienThoi());

  const capNhatThanhToan = () => {
    const tienMat = form.querySelector('[name="phuong_thuc_thanh_toan"]:checked')?.value === 'tien_mat';
    form.querySelector('[data-tien-mat]').hidden = !tienMat;
  };
  form.querySelectorAll('[name="phuong_thuc_thanh_toan"]').forEach(o => o.addEventListener('change', capNhatThanhToan));
  chonChiNhanh?.addEventListener('change', ve);

  // ---- Phím tắt và gửi phiếu ----
  document.addEventListener('keydown', suKien => {
    if (suKien.key === '/' && !suKien.target.closest('input, textarea, select')) {
      suKien.preventDefault();
      oTim.focus();
    }
    if (suKien.key === 'Enter' && (suKien.ctrlKey || suKien.metaKey) && !nutHoanTat.disabled) {
      suKien.preventDefault();
      form.requestSubmit(nutHoanTat);
    }
  });
  // Enter trong ô số lượng hay ô khách đưa chỉ chốt giá trị, không gửi phiếu ngoài ý muốn.
  form.addEventListener('keydown', suKien => {
    const o = suKien.target;
    if (suKien.key === 'Enter' && !suKien.ctrlKey && !suKien.metaKey && o.matches('input') && o !== oTim) {
      suKien.preventDefault();
      o.dispatchEvent(new Event('change', {bubbles: true}));
    }
  });
  form.addEventListener('submit', suKien => {
    if (!cacDong.length) {
      suKien.preventDefault();
      oTim.focus();
      return;
    }
    nutHoanTat.disabled = true;
    nutHoanTat.lastChild.textContent = 'Đang lưu phiếu…';
  });

  capNhatThanhToan();
  ve();
  oTim.focus();
})();
