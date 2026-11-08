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
