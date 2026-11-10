// Thông báo tin nhắn trên mọi trang: huy hiệu số chưa đọc, "(n)" trên tiêu đề tab, thông báo nổi.
// Số liệu lấy từ CSDL (render sẵn và hỏi lại qua kênh); Redis chỉ báo "có thay đổi".
(() => {
  const goc = document.body.dataset.thongBao;
  if (!goc) return;
  const laKhach = goc === 'khach';
  const tieuDeGoc = document.title.replace(/^\(\d+\)\s*/, '');
  const giaoThuc = location.protocol === 'https:' ? 'wss:' : 'ws:';
  let thuLai = 2000;
  let henHoi;

  function capNhatDem(tong) {
    document.querySelectorAll('[data-dem-chat]').forEach(huyHieu => {
      huyHieu.textContent = tong > 99 ? '99+' : String(tong);
      huyHieu.hidden = !tong;
    });
    document.title = tong ? `(${tong}) ${tieuDeGoc}` : tieuDeGoc;
  }

  // Đang mở đúng phòng (trên trang hoặc trong khung chat nổi đang mở) thì không cần báo nổi.
  function dangXemPhong(maPhong) {
    if (document.querySelector(`[data-tro-chuyen][data-ma-phong="${maPhong}"]`)) return true;
    const khung = document.querySelector('[data-khung-tu-van]:not([hidden]) iframe');
    try {
      return Boolean(khung?.contentDocument?.querySelector(`[data-tro-chuyen][data-ma-phong="${maPhong}"]`));
    } catch {
      return false;
    }
  }

  function baoNoi(tin) {
    if (dangXemPhong(tin.ma_phong)) return;
    let vung = document.querySelector('.vung-bao-noi');
    if (!vung) {
      vung = document.createElement('div');
      vung.className = 'vung-bao-noi';
      vung.setAttribute('role', 'status');
      vung.setAttribute('aria-live', 'polite');
      document.body.append(vung);
    }
    const the = document.createElement('a');
    the.className = 'bao-noi';
    the.href = laKhach ? tin.url_khach : tin.url_nha_thuoc;
    const icon = document.createElement('span');
    icon.className = 'bao-noi-icon';
    icon.innerHTML = '<i data-lucide="message-circle" aria-hidden="true"></i>';
    const chu = document.createElement('span');
    const tieuDe = document.createElement('strong');
    tieuDe.textContent = laKhach ? `${tin.tieu_de} trả lời bạn` : `Tin nhắn mới từ ${tin.tieu_de}`;
    const xemTruoc = document.createElement('small');
    xemTruoc.textContent = tin.xem_truoc;
    chu.append(tieuDe, xemTruoc);
    the.append(icon, chu);
    // Khách đang ở website: mở trong khung chat nổi thay vì rời trang.
    if (laKhach && document.querySelector('[data-tu-van-noi]')) {
      the.addEventListener('click', suKien => {
        suKien.preventDefault();
        window.moKhungTuVan?.(`${tin.url_khach}?nhung=1`);
        the.remove();
      });
    }
    vung.append(the);
    window.lucide?.createIcons();
    setTimeout(() => the.remove(), 8000);
  }

  async function hoiLai() {
    try {
      const phanHoi = await fetch(document.body.dataset.urlChuaDoc, {headers: {Accept: 'application/json'}});
      if (phanHoi.ok) capNhatDem((await phanHoi.json()).tong);
    } catch {
      /* mạng chập chờn: lần sau hỏi lại */
    }
  }

  function ketNoi() {
    const socket = new WebSocket(`${giaoThuc}//${location.host}/ws/thong-bao/`);
    socket.addEventListener('open', () => {
      thuLai = 2000;
      clearInterval(henHoi);
    });
    socket.addEventListener('message', suKien => {
      const tin = JSON.parse(suKien.data);
      if (typeof tin.tong === 'number') capNhatDem(tin.tong);
      if (tin.loai === 'tin_moi') baoNoi(tin);
    });
    socket.addEventListener('close', suKien => {
      if (suKien.code === 4403) return;
      // Kênh thời gian thực gián đoạn (ví dụ Redis tắt): vẫn hỏi số chưa đọc định kỳ.
      clearInterval(henHoi);
      henHoi = setInterval(hoiLai, 60000);
      setTimeout(ketNoi, thuLai);
      thuLai = Math.min(thuLai * 2, 60000);
    });
  }

  window.capNhatDemChat = capNhatDem;
  ketNoi();
})();
