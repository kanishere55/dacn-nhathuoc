// Bản đồ trang đặt giữ: các chi nhánh đủ hàng, vị trí của khách và đường đi tới chi nhánh đang chọn.
(() => {
  const form = document.getElementById('form-dat-hang');
  if (!form) return;
  function khoiTao() {
    const khung = form.querySelector('[data-ban-do-dat-hang]');
    if (!khung) return;
    const duLieu = JSON.parse(document.getElementById('du-lieu-ban-do-dat-hang').textContent);
    const tomTat = form.querySelector('[data-tom-tat-lo-trinh]');
    const chon = duLieu.cac_chi_nhanh.find((cn) => cn.chon) || duLieu.cac_chi_nhanh[0];
    // Khối checkout có thể bị thay thế trong lúc người dùng đang phóng bản đồ.
    const banDo = window.taoBanDoNhaThuoc(
      khung, chon ? [chon.vi_do, chon.kinh_do] : undefined, 14, { zoomAnimation: false },
    );
    let diemKhach = duLieu.khach ? [duLieu.khach.vi_do, duLieu.khach.kinh_do] : null;
    let mocKhach = null;
    let lopDuong = null;
    let boLoTrinh = null;
    let daHuy = false;
    const gioiHan = [];

    duLieu.cac_chi_nhanh.forEach((cn) => {
      const diem = [cn.vi_do, cn.kinh_do];
      gioiHan.push(diem);
      const moc = L.marker(diem, { icon: window.bieuTuongNhaThuoc({ mo: cn.chon }), title: cn.ten, zIndexOffset: cn.chon ? 500 : 0 })
        .bindTooltip(cn.ten + (cn.chon ? ' (đang chọn)' : ''), { direction: 'top', offset: [0, -40] })
        .addTo(banDo);
      moc.on('click', () => {
        if (cn.chon) return;
        const o = form.querySelector(`input[name="chi_nhanh"][value="${cn.id}"]`);
        if (o) {
          o.checked = true;
          o.dispatchEvent(new Event('change', { bubbles: true }));
        }
      });
    });

    const datKhach = (diem, nhan) => {
      diemKhach = diem;
      if (!mocKhach) mocKhach = L.marker(diem, { icon: window.bieuTuongNguoiDung(nhan), zIndexOffset: 1000 }).addTo(banDo);
      else mocKhach.setLatLng(diem);
    };
    if (diemKhach) {
      datKhach(diemKhach, 'Bạn ở đây');
      gioiHan.push(diemKhach);
    }
    if (gioiHan.length > 1) banDo.fitBounds(gioiHan, { padding: [40, 40], maxZoom: 15, animate: false });

    async function veLoTrinh() {
      if (!chon) return;
      if (!diemKhach) {
        tomTat.textContent = `Nhận tại ${chon.ten}. Bấm “Tính đường từ vị trí hiện tại” để xem đường đi.`;
        return;
      }
      tomTat.textContent = 'Đang tính lộ trình…';
      boLoTrinh?.abort();
      const luot = new AbortController();
      boLoTrinh = luot;
      const hen = setTimeout(() => luot.abort(), 10000);
      lopDuong?.remove();
      const tu = diemKhach;
      const den = [chon.vi_do, chon.kinh_do];
      try {
        const duong = await window.layLoTrinh(duLieu.osrm, tu, den, luot.signal);
        if (daHuy || boLoTrinh !== luot) return;
        lopDuong = L.geoJSON(duong.geometry, { style: { color: '#116b54', weight: 6, opacity: 0.85 } }).addTo(banDo);
        banDo.fitBounds(lopDuong.getBounds(), { padding: [40, 40], maxZoom: 16, animate: false });
        const xeMay = window.dinhDangPhut(window.thoiGianTheoPhuongTien(duong, 'xe_may'));
        tomTat.replaceChildren();
        const them = (nhan, giaTri) => {
          const span = document.createElement('span');
          span.append(nhan + ': ');
          const b = document.createElement('strong');
          b.textContent = giaTri;
          span.append(b);
          tomTat.append(span);
        };
        them(`Đến ${chon.ten}`, window.dinhDangKm(duong.distance));
        them('Xe máy khoảng', xeMay);
        them('Ô tô khoảng', window.dinhDangPhut(duong.duration));
      } catch {
        if (daHuy || boLoTrinh !== luot) return;
        lopDuong = L.polyline([tu, den], { color: '#116b54', dashArray: '6 8', weight: 4 }).addTo(banDo);
        banDo.fitBounds(lopDuong.getBounds(), { padding: [40, 40], maxZoom: 16, animate: false });
        tomTat.textContent = 'Chưa lấy được lộ trình đường bộ; đường nét đứt là khoảng cách thẳng.';
      } finally {
        clearTimeout(hen);
      }
    }

    form.querySelector('[data-dinh-vi-dat-hang]')?.addEventListener('click', () => {
      if (!navigator.geolocation) { tomTat.textContent = 'Trình duyệt không hỗ trợ định vị.'; return; }
      tomTat.textContent = 'Đang lấy vị trí của bạn…';
      navigator.geolocation.getCurrentPosition(
        ({ coords }) => {
          if (daHuy) return;
          datKhach([coords.latitude, coords.longitude], 'Bạn ở đây');
          veLoTrinh();
        },
        () => { if (!daHuy) tomTat.textContent = 'Không lấy được vị trí. Hãy cho phép định vị trong trình duyệt.'; },
        { enableHighAccuracy: true, timeout: 10000 },
      );
    });
    veLoTrinh();
    return () => {
      daHuy = true;
      boLoTrinh?.abort();
      banDo.remove();
    };
  }

  let huyBanDo = null;
  let moBanDo = false;
  form.addEventListener('toggle', (e) => {
    if (!e.target.matches('[data-mo-ban-do-dat-hang]') || !e.target.isConnected) return;
    moBanDo = e.target.open;
    if (moBanDo) {
      huyBanDo ||= khoiTao();
    }
  }, true);
  form.addEventListener('htmx:afterSwap', (e) => {
    if (e.detail.target.id !== 'lua-chon-dat-hang') return;
    huyBanDo?.();
    huyBanDo = null;
    const chiTiet = form.querySelector('[data-mo-ban-do-dat-hang]');
    if (chiTiet && moBanDo) chiTiet.open = true;
  });
})();
