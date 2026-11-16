(() => {
  const form = document.getElementById('form-dat-hang');
  if (!form || !window.htmx) return;
  const trangThai = form.querySelector('[data-trang-thai-dat-hang]');
  let luotCapNhat = null;
  let daCapNhat = true;

  const khoaDatHang = (khoa) => {
    const nutDat = form.querySelector('[data-xac-nhan-dat-hang]');
    nutDat.disabled = khoa || !nutDat.hasAttribute('data-du-dieu-kien');
  };

  form.addEventListener('htmx:beforeRequest', (e) => {
    luotCapNhat = e.detail.xhr;
    daCapNhat = false;
    form.querySelector('#lua-chon-dat-hang').setAttribute('aria-busy', 'true');
    khoaDatHang(true);
    trangThai.textContent = 'Đang cập nhật lựa chọn và tổng tiền…';
  });
  form.addEventListener('htmx:beforeSwap', (e) => {
    if (e.detail.xhr.getResponseHeader('X-Khoi-Dat-Hang') === 'lua-chon') return;
    e.detail.shouldSwap = false;
    const url = new URL(e.detail.xhr.responseURL || location.href, location.href);
    if (url.origin === location.origin && url.pathname !== location.pathname) location.assign(url);
  });
  form.addEventListener('htmx:afterRequest', (e) => {
    if (e.detail.xhr !== luotCapNhat) return;
    luotCapNhat = null;
    daCapNhat = e.detail.successful && e.detail.xhr.getResponseHeader('X-Khoi-Dat-Hang') === 'lua-chon';
    form.querySelector('#lua-chon-dat-hang').removeAttribute('aria-busy');
    khoaDatHang(!daCapNhat);
    trangThai.textContent = daCapNhat
      ? 'Đã cập nhật lựa chọn và tổng tiền.'
      : 'Chưa cập nhật được. Hãy chọn lại chi nhánh hoặc tải lại trang.';
  });
  // Vị trí của khách (định vị, địa chỉ gõ vào hoặc điểm chạm trên bản đồ) được ghi vào ba ô ẩn rồi tải lại
  // khối lựa chọn: máy chủ sắp chi nhánh theo khoảng cách PostGIS, bản đồ hiện vị trí và đường đi.
  // Ô ẩn nằm trong form nên vị trí còn nguyên khi khách đổi chi nhánh.
  const bao = (chu) => {
    const o = form.querySelector('[data-trang-thai-vi-tri]');
    if (o) o.textContent = chu;
  };
  const datViTri = (viDo, kinhDo, nhan) => {
    form.querySelector('[data-vi-do]').value = Number(viDo).toFixed(6);
    form.querySelector('[data-kinh-do]').value = Number(kinhDo).toFixed(6);
    form.querySelector('[data-nhan-vi-tri]').value = nhan;
    // Vị trí mới thì chọn lại từ đầu: máy chủ chọn sẵn nhà thuốc gần nhất còn đủ hàng.
    form.querySelectorAll('input[name="chi_nhanh"]').forEach((o) => { o.checked = false; });
    window.htmx.trigger(form, 'cap-nhat');
  };
  form.addEventListener('dat-vi-tri', (e) => datViTri(e.detail.viDo, e.detail.kinhDo, e.detail.nhan));

  const dinhVi = (nut) => {
    if (!navigator.geolocation) {
      bao('Trình duyệt không hỗ trợ định vị. Hãy nhập địa chỉ của bạn.');
      return;
    }
    nut.disabled = true;
    bao('Đang lấy vị trí của bạn…');
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => datViTri(coords.latitude, coords.longitude, 'vị trí hiện tại của bạn'),
      () => {
        nut.disabled = false;
        bao('Không lấy được vị trí (chưa cho phép định vị hoặc thiết bị không định vị được). Hãy nhập địa chỉ của bạn.');
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  };

  // Địa chỉ Nominatim rất dài (thêm phường, mã bưu chính, quốc gia): chỉ giữ ba phần đầu để hiện lại.
  const rutGonDiaChi = (diaChi) => diaChi.split(', ')
    .filter((phan) => !/^\d{5,6}$/.test(phan) && phan !== 'Việt Nam')
    .slice(0, 3)
    .join(', ');

  async function timDiaChi() {
    const khung = form.querySelector('[data-url-tim-dia-chi]');
    const o = form.querySelector('[data-tu-khoa-dat-hang]');
    const ketQua = form.querySelector('[data-ket-qua-dia-chi-dat-hang]');
    if (!khung || !o) return;
    const tuKhoa = o.value.trim();
    ketQua.replaceChildren();
    if (tuKhoa.length < 3) { bao('Nhập ít nhất 3 ký tự, ví dụ tên đường và quận.'); return; }
    bao('Đang tìm địa chỉ…');
    try {
      const phanHoi = await fetch(`${khung.dataset.urlTimDiaChi}?q=${encodeURIComponent(tuKhoa)}`, { headers: { Accept: 'application/json' } });
      const duLieu = await phanHoi.json();
      if (!phanHoi.ok) throw new Error((duLieu.loi || []).join(' '));
      if (!duLieu.ket_qua.length) { bao('Không thấy địa chỉ phù hợp. Hãy thử chỉ gõ tên đường và quận.'); return; }
      bao(duLieu.gan_dung ? 'Chưa thấy đúng số nhà này. Chọn con đường gần đúng:' : 'Chọn đúng địa chỉ của bạn:');
      duLieu.ket_qua.forEach((muc) => {
        const nut = document.createElement('button');
        nut.type = 'button';
        nut.textContent = muc.dia_chi;
        nut.addEventListener('click', () => {
          ketQua.replaceChildren();
          bao('Đang tìm nhà thuốc gần địa chỉ này…');
          datViTri(muc.vi_do, muc.kinh_do, rutGonDiaChi(muc.dia_chi));
        });
        ketQua.append(nut);
      });
    } catch (loi) {
      bao(loi.message || 'Chưa tìm được địa chỉ, hãy thử lại.');
    }
  }

  form.addEventListener('click', (e) => {
    const nutDinhVi = e.target.closest('[data-sap-theo-vi-tri]');
    if (nutDinhVi) dinhVi(nutDinhVi);
    if (e.target.closest('[data-tim-dia-chi-dat-hang]')) timDiaChi();
  });
  // Enter trong ô địa chỉ là tìm địa chỉ, không được gửi form đặt giữ.
  form.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.target.matches('[data-tu-khoa-dat-hang]')) {
      e.preventDefault();
      timDiaChi();
    }
  });
  form.addEventListener('submit', (e) => {
    if (e.submitter?.name === 'cap_nhat') {
      e.preventDefault();
      window.htmx.trigger(form, 'cap-nhat');
    } else if (!daCapNhat) {
      e.preventDefault();
    }
  });
})();
