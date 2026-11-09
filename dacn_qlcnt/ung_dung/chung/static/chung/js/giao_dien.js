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
