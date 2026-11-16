// Bộ ảnh trượt dùng chung (trang thuốc, trang chi nhánh, popup bản đồ), chạy trên thư viện Splide.
// Khung [data-bo-anh] chứa .bo-anh-chinh (ảnh lớn, nút ‹ ›) và tùy chọn .bo-anh-nho (ảnh nhỏ để chọn).
(() => {
  const CHU = {
    prev: 'Ảnh trước',
    next: 'Ảnh sau',
    first: 'Về ảnh đầu',
    last: 'Đến ảnh cuối',
    slideX: 'Xem ảnh %s',
    pageX: 'Xem ảnh %s',
    carousel: 'bộ ảnh',
    select: 'Chọn ảnh để xem',
    slide: 'ảnh',
    slideLabel: 'Ảnh %s trên %s',
  };

  window.ganBoAnh = (khung) => {
    const chinh = khung.querySelector('.bo-anh-chinh');
    if (!window.Splide || !chinh || khung.boAnh) return khung.boAnh;
    const nhieuAnh = chinh.querySelectorAll('.splide__slide').length > 1;
    const lon = new window.Splide(chinh, {
      type: nhieuAnh ? 'loop' : 'slide',
      arrows: nhieuAnh,
      pagination: false,
      drag: nhieuAnh,
      keyboard: 'focused',
      speed: 420,
      i18n: CHU,
    });
    const soAnh = chinh.querySelector('[data-so-anh]');
    if (soAnh) lon.on('move', (moi) => { soAnh.textContent = moi + 1; });
    const nhoEl = khung.querySelector('.bo-anh-nho');
    if (nhoEl) {
      const nho = new window.Splide(nhoEl, {
        isNavigation: true,
        pagination: false,
        arrows: false,
        fixedWidth: 72,
        fixedHeight: 72,
        gap: 8,
        i18n: CHU,
        breakpoints: { 640: { fixedWidth: 56, fixedHeight: 56 } },
      });
      lon.sync(nho);
      lon.mount();
      nho.mount();
    } else {
      lon.mount();
    }
    khung.boAnh = lon;
    return lon;
  };

  document.querySelectorAll('[data-bo-anh]').forEach((khung) => window.ganBoAnh(khung));
})();
