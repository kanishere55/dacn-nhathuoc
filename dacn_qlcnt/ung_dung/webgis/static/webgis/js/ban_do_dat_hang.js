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
    const ganPopup = window.taoPopupNhaThuoc(banDo);

    // Nút trong popup: nhận tại chi nhánh này (chọn ô tương ứng trong danh sách) và xem chi tiết.
    const tacVuPopup = (cn) => {
      let chon;
      if (cn.chon) {
        chon = document.createElement('span');
        chon.className = 'nhan-dang-chon';
        chon.textContent = 'Đang chọn';
      } else {
        chon = document.createElement('button');
        chon.type = 'button';
        chon.className = 'nut';
        chon.textContent = 'Nhận tại đây';
        chon.addEventListener('click', () => {
          const o = form.querySelector(`input[name="chi_nhanh"][value="${cn.id_chi_nhanh}"]`);
          if (!o) return;
          o.checked = true;
          o.dispatchEvent(new Event('change', { bubbles: true }));
        });
      }
      const chiTiet = document.createElement('a');
      chiTiet.className = 'nut nut-phu';
      chiTiet.textContent = 'Xem chi tiết';
      chiTiet.href = cn.duong_dan;
      chiTiet.target = '_blank';
      chiTiet.rel = 'noopener';
      return [chon, chiTiet];
    };

    duLieu.cac_chi_nhanh.forEach((cn) => {
      const diem = [cn.vi_do, cn.kinh_do];
      gioiHan.push(diem);
      const moc = L.marker(diem, {
        icon: window.bieuTuongNhaThuoc({ mo: cn.chon }), alt: cn.ten_chi_nhanh, zIndexOffset: cn.chon ? 500 : 0,
      }).addTo(banDo);
      ganPopup(moc, () => window.noiDungPopupNhaThuoc(cn, tacVuPopup(cn)));
    });

    const datKhach = (diem, nhan) => {
      diemKhach = diem;
      if (!mocKhach) mocKhach = L.marker(diem, { icon: window.bieuTuongNguoiDung(nhan), zIndexOffset: 1000, interactive: false }).addTo(banDo);
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
        tomTat.textContent = `Nhận tại ${chon.ten_chi_nhanh}.`;
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
        them(`Đến ${chon.ten_chi_nhanh}`, window.dinhDangKm(duong.distance));
        them('Xe máy khoảng', xeMay);
        them('Ô tô khoảng', window.dinhDangPhut(duong.duration));
      } catch {
        if (daHuy || boLoTrinh !== luot) return;
        banDo.fitBounds([tu, den], { padding: [40, 40], maxZoom: 16, animate: false });
        tomTat.textContent = 'Chưa tải được đường đi, vui lòng thử lại sau.';
      } finally {
        clearTimeout(hen);
      }
    }

    // Chạm lên bản đồ (không phải biểu tượng nhà thuốc) để đặt vị trí của khách tại đó.
    banDo.on('click', (e) => {
      tomTat.textContent = 'Đang tìm nhà thuốc gần điểm bạn chọn…';
      form.dispatchEvent(new CustomEvent('dat-vi-tri', {
        detail: { viDo: e.latlng.lat, kinhDo: e.latlng.lng, nhan: 'điểm bạn chọn trên bản đồ' },
      }));
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
  // Khối lựa chọn được thay sau mỗi lần đổi chi nhánh hoặc vị trí: dựng lại bản đồ nếu khách đang mở,
  // hoặc khi đã có vị trí (máy chủ trả khung bản đồ ở trạng thái mở).
  const moLai = () => {
    const chiTiet = form.querySelector('[data-mo-ban-do-dat-hang]');
    if (!chiTiet) return;
    if (moBanDo) chiTiet.open = true;
    if (chiTiet.open) {
      moBanDo = true;
      huyBanDo ||= khoiTao();
    }
  };
  form.addEventListener('htmx:afterSwap', (e) => {
    if (e.detail.target.id !== 'lua-chon-dat-hang') return;
    huyBanDo?.();
    huyBanDo = null;
    moLai();
  });
  moLai();
})();
