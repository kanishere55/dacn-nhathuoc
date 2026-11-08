(() => {
  const khung = document.querySelector("[data-vi-tri-chi-nhanh]");
  const viTri = [Number(khung.dataset.viDo), Number(khung.dataset.kinhDo)];
  const banDo = L.map(khung).setView(viTri, 16);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(banDo);
  L.marker(viTri).addTo(banDo);
})();
