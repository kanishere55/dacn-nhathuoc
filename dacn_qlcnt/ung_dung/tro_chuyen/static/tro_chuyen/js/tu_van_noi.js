// Nút "Tư vấn" nổi ở mọi trang khách: mở khung chat (iframe cùng nguồn) ngay trên trang đang xem.
// Sau khi đăng nhập từ nút này, trang quay về với #tu-van và khung tự mở.
(() => {
  const goc = document.querySelector('[data-tu-van-noi]');
  if (!goc) return;
  const khung = goc.querySelector('[data-khung-tu-van]');
  const nutMo = goc.querySelector('[data-mo-tu-van]');
  if (!khung || !nutMo) return;
  const iframe = khung.querySelector('iframe');

  function mo(duongDan) {
    if (duongDan) iframe.src = duongDan;
    else if (!iframe.src) iframe.src = iframe.dataset.src;
    khung.hidden = false;
    nutMo.setAttribute('aria-expanded', 'true');
    goc.classList.add('dang-mo');
  }

  function dong() {
    khung.hidden = true;
    nutMo.setAttribute('aria-expanded', 'false');
    goc.classList.remove('dang-mo');
    nutMo.focus();
  }

  nutMo.addEventListener('click', () => (khung.hidden ? mo() : dong()));
  khung.querySelector('[data-dong-tu-van]').addEventListener('click', dong);
  document.addEventListener('keydown', suKien => {
    if (suKien.key === 'Escape' && !khung.hidden) dong();
  });
  // Liên kết "Xem đơn" trong khung mở ở trang chính (target=_top); khung tự đóng theo trang mới.
  window.moKhungTuVan = mo;

  if (location.hash === '#tu-van') {
    history.replaceState(null, '', location.pathname + location.search);
    mo();
  }
})();
