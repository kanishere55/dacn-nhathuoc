// Băng chuyền banner trang chủ: tự chuyển 5 giây, tự dừng khi con trỏ hoặc tiêu điểm bàn phím đang ở
// trên banner hay khi tab bị ẩn; vuốt trên điện thoại, phím mũi tên; máy bật giảm chuyển động thì không tự chuyển.
(() => {
  const khoi = document.querySelector('[data-bang-chuyen]');
  if (!khoi) return;
  const cacSlide = [...khoi.querySelectorAll('.slide-hero')];
  const cacCham = [...khoi.querySelectorAll('[data-den]')];
  if (cacSlide.length < 2) return;
  const giamChuyenDong = window.matchMedia('(prefers-reduced-motion: reduce)');
  let hienTai = 0;
  let hen = null;
  let giamDong = giamChuyenDong.matches;
  let reChuot = false;
  let coFocus = false;
  let daTaiTrang = document.readyState === 'complete';
  let xBatDau = null;

  const den = (so) => {
    hienTai = (so + cacSlide.length) % cacSlide.length;
    const anh = cacSlide[hienTai].querySelector('[data-anh-banner]');
    if (anh) anh.replaceWith(anh.content);
    cacSlide.forEach((slide, i) => {
      const hien = i === hienTai;
      slide.classList.toggle('dang-hien', hien);
      slide.toggleAttribute('inert', !hien);
      slide.setAttribute('aria-hidden', String(!hien));
    });
    cacCham.forEach((cham, i) => {
      if (i === hienTai) cham.setAttribute('aria-current', 'true');
      else cham.removeAttribute('aria-current');
    });
    khoi.style.setProperty('--mau-hero', cacSlide[hienTai].dataset.mau);
  };
  const capNhatHen = () => {
    clearInterval(hen);
    hen = null;
    if (daTaiTrang && !giamDong && !reChuot && !coFocus && !document.hidden && xBatDau === null) {
      hen = setInterval(() => den(hienTai + 1), 5000);
    }
  };
  const chon = (so) => {
    den(so);
    capNhatHen();
  };

  khoi.querySelector('[data-dieu-khien-banner]').hidden = false;
  giamChuyenDong.addEventListener('change', (e) => { giamDong = e.matches; capNhatHen(); });
  khoi.querySelectorAll('[data-truoc], [data-sau]').forEach((nut) => {
    nut.hidden = false;
    nut.addEventListener('click', () => chon(hienTai + (nut.hasAttribute('data-truoc') ? -1 : 1)));
  });
  cacCham.forEach((cham) => cham.addEventListener('click', () => chon(Number(cham.dataset.den))));
  khoi.addEventListener('pointerenter', (e) => { reChuot = e.pointerType === 'mouse'; capNhatHen(); });
  khoi.addEventListener('pointerleave', () => { reChuot = false; capNhatHen(); });
  khoi.addEventListener('focusin', () => { coFocus = true; capNhatHen(); });
  khoi.addEventListener('focusout', (e) => { coFocus = khoi.contains(e.relatedTarget); capNhatHen(); });
  khoi.addEventListener('keydown', (e) => {
    if (!['ArrowLeft', 'ArrowRight'].includes(e.key)) return;
    e.preventDefault();
    const moi = hienTai + (e.key === 'ArrowLeft' ? -1 : 1);
    if (e.target.closest('.slide-hero')) cacCham[(moi + cacCham.length) % cacCham.length].focus();
    chon(moi);
  });
  document.addEventListener('visibilitychange', capNhatHen);

  khoi.addEventListener('touchstart', (e) => { xBatDau = e.touches[0].clientX; capNhatHen(); }, { passive: true });
  khoi.addEventListener('touchend', (e) => {
    if (xBatDau === null) return;
    const lech = e.changedTouches[0].clientX - xBatDau;
    if (Math.abs(lech) > 40) den(hienTai + (lech < 0 ? 1 : -1));
    xBatDau = null;
    capNhatHen();
  });
  khoi.addEventListener('touchcancel', () => { xBatDau = null; capNhatHen(); });
  if (!daTaiTrang) {
    window.addEventListener('load', () => { daTaiTrang = true; capNhatHen(); }, { once: true });
  }
  capNhatHen();
})();
