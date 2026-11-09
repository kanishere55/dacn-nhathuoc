document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) window.lucide.createIcons();
});
document.addEventListener("htmx:afterSwap", () => {
  if (window.lucide) window.lucide.createIcons();
});

// Form có data-doi-lua-chon: đổi ô có data-tai-lai thì tải lại trang bằng GET để máy chủ tính lại.
document.addEventListener('change', (suKien) => {
  const o = suKien.target;
  if (!o.matches('[data-doi-lua-chon] [data-tai-lai]')) return;
  const thamSo = new URLSearchParams(new FormData(o.form));
  thamSo.delete('csrfmiddlewaretoken');
  window.location.search = thamSo.toString();
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
