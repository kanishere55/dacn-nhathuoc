// Tính chênh lệch ngay khi nhập số đếm; chỉ để xem trước, server tính lại khi lưu.
(() => {
  const form = document.querySelector('[data-kiem-ke]');
  if (!form) return;
  const tomTat = form.querySelector('[data-tom-tat-kiem-ke]');
  const capNhat = () => {
    let soLo = 0;
    let lech = 0;
    form.querySelectorAll('[data-dong-kiem-ke]').forEach(dong => {
      const o = dong.querySelector('input[name$="-so_luong_thuc_te"]');
      const soSach = Number(dong.querySelector('[data-so-sach]').dataset.soSach);
      const oChenh = dong.querySelector('[data-chenh]');
      oChenh.className = 'o-so';
      if (o.value === '') {
        oChenh.textContent = '–';
        return;
      }
      soLo += 1;
      const chenh = Number(o.value) - soSach;
      if (chenh) lech += 1;
      oChenh.textContent = chenh > 0 ? `+${chenh.toLocaleString('vi-VN')}` : chenh.toLocaleString('vi-VN');
      oChenh.classList.add(chenh > 0 ? 'thua' : chenh < 0 ? 'thieu' : 'khop');
    });
    tomTat.textContent = soLo ? `Đã đếm ${soLo} lô, ${lech} lô lệch sổ` : 'Chưa nhập lô nào';
  };
  form.addEventListener('input', capNhat);
  capNhat();
})();
