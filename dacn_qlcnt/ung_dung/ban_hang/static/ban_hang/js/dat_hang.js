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
  // "Gần tôi nhất": lấy vị trí trình duyệt rồi tải lại danh sách chi nhánh, máy chủ sắp theo PostGIS.
  form.addEventListener('click', (e) => {
    const nut = e.target.closest('[data-sap-theo-vi-tri]');
    if (!nut) return;
    const bao = form.querySelector('[data-trang-thai-vi-tri]');
    if (!navigator.geolocation) {
      if (bao) bao.textContent = 'Trình duyệt không hỗ trợ định vị.';
      return;
    }
    nut.disabled = true;
    if (bao) bao.textContent = 'Đang lấy vị trí của bạn…';
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        form.querySelector('[data-vi-do]').value = coords.latitude.toFixed(6);
        form.querySelector('[data-kinh-do]').value = coords.longitude.toFixed(6);
        window.htmx.trigger(form, 'cap-nhat');
      },
      () => {
        nut.disabled = false;
        if (bao) bao.textContent = 'Không lấy được vị trí. Hãy cho phép định vị trong trình duyệt hoặc tự chọn chi nhánh.';
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
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
