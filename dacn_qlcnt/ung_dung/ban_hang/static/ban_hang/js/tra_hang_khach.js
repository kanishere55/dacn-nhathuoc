// Form trả hàng: xem trước ảnh minh chứng ngay khi chọn, bỏ từng ảnh, kéo thả, giới hạn số ảnh.
(() => {
  const form = document.querySelector('[data-form-tra-hang]');
  if (!form) return;
  const oAnh = form.querySelector('[data-o-anh]');
  const khungChon = form.querySelector('[data-khung-chon]');
  const xemTruoc = form.querySelector('[data-xem-truoc]');
  const thongBao = form.querySelector('[data-thong-bao-anh]');
  const toiDa = Number(form.dataset.toiDa || 4);
  let cacTep = [];

  const dongBo = () => {
    // Ô tệp gửi đúng danh sách đang xem trước.
    const dt = new DataTransfer();
    cacTep.forEach((tep) => dt.items.add(tep));
    oAnh.files = dt.files;
  };
  const ve = () => {
    xemTruoc.replaceChildren();
    cacTep.forEach((tep, so) => {
      const li = document.createElement('li');
      const anh = document.createElement('img');
      anh.src = URL.createObjectURL(tep);
      anh.alt = `Ảnh ${so + 1}`;
      anh.addEventListener('load', () => URL.revokeObjectURL(anh.src), { once: true });
      const ten = document.createElement('span');
      ten.textContent = tep.name;
      const bo = document.createElement('button');
      bo.type = 'button';
      bo.textContent = '×';
      bo.setAttribute('aria-label', `Bỏ ảnh ${tep.name}`);
      bo.addEventListener('click', () => { cacTep.splice(so, 1); dongBo(); ve(); });
      li.append(anh, ten, bo);
      xemTruoc.append(li);
    });
    thongBao.textContent = cacTep.length ? `Đã chọn ${cacTep.length}/${toiDa} ảnh.` : '';
    thongBao.classList.remove('loi');
  };
  const them = (danhSach) => {
    const hopLe = [...danhSach].filter((t) => t.type.startsWith('image/'));
    const conCho = toiDa - cacTep.length;
    cacTep.push(...hopLe.slice(0, Math.max(conCho, 0)));
    dongBo();
    ve();
    if (hopLe.length > conCho) {
      thongBao.textContent = `Chỉ gửi tối đa ${toiDa} ảnh; đã bỏ bớt ảnh dư.`;
      thongBao.classList.add('loi');
    }
  };
  oAnh.addEventListener('change', () => {
    const moi = [...oAnh.files];
    them(moi);
  });
  ['dragenter', 'dragover'].forEach((s) => khungChon.addEventListener(s, (e) => { e.preventDefault(); khungChon.classList.add('dang-keo'); }));
  ['dragleave', 'drop'].forEach((s) => khungChon.addEventListener(s, (e) => { e.preventDefault(); khungChon.classList.remove('dang-keo'); }));
  khungChon.addEventListener('drop', (e) => them(e.dataTransfer.files));
  // Kiểm tra ngay trên trình duyệt để khách không phải chọn lại ảnh vì một ô bỏ trống
  // (trình duyệt không cho điền lại ô tệp sau khi máy chủ trả lỗi). Máy chủ vẫn kiểm tra lại toàn bộ.
  const baoLoi = (o, noiDung) => {
    const cu = o.closest('div, fieldset, li')?.querySelector(':scope > .loi-truong[data-loi-tam]');
    cu?.remove();
    if (!noiDung) return;
    const p = document.createElement('p');
    p.className = 'loi-truong';
    p.dataset.loiTam = '';
    p.textContent = noiDung;
    o.closest('div, fieldset, li').append(p);
  };
  const giaTri = (ten) => (form.elements[ten]?.value || '').trim();
  form.addEventListener('submit', (e) => {
    form.querySelectorAll('[data-loi-tam]').forEach((p) => p.remove());
    const loi = [];
    const cacSoLuong = [...form.querySelectorAll('input[name^="so_luong_"]')];
    if (!cacSoLuong.some((o) => Number(o.value) > 0)) loi.push([cacSoLuong[0], 'Nhập số lượng cho ít nhất một thuốc cần trả.']);
    if (!form.querySelector('[name="ly_do"]:checked')) loi.push([form.querySelector('[name="ly_do"]'), 'Chọn lý do trả hàng.']);
    if (!giaTri('mo_ta')) loi.push([form.elements.mo_ta, 'Mô tả tình trạng thuốc.']);
    const cach = form.querySelector('[name="hinh_thuc_hoan_tien"]:checked')?.value;
    if (cach === 'chuyen_khoan') {
      if (!giaTri('ten_ngan_hang')) loi.push([form.elements.ten_ngan_hang, 'Nhập ngân hàng nhận tiền hoàn.']);
      const soTk = giaTri('so_tai_khoan').replace(/[\s.-]/g, '');
      if (!/^[0-9]{6,19}$/.test(soTk)) loi.push([form.elements.so_tai_khoan, 'Số tài khoản gồm 6 đến 19 chữ số.']);
      if (!giaTri('ten_chu_tai_khoan')) loi.push([form.elements.ten_chu_tai_khoan, 'Nhập tên chủ tài khoản.']);
    } else if (cach === 'momo') {
      const so = giaTri('so_dien_thoai_momo').replace(/[\s.\-()]/g, '').replace(/^\+?84(?=[0-9]{9,10}$)/, '0');
      if (!/^0[0-9]{9,10}$/.test(so)) loi.push([form.elements.so_dien_thoai_momo, 'Nhập số điện thoại đăng ký ví MoMo (10 chữ số).']);
    }
    loi.forEach(([o, noiDung]) => o && baoLoi(o, noiDung));
    if (!cacTep.length) {
      thongBao.textContent = 'Cần ít nhất một ảnh chụp tình trạng thuốc.';
      thongBao.classList.add('loi');
      loi.push([khungChon]);
    }
    if (loi.length) {
      e.preventDefault();
      loi[0][0]?.scrollIntoView({ block: 'center' });
      loi[0][0]?.focus?.({ preventScroll: true });
    }
  });
})();
