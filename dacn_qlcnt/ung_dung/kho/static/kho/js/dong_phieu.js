// Bảng dòng hàng của phiếu kho: thêm dòng từ mẫu, bỏ dòng (đánh dấu DELETE để giữ chỉ số formset),
// đánh số lại các dòng đang hiện và gắn ô chọn có tìm kiếm cho dòng mới.
// Có dữ liệu #du-lieu-phieu thì gợi ý ngay khi chọn: bao gói đúng thuốc, quy đổi ra đơn vị cơ sở,
// thành tiền và tổng phiếu nhập, lô cận hạn, tồn còn dùng được, số còn trả nhà cung cấp.
// Chỉ để người lập đối chiếu trước khi lưu; máy chủ vẫn kiểm và tính lại toàn bộ.
document.querySelectorAll('[data-formset]').forEach(form => {
  const than = form.querySelector('[data-cac-dong]');
  const tong = form.querySelector('[name$="-TOTAL_FORMS"]');
  const mau = form.querySelector('[data-dong-rong]');
  const dem = form.querySelector('[data-dem-dong]');
  if (!than || !tong || !mau) return;

  const nguon = document.getElementById('du-lieu-phieu');
  const duLieu = nguon ? JSON.parse(nguon.textContent) : {};
  const cacThuoc = duLieu.thuoc || {};
  const loTra = new Map();
  const so = n => Number(n || 0).toLocaleString('vi-VN');
  const o = (dong, ten) => dong.querySelector(`[name$="-${ten}"]`);
  const goiY = (dong, ten, chu) => {
    const vung = dong.querySelector(`[data-goi-y="${ten}"]`);
    if (vung) vung.textContent = chu || '';
  };
  const chiNhanhDangChon = () => {
    const ten = duLieu.o_chi_nhanh;
    return ten ? form.querySelector(`[name="${ten}"]`)?.value || '' : '';
  };

  const cacDongHien = () => [...than.querySelectorAll('[data-dong]')].filter(dong => !dong.hidden);

  // Ô "Tính theo" chỉ liệt kê bao gói của thuốc ở dòng đó, kèm hệ số quy đổi.
  const dungBaoGoi = dong => {
    const chon = o(dong, 'quy_doi_bao_goi');
    const thuoc = cacThuoc[o(dong, 'thuoc')?.value || ''];
    if (!chon || chon.dataset.daGanChon) return;
    const dangChon = chon.value;
    chon.replaceChildren(new Option(thuoc ? `Đơn vị cơ sở (${thuoc.don_vi})` : 'Đơn vị cơ sở', ''));
    (thuoc?.bao_goi || []).forEach(b => {
      chon.append(new Option(`${b.ten} (= ${so(b.he_so)} ${thuoc.don_vi})`, String(b.id)));
    });
    chon.value = [...chon.options].some(t => t.value === dangChon) ? dangChon : '';
  };

  const heSo = dong => {
    const thuoc = cacThuoc[o(dong, 'thuoc')?.value || ''];
    const ma = Number(o(dong, 'quy_doi_bao_goi')?.value || 0);
    return thuoc?.bao_goi.find(b => b.id === ma)?.he_so || 1;
  };

  const tinhDong = dong => {
    const thuoc = cacThuoc[o(dong, 'thuoc')?.value || ''];
    const soLuong = Number(o(dong, 'so_luong')?.value || 0);
    const coSo = soLuong * heSo(dong);
    let chuSoLuong = thuoc && heSo(dong) > 1 && soLuong ? `= ${so(coSo)} ${thuoc.don_vi}` : '';
    // Điều chuyển: lượng còn chuyển được ở chi nhánh nguồn (đã trừ phần giữ, lô hết hạn/khóa).
    if (duLieu.ton_thuoc && thuoc) {
      const con = duLieu.ton_thuoc[chiNhanhDangChon()]?.[o(dong, 'thuoc').value] || 0;
      chuSoLuong = `${chuSoLuong ? `${chuSoLuong} · ` : ''}còn chuyển được ${so(con)} ${thuoc.don_vi}`;
      dong.querySelector('[data-goi-y="so_luong"]')?.classList.toggle('vuot', coSo > con);
    }
    // Xuất hủy: tồn của lô ở chi nhánh đã chọn.
    const lo = o(dong, 'lo_thuoc');
    if (duLieu.ton_lo && lo) {
      const ton = duLieu.ton_lo[chiNhanhDangChon()]?.[lo.value];
      goiY(dong, 'lo_thuoc', !lo.value ? '' : ton
        ? `Trong kho ${so(ton[0])} ${ton[2]}${ton[1] ? `, đang giữ cho đơn ${so(ton[1])}` : ''}; hủy được tối đa ${so(ton[0] - ton[1])}.`
        : 'Lô này không còn hàng ở chi nhánh đã chọn.');
    }
    // Trả nhà cung cấp: số liệu của lô theo phiếu nhập gốc.
    if (duLieu.url_lo_theo_phieu && lo) {
      const t = loTra.get(lo.value);
      goiY(dong, 'lo_thuoc', t
        ? `Đã nhập ${so(t.da_nhap)}, đã trả ${so(t.da_tra)}, đang giữ cho đơn ${so(t.dang_giu)}: còn trả được ${so(t.con_tra_duoc)} ${t.don_vi}.`
        : '');
    }
    goiY(dong, 'so_luong', chuSoLuong);
    // Phiếu nhập: hạn dùng và thành tiền.
    const han = o(dong, 'ngay_het_han');
    if (han) {
      const xacNhan = dong.querySelector('[data-xac-nhan-can-han]');
      let chuHan = '';
      if (han.value) {
        const homNay = new Date();
        homNay.setHours(0, 0, 0, 0);
        const conNgay = Math.round((new Date(`${han.value}T00:00:00`) - homNay) / 86400000);
        chuHan = conNgay <= 0 ? 'Đã hết hạn, không nhận vào kho.' : `Còn ${so(conNgay)} ngày`;
        const canHan = conNgay > 0 && conNgay < (duLieu.so_ngay_can_han || 90);
        if (xacNhan && canHan) xacNhan.hidden = false;
        if (xacNhan && !canHan && !xacNhan.querySelector('input').checked) xacNhan.hidden = true;
        han.closest('td')?.classList.toggle('can-han', canHan || conNgay <= 0);
      }
      goiY(dong, 'ngay_het_han', chuHan);
    }
    const oTien = dong.querySelector('[data-thanh-tien]');
    if (oTien) {
      const gia = Number(o(dong, 'don_gia')?.value || 0);
      const tien = coSo * gia;
      oTien.textContent = tien ? `${so(tien)} đ` : '–';
      oTien.dataset.giaTri = String(tien);
      goiY(dong, 'don_gia', thuoc && gia && heSo(dong) > 1 ? `= ${so(gia * heSo(dong))} đ / bao gói` : '');
    }
  };

  const capNhat = () => {
    const hien = cacDongHien();
    let tongTien = 0;
    hien.forEach((dong, i) => {
      dong.querySelector('[data-stt]').textContent = i + 1;
      tinhDong(dong);
      tongTien += Number(dong.querySelector('[data-thanh-tien]')?.dataset.giaTri || 0);
    });
    if (dem) dem.textContent = `${hien.length} dòng`;
    const oTong = form.querySelector('[data-tong-tien]');
    if (oTong) oTong.textContent = `${so(tongTien)} đ`;
  };

  // Trả nhà cung cấp: chọn phiếu nhập thì nạp lại danh sách lô của đúng phiếu đó.
  const napLoTra = async (giuLuaChon) => {
    const phieu = form.querySelector('[name="phieu_nhap"]')?.value;
    loTra.clear();
    let cacLo = [];
    if (phieu) {
      try {
        const traVe = await fetch(`${duLieu.url_lo_theo_phieu}?phieu_nhap=${encodeURIComponent(phieu)}`, {
          headers: {Accept: 'application/json'},
        });
        if (traVe.ok) cacLo = (await traVe.json()).lo;
      } catch {
        cacLo = [];
      }
    }
    cacLo.forEach(t => loTra.set(String(t.id), t));
    const dung = chon => {
      if (!chon || chon.dataset.daGanChon) return;
      const cu = chon.value;
      chon.replaceChildren(new Option(phieu ? 'Chọn lô' : 'Chọn phiếu nhập trước', ''));
      cacLo.forEach(t => chon.append(new Option(`${t.nhan} · còn trả ${so(t.con_tra_duoc)}`, String(t.id))));
      chon.value = giuLuaChon && loTra.has(cu) ? cu : '';
    };
    than.querySelectorAll('[name$="-lo_thuoc"]').forEach(dung);
    const tam = document.createElement('tbody');
    tam.innerHTML = mau.innerHTML;
    dung(tam.querySelector('[name$="-lo_thuoc"]'));
    mau.innerHTML = tam.innerHTML;
    capNhat();
  };

  form.querySelector('[data-them-dong]')?.addEventListener('click', () => {
    if (Number(tong.value) >= 50) return;
    const tam = document.createElement('tbody');
    tam.innerHTML = mau.innerHTML.replaceAll('__prefix__', tong.value);
    const dongMoi = tam.querySelector('[data-dong]');
    than.append(dongMoi);
    tong.value = String(Number(tong.value) + 1);
    if (typeof ganChonCoTim === 'function') ganChonCoTim(dongMoi);
    window.lucide?.createIcons();
    capNhat();
    dongMoi.querySelector('input:not([type=hidden]), select')?.focus();
  });

  than.addEventListener('click', suKien => {
    const nut = suKien.target.closest('[data-bo-dong]');
    if (!nut) return;
    const dong = nut.closest('[data-dong]');
    const xoa = dong.querySelector('[name$="-DELETE"]');
    if (xoa) xoa.checked = true;
    dong.hidden = true;
    // Dòng lỗi đi kèm (nếu có) cũng ẩn theo.
    if (dong.nextElementSibling?.classList.contains('dong-loi')) dong.nextElementSibling.hidden = true;
    capNhat();
  });

  form.addEventListener('change', suKien => {
    const ten = suKien.target.name || '';
    if (ten === 'phieu_nhap' && duLieu.url_lo_theo_phieu) {
      napLoTra(false);
      return;
    }
    if (ten.endsWith('-thuoc')) dungBaoGoi(suKien.target.closest('[data-dong]'));
    capNhat();
  });
  form.addEventListener('input', capNhat);

  // Chống gửi trùng: khóa nút lưu khi đang gửi; máy chủ còn chặn bằng mã yêu cầu của form.
  form.addEventListener('submit', () => {
    const nut = form.querySelector('[data-nut-luu]');
    if (!nut) return;
    nut.disabled = true;
    nut.dataset.nhanCu = nut.textContent.trim();
    nut.lastChild.textContent = 'Đang lưu…';
  });
  window.addEventListener('pageshow', () => {
    const nut = form.querySelector('[data-nut-luu]');
    if (nut?.disabled) {
      nut.disabled = false;
      nut.lastChild.textContent = nut.dataset.nhanCu || nut.lastChild.textContent;
    }
  });

  if (Object.keys(cacThuoc).length) cacDongHien().forEach(dungBaoGoi);
  if (duLieu.url_lo_theo_phieu) napLoTra(true);
  else capNhat();
});
