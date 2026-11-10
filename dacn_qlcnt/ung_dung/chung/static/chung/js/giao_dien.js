// Ô chọn thả xuống có ô tìm kiếm (Choices.js): mọi ô trong thanh lọc, và ô dài từ 7 lựa chọn ở form.
// Thêm data-khong-tim để giữ ô chọn gốc; data-tim-kiem-chon để luôn bật tìm kiếm.
const ganChonCoTim = (pham_vi = document) => {
  if (!window.Choices) return;
  pham_vi.querySelectorAll('select').forEach((o) => {
    if (o.dataset.daGanChon || o.multiple || o.disabled || o.hasAttribute('data-khong-tim')) return;
    if (o.closest('.ql-toolbar, .leaflet-container')) return;
    // Mọi ô lọc ở khu quản lý (form GET) đều có tìm kiếm, trừ ô số dòng mỗi trang.
    const laOLoc = (o.closest('.thanh-loc') || (o.closest('form[method="get"]') && o.closest('.khung-ung-dung')))
      && o.name !== 'moi_trang';
    if (!(laOLoc || o.hasAttribute('data-tim-kiem-chon') || o.options.length >= 7)) return;
    o.dataset.daGanChon = '1';
    // eslint-disable-next-line no-new
    new window.Choices(o, {
      allowHTML: false,
      shouldSort: false,
      searchEnabled: true,
      searchResultLimit: 50,
      searchFields: ['label'],
      fuseOptions: { threshold: 0.3, ignoreLocation: true },
      itemSelectText: '',
      position: 'bottom',
      searchPlaceholderValue: 'Gõ để tìm…',
      noResultsText: 'Không có kết quả phù hợp',
      noChoicesText: 'Không còn lựa chọn',
      loadingText: 'Đang tải…',
    });
  });
};

document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) window.lucide.createIcons();
  ganChonCoTim();
});
document.addEventListener("htmx:afterSwap", (suKien) => {
  if (window.lucide) window.lucide.createIcons();
  ganChonCoTim(suKien.target);
});

// Nút data-sao-chep="giá trị": chép vào bộ nhớ tạm, đổi nhãn trong 2 giây.
document.addEventListener('click', async (suKien) => {
  const nut = suKien.target.closest('[data-sao-chep]');
  if (!nut) return;
  try {
    await navigator.clipboard.writeText(nut.dataset.saoChep);
    nut.classList.add('da-sao-chep');
    nut.setAttribute('aria-label', 'Đã chép');
    setTimeout(() => nut.classList.remove('da-sao-chep'), 2000);
  } catch (_) {
    window.prompt('Chép giá trị này:', nut.dataset.saoChep);
  }
});

// Phần tử data-dem-nguoc="giây Unix": hiện mm:ss còn lại, hết giờ thì tải lại trang.
const demNguoc = () => {
  document.querySelectorAll('[data-dem-nguoc]').forEach((o) => {
    const con = Math.max(0, Number(o.dataset.demNguoc) * 1000 - Date.now());
    const phut = Math.floor(con / 60000);
    const giay = Math.floor((con % 60000) / 1000);
    o.textContent = `${String(phut).padStart(2, '0')}:${String(giay).padStart(2, '0')}`;
    if (con === 0 && !o.dataset.daHet) {
      o.dataset.daHet = '1';
      setTimeout(() => window.location.reload(), 1500);
    }
  });
};
if (document.querySelector('[data-dem-nguoc]')) {
  demNguoc();
  setInterval(demNguoc, 1000);
}

// Menu cuộn ngang trên điện thoại: đưa mục đang chọn vào giữa tầm nhìn.
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.menu-trang-thong-tin [aria-current], .menu-tai-khoan nav [aria-current], .menu-khach [aria-current]').forEach((muc) => {
    const khung = muc.parentElement;
    if (khung.scrollWidth > khung.clientWidth) {
      khung.scrollLeft = muc.offsetLeft - (khung.clientWidth - muc.offsetWidth) / 2;
    }
  });
});

// Hiện dần các khối khi cuộn tới (trang khách); tắt khi người dùng chọn giảm chuyển động.
(() => {
  if (!('IntersectionObserver' in window)) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const cacKhoi = document.querySelectorAll('.noi-dung-khach .muc-khach, .noi-dung-khach .luoi-thuoc-khach > *');
  if (!cacKhoi.length) return;
  document.documentElement.classList.add('hieu-ung-cuon');
  const quanSat = new IntersectionObserver((cacMuc) => {
    cacMuc.forEach((muc) => {
      if (!muc.isIntersecting) return;
      muc.target.classList.add('da-hien');
      quanSat.unobserve(muc.target);
    });
  }, { rootMargin: '0px 0px -40px 0px', threshold: 0.05 });
  cacKhoi.forEach((khoi, i) => {
    khoi.style.setProperty('--tre', `${(i % 4) * 60}ms`);
    quanSat.observe(khoi);
  });
})();
