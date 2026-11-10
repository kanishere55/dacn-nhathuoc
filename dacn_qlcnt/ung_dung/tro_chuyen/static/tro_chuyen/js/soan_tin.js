// Form gửi tin đầu tiên (hỏi dược sĩ, nhắn về đơn): bấm mẫu câu để điền, Enter để gửi,
// khóa nút sau khi bấm để không tạo hai tin vì bấm hai lần.
(() => {
  document.querySelectorAll('[data-soan-tin]').forEach(form => {
    const oNhap = form.querySelector('textarea');
    const nut = form.querySelector('button[type=submit]');
    form.querySelectorAll('[data-goi-y-nhanh] button').forEach(nutGoiY =>
      nutGoiY.addEventListener('click', () => {
        oNhap.value = nutGoiY.dataset.cau;
        oNhap.focus();
      }),
    );
    oNhap?.addEventListener('keydown', suKien => {
      if (suKien.key === 'Enter' && !suKien.shiftKey && !suKien.isComposing) {
        suKien.preventDefault();
        form.requestSubmit();
      }
    });
    form.addEventListener('submit', () => {
      nut.disabled = true;
      nut.setAttribute('aria-busy', 'true');
    });
  });
})();
