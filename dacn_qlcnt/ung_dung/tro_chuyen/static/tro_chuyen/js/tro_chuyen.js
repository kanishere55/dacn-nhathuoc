(() => {
  const khung = document.querySelector("[data-tro-chuyen]");
  const form = khung.querySelector("form");
  const nut = form.querySelector("button");
  const lichSu = khung.querySelector("[data-cac-tin]");
  const trangThai = khung.querySelector("[data-trang-thai]");
  const daHien = new Set(Array.from(lichSu.children, dong => Number(dong.dataset.idTin)));
  const giaoThuc = location.protocol === "https:" ? "wss:" : "ws:";
  let socket, dangGui = null, thuLai = 1000;

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

  function ketNoi() {
    socket = new WebSocket(`${giaoThuc}//${location.host}/ws/tro-chuyen/${khung.dataset.maPhong}/`);
    socket.addEventListener("open", () => {
      thuLai = 1000;
      trangThai.textContent = "Đã kết nối";
      nut.disabled = Boolean(dangGui);
      if (dangGui) socket.send(JSON.stringify(dangGui));
    });
    socket.addEventListener("message", suKien => {
      const ketQua = JSON.parse(suKien.data);
      if (ketQua.loai === "lich_su") ketQua.cac_tin.forEach(hienTin);
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
    socket.addEventListener("close", suKien => {
      nut.disabled = true;
      if (suKien.code === 4403) {
        trangThai.textContent = "Không còn quyền truy cập cuộc trò chuyện.";
        return;
      }
      trangThai.textContent = "Mất kết nối. Đang thử lại…";
      setTimeout(ketNoi, thuLai);
      thuLai = Math.min(thuLai * 2, 15000);
    });
  }

  form.addEventListener("submit", suKien => {
    suKien.preventDefault();
    const noiDung = form.noi_dung.value.trim();
    if (dangGui || !noiDung || socket.readyState !== WebSocket.OPEN) return;
    dangGui = { ma_tin_nhan: crypto.randomUUID(), noi_dung: noiDung };
    nut.disabled = true;
    socket.send(JSON.stringify(dangGui));
  });
  ketNoi();
})();
