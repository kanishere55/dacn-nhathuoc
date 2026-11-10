(() => {
  const khung = document.querySelector("[data-vi-tri-chi-nhanh]");
  const viTri = [Number(khung.dataset.viDo), Number(khung.dataset.kinhDo)];
  const banDo = window.taoBanDoNhaThuoc(khung, viTri, 16);
  L.marker(viTri, { icon: window.bieuTuongNhaThuoc({ noiBat: true }), alt: khung.getAttribute('aria-label') }).addTo(banDo);
})();
