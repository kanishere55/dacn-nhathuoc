// Băng chuyền banner trang chủ: tự chuyển 5 giây, dừng khi rê chuột/focus/ẩn tab,
// vuốt trên điện thoại, phím mũi tên; tôn trọng prefers-reduced-motion.
(() => {
  const khoi = document.querySelector('[data-bang-chuyen]');
  if (!khoi) return;
  const cacSlide = [...khoi.querySelectorAll('.slide-hero')];
  const cacCham = [...khoi.querySelectorAll('[data-den]')];
  if (cacSlide.length < 2) return;
  const giamChuyenDong = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let hienTai = 0;
  let hen = null;

  const den = (so) => {
    hienTai = (so + cacSlide.length) % cacSlide.length;
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
  const dung = () => { clearInterval(hen); hen = null; };
  const chay = () => {
    if (giamChuyenDong || hen) return;
    hen = setInterval(() => den(hienTai + 1), 5000);
  };
  const datLai = () => { dung(); chay(); };

  khoi.querySelector('[data-truoc]')?.addEventListener('click', () => { den(hienTai - 1); datLai(); });
  khoi.querySelector('[data-sau]')?.addEventListener('click', () => { den(hienTai + 1); datLai(); });
  cacCham.forEach((cham) => cham.addEventListener('click', () => { den(Number(cham.dataset.den)); datLai(); }));
  khoi.addEventListener('mouseenter', dung);
  khoi.addEventListener('mouseleave', chay);
  khoi.addEventListener('focusin', dung);
  khoi.addEventListener('focusout', chay);
  khoi.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') { den(hienTai - 1); datLai(); }
    if (e.key === 'ArrowRight') { den(hienTai + 1); datLai(); }
  });
  document.addEventListener('visibilitychange', () => (document.hidden ? dung() : chay()));

  let xBatDau = null;
  khoi.addEventListener('touchstart', (e) => { xBatDau = e.touches[0].clientX; dung(); }, { passive: true });
  khoi.addEventListener('touchend', (e) => {
    if (xBatDau === null) return;
    const lech = e.changedTouches[0].clientX - xBatDau;
    if (Math.abs(lech) > 40) den(hienTai + (lech < 0 ? 1 : -1));
    xBatDau = null;
    chay();
  });
  chay();
})();
