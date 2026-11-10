// Quản lý ảnh của thuốc/chi nhánh ngay trên trang sửa: xem trước ảnh vừa chọn, tải lên, xóa và
// đặt ảnh đại diện bằng fetch nên trang không tải lại và không nhảy lên đầu trang.
(() => {
  const vung = document.querySelector('[data-vung-anh]');
  if (!vung) return;
  const luoi = vung.querySelector('[data-luoi]');
  const form = vung.querySelector('[data-form-tai-anh]');
  const oChon = form.querySelector('input[type=file]');
  const khungChon = form.querySelector('[data-khung-chon]');
  const xemTruoc = vung.querySelector('[data-xem-truoc]');
  const nutTai = form.querySelector('[data-nut-tai]');
  const thongBao = vung.querySelector('[data-thong-bao]');
  const demAnh = vung.querySelector('[data-dem-anh]');
  const toiDa = Number(vung.dataset.toiDa || 8);
  const BYTE_MOI_LAN = 8 * 1024 * 1024; // máy chủ giới hạn 10 MB mỗi yêu cầu
  const csrf = form.querySelector('input[name=csrfmiddlewaretoken]').value;
  let cacTep = [];
  let dangXuLy = false;

  const bao = (chu, loi = false) => {
    thongBao.textContent = chu;
    thongBao.classList.toggle('loi', loi);
  };
  const kichThuoc = (byte) => (byte > 1048576 ? `${(byte / 1048576).toFixed(1)} MB` : `${Math.ceil(byte / 1024)} KB`);
  const soAnhHienCo = () => luoi.querySelectorAll('li[data-id]').length;
  const capNhatTrangThai = () => {
    demAnh.textContent = `${soAnhHienCo()}/${toiDa} ảnh`;
    nutTai.disabled = dangXuLy || cacTep.length === 0;
    nutTai.textContent = cacTep.length ? `Tải ${cacTep.length} ảnh lên` : 'Tải ảnh lên';
  };

  const veXemTruoc = () => {
    xemTruoc.replaceChildren();
    cacTep.forEach((tep, so) => {
      const li = document.createElement('li');
      const anh = document.createElement('img');
      anh.src = URL.createObjectURL(tep);
      anh.alt = `Xem trước ${tep.name}`;
      anh.addEventListener('load', () => URL.revokeObjectURL(anh.src), { once: true });
      const ten = document.createElement('span');
      ten.textContent = `${tep.name} · ${kichThuoc(tep.size)}`;
      ten.title = ten.textContent;
      const bo = document.createElement('button');
      bo.type = 'button';
      bo.textContent = '×';
      bo.title = 'Bỏ ảnh này khỏi danh sách chờ tải';
      bo.setAttribute('aria-label', `Bỏ ${tep.name}`);
      bo.addEventListener('click', () => { cacTep.splice(so, 1); veXemTruoc(); capNhatTrangThai(); });
      li.append(anh, ten, bo);
      xemTruoc.appendChild(li);
    });
    capNhatTrangThai();
  };

  const themTep = (danhSach) => {
    const hopLe = [...danhSach].filter((t) => t.type.startsWith('image/'));
    if (hopLe.length < danhSach.length) bao('Đã bỏ qua tệp không phải ảnh.', true);
    else bao('');
    const conChua = toiDa - soAnhHienCo() - cacTep.length;
    if (hopLe.length > conChua) {
      bao(`Mỗi mục chỉ lưu tối đa ${toiDa} ảnh, còn chỗ cho ${Math.max(conChua, 0)} ảnh nữa.`, true);
    }
    cacTep.push(...hopLe.slice(0, Math.max(conChua, 0)));
    oChon.value = '';
    veXemTruoc();
  };

  oChon.addEventListener('change', () => themTep(oChon.files));
  ['dragenter', 'dragover'].forEach((s) => khungChon.addEventListener(s, (e) => { e.preventDefault(); khungChon.classList.add('dang-keo'); }));
  ['dragleave', 'drop'].forEach((s) => khungChon.addEventListener(s, (e) => { e.preventDefault(); khungChon.classList.remove('dang-keo'); }));
  khungChon.addEventListener('drop', (e) => themTep(e.dataTransfer.files));

  // Vẽ lại lưới ảnh từ danh sách máy chủ trả về.
  const veLuoi = (cacAnh) => {
    luoi.replaceChildren();
    if (!cacAnh.length) {
      const trong = document.createElement('li');
      trong.className = 'khong-co-anh';
      trong.textContent = 'Chưa có ảnh. Website sẽ hiện biểu tượng thay thế.';
      luoi.appendChild(trong);
    }
    cacAnh.forEach((anh, so) => {
      const li = document.createElement('li');
      li.dataset.id = anh.id;
      const hinh = document.createElement('img');
      hinh.src = anh.url;
      hinh.alt = `Ảnh ${so + 1}`;
      hinh.width = anh.rong;
      hinh.height = anh.cao;
      li.appendChild(hinh);
      if (anh.nguon) {
        const nguon = document.createElement('small');
        nguon.className = 'ghi-nguon';
        nguon.textContent = `Nguồn: ${anh.nguon}`;
        li.appendChild(nguon);
      }
      const khu = document.createElement('div');
      if (anh.la_dai_dien) {
        const nhan = document.createElement('span');
        nhan.className = 'nhan-trang-thai';
        nhan.textContent = 'Ảnh đại diện';
        khu.appendChild(nhan);
      } else {
        khu.appendChild(taoNut('Làm ảnh đại diện', anh.url_dai_dien));
      }
      khu.appendChild(taoNut('Xóa', anh.url_xoa, 'Xóa ảnh này?'));
      li.appendChild(khu);
      luoi.appendChild(li);
    });
    capNhatTrangThai();
  };
  const taoNut = (nhan, url, hoiXacNhan) => {
    const f = document.createElement('form');
    f.method = 'post';
    f.action = url;
    f.dataset.anhHanhDong = '1';
    if (hoiXacNhan) f.dataset.hoiXacNhan = hoiXacNhan;
    const nut = document.createElement('button');
    nut.className = 'nut nut-phu';
    nut.type = 'submit';
    nut.textContent = nhan;
    f.appendChild(nut);
    return f;
  };

  // Body rỗng gửi bằng URLSearchParams (x-www-form-urlencoded); FormData rỗng tạo multipart không phần nên máy chủ trả 400.
  const guiYeuCau = async (url, thanBody = new URLSearchParams()) => {
    try {
      const phanHoi = await fetch(url, {
        method: 'POST', body: thanBody, credentials: 'same-origin',
        headers: { 'X-CSRFToken': csrf, 'X-Requested-With': 'XMLHttpRequest', Accept: 'application/json' },
      });
      let du = {};
      try { du = await phanHoi.json(); } catch (_) { du = { ok: false, thong_diep: `Máy chủ trả lỗi ${phanHoi.status}.` }; }
      return du;
    } catch (_) {
      return { ok: false, mat_ket_noi: true, thong_diep: 'Mất kết nối tới máy chủ. Kiểm tra mạng rồi thử lại; các ảnh đã chọn vẫn được giữ.' };
    }
  };

  // Xóa / đặt ảnh đại diện: chặn gửi form thường, gọi fetch và vẽ lại lưới tại chỗ.
  vung.addEventListener('submit', async (e) => {
    const f = e.target.closest('form[data-anh-hanh-dong]');
    if (!f) return;
    e.preventDefault();
    if (f.dataset.hoiXacNhan && !window.confirm(f.dataset.hoiXacNhan)) return;
    if (dangXuLy) return;
    dangXuLy = true;
    f.querySelector('button').disabled = true;
    const du = await guiYeuCau(f.action);
    dangXuLy = false;
    f.querySelector('button').disabled = false;
    if (du.cac_anh) veLuoi(du.cac_anh);
    bao(du.thong_diep || '', !du.ok);
    capNhatTrangThai();
  });

  // Tải lên theo từng đợt không quá 8 MB để vượt được giới hạn một yêu cầu.
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!cacTep.length || dangXuLy) return;
    dangXuLy = true;
    capNhatTrangThai();
    const cacDot = [];
    let dot = []; let tong = 0;
    cacTep.forEach((tep) => {
      if (dot.length && tong + tep.size > BYTE_MOI_LAN) { cacDot.push(dot); dot = []; tong = 0; }
      dot.push(tep); tong += tep.size;
    });
    if (dot.length) cacDot.push(dot);
    let daTai = 0;
    for (const nhom of cacDot) {
      bao(`Đang tải ${daTai + nhom.length}/${cacTep.length} ảnh…`);
      const du = new FormData();
      nhom.forEach((tep) => du.append('cac_anh', tep));
      const ketQua = await guiYeuCau(form.action, du);
      if (ketQua.cac_anh) veLuoi(ketQua.cac_anh);
      if (!ketQua.ok) {
        dangXuLy = false;
        cacTep = cacTep.slice(daTai);
        veXemTruoc();
        bao(ketQua.thong_diep || 'Không tải được ảnh.', true);
        return;
      }
      daTai += nhom.length;
    }
    dangXuLy = false;
    cacTep = [];
    veXemTruoc();
    bao(`Đã tải ${daTai} ảnh lên.`);
  });

  capNhatTrangThai();
})();
