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
      : 'Chưa cập nhật được. Bấm Cập nhật lựa chọn để thử lại.';
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
