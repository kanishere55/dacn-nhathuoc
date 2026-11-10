// Cuộc trò chuyện: WebSocket qua Redis, tự nối lại khi mất mạng, vẽ tin dạng bong bóng,
// báo "Đã xem" theo mốc đã đọc lưu trong CSDL và đánh dấu đã đọc khi người xem thực sự nhìn thấy.
// Cuộc trò chuyện dài chỉ nạp 30 tin gần nhất; "Xem tin cũ hơn" tải tiếp từng trang qua HTTP.
// Tin chỉ có chữ đi qua WebSocket; tin kèm ảnh gửi multipart qua HTTP rồi máy chủ phát lại qua
// Redis. Thẻ "Bạn đang hỏi về sản phẩm/đơn này" (nếu có) gắn vào tin kế tiếp rồi tự biến mất.
// Câu hỏi gợi ý nằm cuối luồng tin và ẩn ngay khi khách gửi tin; lưu ý tư vấn có nút X để ẩn.
(() => {
  const khung = document.querySelector('[data-tro-chuyen]');
  if (!khung) return;
  const form = khung.querySelector('[data-form-tin]');
  const oNhap = form.querySelector('textarea');
  const nut = form.querySelector('.nut-gui-tin');
  const theCho = form.querySelector('[data-the-cho]');
  const hopXemAnh = khung.querySelector('[data-hop-xem-anh]');
  const lichSu = khung.querySelector('[data-cac-tin]');
  const trangThai = khung.querySelector('[data-trang-thai]');
  // Lưu ý tư vấn ở đầu cuộc trò chuyện (chỉ phía khách) và nút (i) mở lại khi đã ẩn.
  const luuY = document.querySelector('[data-luu-y]');
  const nutMoLuuY = document.querySelector('[data-mo-luu-y]');
  // Dòng câu hỏi gợi ý do server vẽ sẵn; giữ lại để mỗi lần vẽ lại vẫn đặt ở cuối luồng tin.
  let dongGoiY = lichSu.querySelector('[data-goi-y-trong-chat]');
  const ben = khung.dataset.ben; // "khach" hoặc "nha_thuoc"
  const toiLaKhach = ben === 'khach';
  const giaoThuc = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const CHU_KY_KIEM_TRA = 30000;
  const HAN_PHAN_HOI = 10000;
  let socket = null;
  let dangGui = null;
  let dangGuiAnh = false;
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
  let conTinCu = khung.dataset.conTinCu === '1';
  let dangTaiTinCu = false;

  const laCuaToi = tin => tin.la_khach === toiLaKhach;
  const urlAnh = id => khung.dataset.urlAnh.replace(/0\/$/, `${id}/`);
  const gio = iso =>
    new Date(iso).toLocaleString('vi-VN', {hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit'});
  const tao = (the, lop, chu) => {
    const phanTu = document.createElement(the);
    if (lop) phanTu.className = lop;
    if (chu != null) phanTu.textContent = chu;
    return phanTu;
  };

  function baoLoiAnh(chu) {
    if (chu || trangThai.dataset.loiAnh) trangThai.textContent = chu;
    trangThai.dataset.loiAnh = chu ? '1' : '';
  }

  const boAnh = window.taoBoChonAnh({
    oChon: form.querySelector('[data-chon-anh]'),
    vung: form.querySelector('[data-xem-truoc-anh]'),
    khiDoi: () => capNhatNut(),
    baoLoi: baoLoiAnh,
  });

  // Gửi được khi có chữ hoặc ảnh; tin chữ cần WebSocket đang mở, tin ảnh đi HTTP.
  function capNhatNut() {
    const coNoiDung = Boolean(oNhap.value.trim()) || boAnh.soLuong() > 0;
    const coKenh = boAnh.soLuong() > 0 || socket?.readyState === WebSocket.OPEN;
    nut.disabled = Boolean(dangGui) || dangGuiAnh || !coNoiDung || !coKenh;
  }

  // Thẻ sản phẩm / đơn hàng trong tin, bấm để mở trang sản phẩm hoặc đơn.
  function veThe(the) {
    const lienKet = tao('a', `the-tin the-tin-${the.loai}`);
    lienKet.href = toiLaKhach ? the.url_khach : the.url_nha_thuoc;
    lienKet.target = '_top';
    if (the.url_anh) {
      const anh = tao('img');
      anh.src = the.url_anh;
      anh.alt = '';
      anh.loading = 'lazy';
      lienKet.append(anh);
    } else {
      const icon = tao('span', 'icon-the');
      icon.setAttribute('aria-hidden', 'true');
      icon.append(tao('i'));
      icon.firstChild.dataset.lucide = the.loai === 'don' ? 'package' : 'pill';
      lienKet.append(icon);
    }
    const chu = tao('span', 'chu-the');
    chu.append(
      tao('small', '', the.tieu_de + (the.ke_don ? ' · Thuốc kê đơn' : '')),
      tao('strong', '', the.ten),
      tao('span', '', the.phu),
    );
    lienKet.append(chu);
    return lienKet;
  }

  function veAnh(cacAnh) {
    const luoi = tao('div', `luoi-anh-tin so-anh-${cacAnh.length}`);
    cacAnh.forEach(anh => {
      const lienKet = tao('a');
      lienKet.href = urlAnh(anh.id);
      lienKet.target = '_blank';
      lienKet.rel = 'noopener';
      const hinh = tao('img');
      hinh.src = urlAnh(anh.id);
      hinh.alt = 'Ảnh đính kèm, bấm để xem lớn';
      hinh.width = anh.rong;
      hinh.height = anh.cao;
      hinh.loading = 'lazy';
      lienKet.append(hinh);
      lienKet.addEventListener('click', suKien => {
        if (!hopXemAnh?.showModal) return;
        suKien.preventDefault();
        hopXemAnh.querySelector('img').src = lienKet.href;
        hopXemAnh.querySelector('[data-mo-anh-goc]').href = lienKet.href;
        hopXemAnh.showModal();
      });
      luoi.append(lienKet);
    });
    return luoi;
  }

  function ve() {
    const benHo = toiLaKhach ? 'nha_thuoc' : 'khach';
    const tinCuoiCuaToi = [...cacTin].reverse().find(laCuaToi);
    const cacDong = [];
    if (conTinCu && cacTin.length) {
      const dongNut = tao('li', 'dong-tai-tin-cu');
      const nutTai = tao('button', 'nut-tai-tin-cu', dangTaiTinCu ? 'Đang tải…' : 'Xem tin cũ hơn');
      nutTai.type = 'button';
      nutTai.disabled = dangTaiTinCu;
      nutTai.addEventListener('click', taiTinCu);
      dongNut.append(nutTai);
      cacDong.push(dongNut);
    }
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
      if (tin.the) dong.append(veThe(tin.the));
      if (tin.anh?.length) dong.append(veAnh(tin.anh));
      if (tin.noi_dung) {
        const bong = tao('div', 'bong-tin');
        tin.noi_dung.split('\n').forEach((doan, j) => {
          if (j) bong.append(document.createElement('br'));
          bong.append(doan);
        });
        dong.append(bong);
      }
      const thoiGian = tao('time', 'gio-tin', gio(tin.thoi_diem));
      thoiGian.dateTime = tin.thoi_diem;
      dong.append(thoiGian);
      if (tinCuoiCuaToi && tin.id_tin_nhan === tinCuoiCuaToi.id_tin_nhan) {
        const daXem = moc[benHo] >= tin.id_tin_nhan;
        dong.append(tao('span', `trang-thai-tin${daXem ? ' da-xem' : ''}`, daXem ? 'Đã xem' : 'Đã gửi'));
      }
      cacDong.push(dong);
    });
    if (!cacDong.length) {
      cacDong.push(tao('li', 'chat-trong', lichSu.querySelector('[data-chat-trong]')?.textContent || 'Chưa có tin nhắn.'));
    }
    if (dongGoiY) cacDong.push(dongGoiY);
    const oCuoi = dangOCuoi();
    lichSu.replaceChildren(...cacDong);
    window.lucide?.createIcons();
    if (oCuoi || !ve.daCuon) {
      lichSu.scrollTop = lichSu.scrollHeight;
      ve.daCuon = true;
    }
  }

  const dangOCuoi = () => lichSu.scrollHeight - lichSu.scrollTop - lichSu.clientHeight < 80;

  // Khách đã gửi tin thì gợi ý hết tác dụng: bỏ hẳn khỏi luồng tin (tải lại trang cũng không hiện,
  // xem goi_y.py).
  function anGoiY() {
    if (!dongGoiY) return;
    dongGoiY.remove();
    dongGoiY = null;
  }

  // Ẩn / hiện lưu ý tư vấn; server nhớ lựa chọn trong phiên đăng nhập để lần mở sau không hiện lại.
  function datLuuY(an) {
    if (!luuY) return;
    const oCuoi = dangOCuoi();
    luuY.hidden = an;
    if (nutMoLuuY) nutMoLuuY.hidden = !an;
    if (oCuoi) lichSu.scrollTop = lichSu.scrollHeight;
    (an ? nutMoLuuY : luuY.querySelector('[data-dong-luu-y]'))?.focus();
    const duLieu = new FormData();
    duLieu.append('an', an ? '1' : '0');
    fetch(luuY.dataset.url, {method: 'POST', body: duLieu, headers: {'X-CSRFToken': maCsrf()}}).catch(() => {});
  }

  function themTin(tin) {
    if (cacTin.some(t => t.id_tin_nhan === tin.id_tin_nhan)) return;
    cacTin.push(tin);
    cacTin.sort((a, b) => a.id_tin_nhan - b.id_tin_nhan);
  }

  async function taiTinCu() {
    if (dangTaiTinCu || !cacTin.length) return;
    dangTaiTinCu = true;
    ve();
    const caoTruoc = lichSu.scrollHeight;
    const viTriTruoc = lichSu.scrollTop;
    try {
      const phanHoi = await fetch(`${khung.dataset.urlTinCu}?truoc=${cacTin[0].id_tin_nhan}`, {
        headers: {Accept: 'application/json'},
      });
      if (!phanHoi.ok) throw new Error(String(phanHoi.status));
      const ketQua = await phanHoi.json();
      ketQua.cac_tin.forEach(themTin);
      conTinCu = ketQua.con_nua;
    } catch {
      trangThai.textContent = 'Chưa tải được tin cũ. Bấm lại để thử.';
    }
    dangTaiTinCu = false;
    ve();
    // Giữ nguyên chỗ đang đọc: tin cũ chèn phía trên, không nhảy màn hình.
    lichSu.scrollTop = lichSu.scrollHeight - caoTruoc + viTriTruoc;
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
    capNhatNut();
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
        // Nối lại sau khi mất mạng: giữ tin cũ đã tải, trừ khi giữa hai đoạn có thể bị hở.
        const moiNhat = cacTin.length ? cacTin[cacTin.length - 1].id_tin_nhan : 0;
        const cuNhatMoi = ketQua.cac_tin.length ? ketQua.cac_tin[0].id_tin_nhan : 0;
        if (!cacTin.length || (ketQua.con_nua && cuNhatMoi > moiNhat)) {
          cacTin = [];
          conTinCu = Boolean(ketQua.con_nua);
        }
        ketQua.cac_tin.forEach(themTin);
        moc.khach = ketQua.khach_da_doc || 0;
        moc.nha_thuoc = ketQua.nha_thuoc_da_doc || 0;
        if (mocVachMoi === null) {
          const dauChuaDoc = cacTin.find(tin => !laCuaToi(tin) && tin.id_tin_nhan > moc[ben]);
          mocVachMoi = dauChuaDoc ? dauChuaDoc.id_tin_nhan : -1;
        }
        thuLai = 1000;
        trangThai.textContent = '';
        capNhatNut();
        if (dangGui) hienTai.send(JSON.stringify(dangGui));
        henKiemTraKetNoi(hienTai);
        ve();
        baoDaDoc();
      }
      if (ketQua.loai === 'ket_noi_con_song') henKiemTraKetNoi(hienTai);
      if (ketQua.tin) {
        // Tin của mình (gửi từ thẻ này hoặc thẻ khác) đã lưu: gợi ý không còn cần.
        if (laCuaToi(ketQua.tin)) anGoiY();
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
        if (dangGui.thuoc || dangGui.don_hang) boThe();
        anGoiY();
        dangGui = null;
        trangThai.textContent = '';
        capNhatNut();
      }
      if (ketQua.loai === 'loi') {
        trangThai.textContent = ketQua.thong_bao;
        dangGui = null;
        capNhatNut();
      }
    });
    hienTai.addEventListener('close', suKien => {
      if (hienTai !== socket) return;
      biChan = suKien.code === 4403;
      matKetNoi();
    });
  }

  // Mã CSRF có sẵn trên thẻ body (hx-headers) của mọi trang.
  function maCsrf() {
    try {
      return JSON.parse(document.body.getAttribute('hx-headers') || '{}')['X-CSRFToken'] || '';
    } catch {
      return '';
    }
  }

  // Thẻ chờ gửi: {thuoc: id} hoặc {don_hang: id}.
  function duLieuThe() {
    if (!theCho || theCho.hidden) return {};
    const id = Number(theCho.dataset.id);
    return theCho.dataset.loai === 'thuoc' ? {thuoc: id} : {don_hang: id};
  }

  function boThe() {
    if (!theCho || theCho.hidden) return;
    theCho.hidden = true;
    oNhap.placeholder = 'Nhập tin nhắn… (Enter để gửi)';
    // Gợi ý theo thẻ ("thuốc này", "đơn này") mất nghĩa khi không còn thẻ.
    if (dongGoiY?.hasAttribute('data-theo-the')) anGoiY();
    // Tải lại trang không gắn lại thẻ đã gửi hoặc đã bỏ.
    const url = new URL(location.href);
    url.searchParams.delete('thuoc');
    url.searchParams.delete('don');
    history.replaceState(null, '', url);
  }

  async function guiKemAnh() {
    dangGuiAnh = true;
    capNhatNut();
    trangThai.textContent = 'Đang gửi ảnh…';
    try {
      const cacTep = await boAnh.chuanBi();
      const duLieu = new FormData();
      duLieu.append('ma_tin_nhan', crypto.randomUUID());
      duLieu.append('noi_dung', oNhap.value.trim());
      cacTep.forEach(tep => duLieu.append('cac_anh', tep, tep.name));
      const the = duLieuThe();
      Object.entries(the).forEach(([ten, giaTri]) => duLieu.append(ten, giaTri));
      let phanHoi;
      try {
        phanHoi = await fetch(khung.dataset.urlGui, {
          method: 'POST',
          body: duLieu,
          headers: {Accept: 'application/json', 'X-CSRFToken': maCsrf()},
        });
      } catch {
        throw new Error('Mất mạng, chưa gửi được ảnh. Hãy thử lại.');
      }
      const ketQua = await phanHoi.json().catch(() => ({}));
      if (!phanHoi.ok) {
        throw new Error(
          ketQua.loi || (phanHoi.status === 413 ? 'Ảnh quá lớn, hãy bỏ bớt ảnh.' : 'Chưa gửi được ảnh, hãy thử lại.'),
        );
      }
      anGoiY();
      themTin(ketQua.tin);
      oNhap.value = '';
      coGian();
      boAnh.xoaHet();
      if (Object.keys(the).length) boThe();
      trangThai.textContent = '';
      ve();
    } catch (loi) {
      trangThai.textContent = loi.message || 'Chưa gửi được ảnh, hãy thử lại.';
    }
    dangGuiAnh = false;
    capNhatNut();
  }

  function guiTin() {
    if (dangGui || dangGuiAnh) return;
    if (boAnh.soLuong()) {
      guiKemAnh();
      return;
    }
    const noiDung = oNhap.value.trim();
    if (!noiDung || socket?.readyState !== WebSocket.OPEN) return;
    dangGui = {ma_tin_nhan: crypto.randomUUID(), noi_dung: noiDung, ...duLieuThe()};
    trangThai.textContent = 'Đang gửi…';
    capNhatNut();
    socket.send(JSON.stringify(dangGui));
  }

  // Ô nhập tự cao theo nội dung, tối đa khoảng 6 dòng.
  function coGian() {
    oNhap.style.height = 'auto';
    oNhap.style.height = `${Math.min(oNhap.scrollHeight, 150)}px`;
    oNhap.style.overflowY = oNhap.scrollHeight > 150 ? 'auto' : 'hidden';
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
    capNhatNut();
  });
  // Dán ảnh chụp màn hình (Ctrl + V) hoặc kéo thả ảnh vào khung chat.
  oNhap.addEventListener('paste', suKien => {
    const cacTep = [...(suKien.clipboardData?.files || [])];
    if (cacTep.length) {
      suKien.preventDefault();
      boAnh.them(cacTep);
    }
  });
  khung.addEventListener('dragover', suKien => {
    if ([...suKien.dataTransfer.types].includes('Files')) suKien.preventDefault();
  });
  khung.addEventListener('drop', suKien => {
    if (!suKien.dataTransfer.files.length) return;
    suKien.preventDefault();
    boAnh.them([...suKien.dataTransfer.files]);
  });
  theCho?.querySelector('[data-bo-the]')?.addEventListener('click', () => {
    boThe();
    oNhap.focus();
  });
  luuY?.querySelector('[data-dong-luu-y]')?.addEventListener('click', () => datLuuY(true));
  nutMoLuuY?.addEventListener('click', () => datLuuY(false));
  hopXemAnh?.querySelector('[data-dong-xem-anh]')?.addEventListener('click', () => hopXemAnh.close());
  hopXemAnh?.addEventListener('click', suKien => {
    if (suKien.target === hopXemAnh) hopXemAnh.close();
  });
  khung.querySelectorAll('[data-goi-y-nhanh] button').forEach(nutGoiY =>
    nutGoiY.addEventListener('click', () => {
      oNhap.value = nutGoiY.dataset.cau;
      coGian();
      oNhap.focus();
      capNhatNut();
    }),
  );
  document.addEventListener('visibilitychange', baoDaDoc);
  window.addEventListener('focus', baoDaDoc);
  window.addEventListener('offline', matKetNoi);
  window.addEventListener('online', ketNoi);
  if (navigator.onLine) ketNoi();
  else matKetNoi();
})();
