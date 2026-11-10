// Phân quyền từng người: chọn nhóm để điền sẵn ô tick, rồi tick thêm hoặc bỏ bớt cho riêng tài khoản.
(() => {
  const form = document.querySelector('[data-form-tai-khoan]');
  if (!form) return;
  const bang = JSON.parse(document.getElementById('bang-quyen-nhom').textContent);
  const oNhom = form.querySelector('[data-nhom-quyen]');
  const oVaiTro = form.querySelector('select[name="vai_tro"]');
  const cacO = [...form.querySelectorAll('input[data-ma-quyen]')];
  const tomTat = form.querySelector('[data-tom-tat-quyen]');

  const quyenCoSo = () => {
    if (oNhom.value) return new Set(bang.nhom[oNhom.value] || []);
    return new Set(bang.mac_dinh[oVaiTro.value] || []);
  };
  const capNhatNhan = () => {
    const coSo = quyenCoSo();
    let them = 0;
    let bot = 0;
    cacO.forEach((o) => {
      const khac = o.checked !== coSo.has(o.dataset.maQuyen);
      o.closest('[data-o-quyen]').querySelector('[data-nhan-khac]').hidden = !khac;
      o.closest('[data-o-quyen]').classList.toggle('khac-nhom', khac);
      if (khac && o.checked) them += 1;
      if (khac && !o.checked) bot += 1;
    });
    const coQuyen = cacO.filter((o) => o.checked).length;
    tomTat.textContent = `Đang có ${coQuyen}/${cacO.length} quyền` + (them || bot ? ` · cấp thêm ${them}, thu hồi ${bot} so với nhóm` : ' · đúng theo nhóm');
  };
  const apNhom = () => {
    const coSo = quyenCoSo();
    cacO.forEach((o) => { o.checked = coSo.has(o.dataset.maQuyen); });
    capNhatNhan();
  };

  oNhom.addEventListener('change', apNhom);
  oVaiTro.addEventListener('change', () => { if (!oNhom.value) apNhom(); });
  form.querySelector('[data-ap-nhom]').addEventListener('click', apNhom);
  form.addEventListener('change', (e) => { if (e.target.matches('input[data-ma-quyen]')) capNhatNhan(); });
  form.querySelectorAll('[data-nhom-module]').forEach((khoi) => {
    const dat = (giaTri) => { khoi.querySelectorAll('input[data-ma-quyen]').forEach((o) => { o.checked = giaTri; }); capNhatNhan(); };
    khoi.querySelector('[data-chon-het]').addEventListener('click', () => dat(true));
    khoi.querySelector('[data-bo-het]').addEventListener('click', () => dat(false));
  });
  capNhatNhan();
})();
