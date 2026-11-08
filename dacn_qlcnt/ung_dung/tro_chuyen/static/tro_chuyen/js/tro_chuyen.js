(() => {
  const khung = document.querySelector("[data-tro-chuyen]");
  const form = khung.querySelector("form");
  const nut = form.querySelector("button");
  const lichSu = khung.querySelector("[data-cac-tin]");
  const trangThai = khung.querySelector("[data-trang-thai]");
  const daHien = new Set(Array.from(lichSu.children, dong => Number(dong.dataset.idTin)));
  const giaoThuc = location.protocol === "https:" ? "wss:" : "ws:";
  const CHU_KY_KIEM_TRA = 30000;
  const HAN_PHAN_HOI = 10000;
  let socket = null, dangGui = null, thuLai = 1000, biChan = false;
  let henThuLai, henKiemTra, henPhanHoi;

  function hienTin(tin) {
    if (daHien.has(tin.id_tin_nhan)) return;
    daHien.add(tin.id_tin_nhan);
    const dong = document.createElement("li");
    dong.dataset.idTin = tin.id_tin_nhan;
    const ten = document.createElement("strong");
    ten.textContent = tin.nguoi_gui;
    const noiDung = document.createElement("p");
    noiDung.textContent = tin.noi_dung;
    dong.append(ten, noiDung);
    const sau = Array.from(lichSu.children).find(muc => Number(muc.dataset.idTin) > tin.id_tin_nhan);
    lichSu.insertBefore(dong, sau || null);
    while (lichSu.children.length > 100) {
      const dau = lichSu.firstElementChild;
      daHien.delete(Number(dau.dataset.idTin));
      dau.remove();
    }
    lichSu.scrollTop = lichSu.scrollHeight;
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
      trangThai.textContent = "Không còn quyền truy cập cuộc trò chuyện.";
    } else if (!navigator.onLine) {
      trangThai.textContent = "Mất mạng. Sẽ kết nối lại khi có mạng.";
    } else {
      trangThai.textContent = "Mất kết nối. Đang thử lại…";
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
      hienTai.send(JSON.stringify({ loai: "kiem_tra_ket_noi" }));
      choPhanHoi();
    }, CHU_KY_KIEM_TRA);
  }

  function ketNoi() {
    if (socket || biChan || !navigator.onLine) return;
    clearTimeout(henThuLai);
    trangThai.textContent = "Đang kết nối và đồng bộ tin nhắn…";
    const hienTai = new WebSocket(
      `${giaoThuc}//${location.host}/ws/tro-chuyen/${khung.dataset.maPhong}/`
    );
    socket = hienTai;
    choPhanHoi();
    hienTai.addEventListener("message", suKien => {
      if (hienTai !== socket) return;
      const ketQua = JSON.parse(suKien.data);
      if (ketQua.loai === "lich_su") {
        ketQua.cac_tin.forEach(hienTin);
        thuLai = 1000;
        trangThai.textContent = "Đã kết nối";
        nut.disabled = Boolean(dangGui);
        if (dangGui) hienTai.send(JSON.stringify(dangGui));
        henKiemTraKetNoi(hienTai);
      }
      if (ketQua.loai === "ket_noi_con_song") henKiemTraKetNoi(hienTai);
      if (ketQua.tin) hienTin(ketQua.tin);
      if (ketQua.loai === "da_luu" && ketQua.ma_tin_nhan === dangGui?.ma_tin_nhan) {
        if (form.noi_dung.value.trim() === dangGui.noi_dung) form.reset();
        dangGui = null;
        nut.disabled = false;
        trangThai.textContent = "Đã gửi";
      }
      if (ketQua.loai === "loi") {
        trangThai.textContent = ketQua.thong_bao;
        dangGui = null;
        nut.disabled = false;
      }
    });
    hienTai.addEventListener("close", suKien => {
      if (hienTai !== socket) return;
      biChan = suKien.code === 4403;
      matKetNoi();
    });
  }

  form.addEventListener("submit", suKien => {
    suKien.preventDefault();
    const noiDung = form.noi_dung.value.trim();
    if (nut.disabled || dangGui || !noiDung || socket?.readyState !== WebSocket.OPEN) return;
    dangGui = { ma_tin_nhan: crypto.randomUUID(), noi_dung: noiDung };
    nut.disabled = true;
    socket.send(JSON.stringify(dangGui));
  });
  window.addEventListener("offline", matKetNoi);
  window.addEventListener("online", ketNoi);
  if (navigator.onLine) ketNoi();
  else matKetNoi();
})();
