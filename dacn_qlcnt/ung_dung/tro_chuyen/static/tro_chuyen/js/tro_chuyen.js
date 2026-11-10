// Phòng chat: WebSocket qua Redis, tự nối lại khi mất mạng, vẽ tin dạng bong bóng,
// báo "Đã xem" theo mốc đã đọc lưu trong CSDL và đánh dấu đã đọc khi người xem thực sự nhìn thấy.
(() => {
  const khung = document.querySelector('[data-tro-chuyen]');
  if (!khung) return;
  const form = khung.querySelector('[data-form-tin]');
  const oNhap = form.querySelector('textarea');
  const nut = form.querySelector('button');
  const lichSu = khung.querySelector('[data-cac-tin]');
  const trangThai = khung.querySelector('[data-trang-thai]');
  const ben = khung.dataset.ben; // "khach" hoặc "nha_thuoc"
  const toiLaKhach = ben === 'khach';
  const giaoThuc = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const CHU_KY_KIEM_TRA = 30000;
  const HAN_PHAN_HOI = 10000;
  let socket = null;
  let dangGui = null;
  let thuLai = 1000;
  let biChan = false;
  let henThuLai;
  let henKiemTra;
  let henPhanHoi;
  let cacTin = [];
  // Mốc đã đọc của hai phía; mốc của mình quyết định vạch "Tin mới", mốc của họ quyết định "Đã xem".
  const moc = {
    khach: Number(khung.dataset.khachDaDoc) || 0,
    nha_thuoc: Number(khung.dataset.nhaThuocDaDoc) || 0,
  };
  let mocVachMoi = null;
  let daGuiDaDoc = 0;

  const laCuaToi = tin => tin.la_khach === toiLaKhach;
  const gio = iso =>
    new Date(iso).toLocaleString('vi-VN', {hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit'});
  const tao = (the, lop, chu) => {
    const phanTu = document.createElement(the);
    if (lop) phanTu.className = lop;
    if (chu != null) phanTu.textContent = chu;
    return phanTu;
  };

  function ve() {
    const benHo = toiLaKhach ? 'nha_thuoc' : 'khach';
    const tinCuoiCuaToi = [...cacTin].reverse().find(laCuaToi);
    const cacDong = [];
    cacTin.forEach((tin, i) => {
      if (mocVachMoi !== null && tin.id_tin_nhan === mocVachMoi) {
        cacDong.push(tao('li', 'vach-tin-moi', 'Tin mới'));
      }
      const cuaToi = laCuaToi(tin);
      const dong = tao('li', `tin-chat ${cuaToi ? 'cua-toi' : 'cua-ho'}`);
      dong.dataset.idTin = tin.id_tin_nhan;
      const truoc = cacTin[i - 1];
      // Gộp các tin liên tiếp cùng người gửi: chỉ hiện tên ở tin đầu nhóm.
      if (!cuaToi && (!truoc || truoc.nguoi_gui_id !== tin.nguoi_gui_id)) {
        dong.append(tao('span', 'ten-gui', tin.la_khach ? tin.ten_nguoi_gui : `${tin.ten_nguoi_gui} · Nhà thuốc`));
      }
      const bong = tao('div', 'bong-tin');
      tin.noi_dung.split('\n').forEach((doan, j) => {
        if (j) bong.append(document.createElement('br'));
        bong.append(doan);
      });
      const thoiGian = tao('time', 'gio-tin', gio(tin.thoi_diem));
      thoiGian.dateTime = tin.thoi_diem;
      dong.append(bong, thoiGian);
      if (tinCuoiCuaToi && tin.id_tin_nhan === tinCuoiCuaToi.id_tin_nhan) {
        const daXem = moc[benHo] >= tin.id_tin_nhan;
        dong.append(tao('span', `trang-thai-tin${daXem ? ' da-xem' : ''}`, daXem ? 'Đã xem' : 'Đã gửi'));
      }
      cacDong.push(dong);
    });
    if (!cacDong.length) {
      cacDong.push(tao('li', 'chat-trong', lichSu.querySelector('[data-chat-trong]')?.textContent || 'Chưa có tin nhắn.'));
    }
    const oCuoi = lichSu.scrollHeight - lichSu.scrollTop - lichSu.clientHeight < 80;
    lichSu.replaceChildren(...cacDong);
    if (oCuoi || !ve.daCuon) {
      lichSu.scrollTop = lichSu.scrollHeight;
      ve.daCuon = true;
    }
  }

  function themTin(tin) {
    if (cacTin.some(t => t.id_tin_nhan === tin.id_tin_nhan)) return;
    cacTin.push(tin);
    cacTin.sort((a, b) => a.id_tin_nhan - b.id_tin_nhan);
    if (cacTin.length > 100) cacTin = cacTin.slice(-100);
  }

  // Chỉ báo đã đọc khi trang đang hiện và người dùng ở trong cửa sổ này.
  function baoDaDoc() {
    if (document.hidden || socket?.readyState !== WebSocket.OPEN) return;
    const tinCuoiCuaHo = [...cacTin].reverse().find(tin => !laCuaToi(tin));
    if (!tinCuoiCuaHo || tinCuoiCuaHo.id_tin_nhan <= Math.max(moc[ben], daGuiDaDoc)) return;
    daGuiDaDoc = tinCuoiCuaHo.id_tin_nhan;
    socket.send(JSON.stringify({loai: 'da_doc', id_tin: tinCuoiCuaHo.id_tin_nhan}));
  }

  function matKetNoi() {
    const cu = socket;
    socket = null;
    clearTimeout(henKiemTra);
    clearTimeout(henPhanHoi);
    clearTimeout(henThuLai);
    nut.disabled = true;
    if (cu && cu.readyState <= WebSocket.OPEN) cu.close();
    if (biChan) {
      trangThai.textContent = 'Bạn không còn quyền truy cập cuộc trò chuyện này.';
    } else if (!navigator.onLine) {
      trangThai.textContent = 'Mất mạng. Sẽ tự kết nối lại khi có mạng.';
    } else {
      trangThai.textContent = 'Mất kết nối. Đang thử lại…';
      henThuLai = setTimeout(ketNoi, thuLai);
      thuLai = Math.min(thuLai * 2, 15000);
    }
  }

  function choPhanHoi() {
    clearTimeout(henPhanHoi);
    henPhanHoi = setTimeout(matKetNoi, HAN_PHAN_HOI);
  }

  function henKiemTraKetNoi(hienTai) {
    clearTimeout(henPhanHoi);
    clearTimeout(henKiemTra);
    // Mạng có thể đã mất dù trình duyệt chưa phát sự kiện close.
    henKiemTra = setTimeout(() => {
      if (hienTai !== socket || hienTai.readyState !== WebSocket.OPEN) return;
      hienTai.send(JSON.stringify({loai: 'kiem_tra_ket_noi'}));
      choPhanHoi();
    }, CHU_KY_KIEM_TRA);
  }

  function ketNoi() {
    if (socket || biChan || !navigator.onLine) return;
    clearTimeout(henThuLai);
    trangThai.textContent = 'Đang kết nối…';
    const hienTai = new WebSocket(`${giaoThuc}//${location.host}/ws/tro-chuyen/${khung.dataset.maPhong}/`);
    socket = hienTai;
    choPhanHoi();
    hienTai.addEventListener('message', suKien => {
      if (hienTai !== socket) return;
      const ketQua = JSON.parse(suKien.data);
      if (ketQua.loai === 'lich_su') {
        cacTin = [];
        ketQua.cac_tin.forEach(themTin);
        moc.khach = ketQua.khach_da_doc || 0;
        moc.nha_thuoc = ketQua.nha_thuoc_da_doc || 0;
        if (mocVachMoi === null) {
          const dauChuaDoc = cacTin.find(tin => !laCuaToi(tin) && tin.id_tin_nhan > moc[ben]);
          mocVachMoi = dauChuaDoc ? dauChuaDoc.id_tin_nhan : -1;
        }
        thuLai = 1000;
        trangThai.textContent = '';
        nut.disabled = Boolean(dangGui) || !oNhap.value.trim();
        if (dangGui) hienTai.send(JSON.stringify(dangGui));
        henKiemTraKetNoi(hienTai);
        ve();
        baoDaDoc();
      }
      if (ketQua.loai === 'ket_noi_con_song') henKiemTraKetNoi(hienTai);
      if (ketQua.tin) {
        themTin(ketQua.tin);
        ve();
        if (!laCuaToi(ketQua.tin)) baoDaDoc();
      }
      if (ketQua.loai === 'da_doc') {
        moc[ketQua.ben] = Math.max(moc[ketQua.ben], ketQua.id_tin);
        ve();
      }
      if (ketQua.loai === 'da_luu' && ketQua.ma_tin_nhan === dangGui?.ma_tin_nhan) {
        if (oNhap.value.trim() === dangGui.noi_dung) {
          oNhap.value = '';
          coGian();
        }
        dangGui = null;
        nut.disabled = true;
        trangThai.textContent = '';
      }
      if (ketQua.loai === 'loi') {
        trangThai.textContent = ketQua.thong_bao;
        dangGui = null;
        nut.disabled = !oNhap.value.trim();
      }
    });
    hienTai.addEventListener('close', suKien => {
      if (hienTai !== socket) return;
      biChan = suKien.code === 4403;
      matKetNoi();
    });
  }

  function guiTin() {
    const noiDung = oNhap.value.trim();
    if (dangGui || !noiDung || socket?.readyState !== WebSocket.OPEN) return;
    dangGui = {ma_tin_nhan: crypto.randomUUID(), noi_dung: noiDung};
    nut.disabled = true;
    trangThai.textContent = 'Đang gửi…';
    socket.send(JSON.stringify(dangGui));
  }

  // Ô nhập tự cao theo nội dung, tối đa khoảng 6 dòng.
  function coGian() {
    oNhap.style.height = 'auto';
    oNhap.style.height = `${Math.min(oNhap.scrollHeight, 150)}px`;
  }

  form.addEventListener('submit', suKien => {
    suKien.preventDefault();
    guiTin();
  });
  oNhap.addEventListener('keydown', suKien => {
    if (suKien.key === 'Enter' && !suKien.shiftKey && !suKien.isComposing) {
      suKien.preventDefault();
      guiTin();
    }
  });
  oNhap.addEventListener('input', () => {
    coGian();
    nut.disabled = Boolean(dangGui) || !oNhap.value.trim() || socket?.readyState !== WebSocket.OPEN;
  });
  khung.querySelectorAll('[data-goi-y-nhanh] button').forEach(nutGoiY =>
    nutGoiY.addEventListener('click', () => {
      oNhap.value = nutGoiY.dataset.cau;
      coGian();
      oNhap.focus();
      nut.disabled = socket?.readyState !== WebSocket.OPEN;
    }),
  );
  document.addEventListener('visibilitychange', baoDaDoc);
  window.addEventListener('focus', baoDaDoc);
  window.addEventListener('offline', matKetNoi);
  window.addEventListener('online', ketNoi);
  if (navigator.onLine) ketNoi();
  else matKetNoi();
})();
