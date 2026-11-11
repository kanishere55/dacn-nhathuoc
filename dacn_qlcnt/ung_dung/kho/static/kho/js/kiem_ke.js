// Tính chênh lệch ngay khi nhập số đếm; chỉ để xem trước, server tính lại khi lưu.
// Đã nhập số đếm mà bấm chuyển trang hoặc rời trang thì hỏi lại để không mất số đã đếm.
(() => {
  const form = document.querySelector('[data-kiem-ke]');
  if (!form) return;
  const tomTat = form.querySelector('[data-tom-tat-kiem-ke]');
  let daNhap = false;
  let dangGui = false;
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
    return soLo;
  };
  form.addEventListener('input', () => {
    daNhap = capNhat() > 0;
  });
  daNhap = capNhat() > 0;

  const canhBao = 'Số đã đếm trên trang này chưa được lưu và sẽ mất. Vẫn chuyển trang?';
  document.querySelectorAll('[data-roi-trang]').forEach(lienKet => {
    lienKet.addEventListener('click', suKien => {
      if (daNhap && !window.confirm(canhBao)) suKien.preventDefault();
      else daNhap = false;
    });
  });
  window.addEventListener('beforeunload', suKien => {
    if (!daNhap || dangGui) return;
    suKien.preventDefault();
    suKien.returnValue = '';
  });
  form.addEventListener('submit', () => {
    dangGui = true;
    const nut = form.querySelector('[data-nut-luu]');
    if (nut) {
      nut.disabled = true;
      nut.lastChild.textContent = 'Đang lưu…';
    }
  });
  window.addEventListener('pageshow', () => {
    const nut = form.querySelector('[data-nut-luu]');
    if (nut?.disabled) {
      nut.disabled = false;
      nut.lastChild.textContent = 'Lưu phiếu kiểm kê';
    }
    dangGui = false;
  });
})();
