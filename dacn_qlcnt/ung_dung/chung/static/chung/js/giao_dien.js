document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) window.lucide.createIcons();
});
document.addEventListener("htmx:afterSwap", () => {
  if (window.lucide) window.lucide.createIcons();
});
