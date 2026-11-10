// Bảng dòng hàng của phiếu kho: thêm dòng từ mẫu, bỏ dòng (đánh dấu DELETE để giữ chỉ số formset),
// đánh số lại các dòng đang hiện và gắn ô chọn có tìm kiếm cho dòng mới.
document.querySelectorAll('[data-formset]').forEach(form => {
  const than = form.querySelector('[data-cac-dong]');
  const tong = form.querySelector('[name$="-TOTAL_FORMS"]');
  const mau = form.querySelector('[data-dong-rong]');
  const dem = form.querySelector('[data-dem-dong]');
  if (!than || !tong || !mau) return;

  const cacDongHien = () => [...than.querySelectorAll('[data-dong]')].filter(dong => !dong.hidden);
  const capNhat = () => {
    const hien = cacDongHien();
    hien.forEach((dong, i) => {
      dong.querySelector('[data-stt]').textContent = i + 1;
    });
    if (dem) dem.textContent = `${hien.length} dòng`;
  };

  form.querySelector('[data-them-dong]')?.addEventListener('click', () => {
    if (Number(tong.value) >= 50) return;
    const tam = document.createElement('tbody');
    tam.innerHTML = mau.innerHTML.replaceAll('__prefix__', tong.value);
    const dongMoi = tam.querySelector('[data-dong]');
    than.append(dongMoi);
    tong.value = String(Number(tong.value) + 1);
    if (typeof ganChonCoTim === 'function') ganChonCoTim(dongMoi);
    window.lucide?.createIcons();
    capNhat();
    dongMoi.querySelector('input:not([type=hidden]), select')?.focus();
  });

  than.addEventListener('click', suKien => {
    const nut = suKien.target.closest('[data-bo-dong]');
    if (!nut) return;
    const dong = nut.closest('[data-dong]');
    const xoa = dong.querySelector('[name$="-DELETE"]');
    if (xoa) xoa.checked = true;
    dong.hidden = true;
    // Dòng lỗi đi kèm (nếu có) cũng ẩn theo.
    if (dong.nextElementSibling?.classList.contains('dong-loi')) dong.nextElementSibling.hidden = true;
    capNhat();
  });

  capNhat();
});
