// Ô chọn thả xuống có ô tìm kiếm (Choices.js): mọi ô trong thanh lọc, và ô dài từ 7 lựa chọn ở form.
// Thêm data-khong-tim để giữ ô chọn gốc; data-tim-kiem-chon để luôn bật tìm kiếm.
const ganChonCoTim = (pham_vi = document) => {
  if (!window.Choices) return;
  pham_vi.querySelectorAll('select').forEach((o) => {
    if (o.dataset.daGanChon || o.multiple || o.disabled || o.hasAttribute('data-khong-tim')) return;
    if (o.closest('.ql-toolbar, .leaflet-container')) return;
    // Mọi ô lọc ở khu quản lý (form GET) đều có tìm kiếm, trừ ô số dòng mỗi trang.
    const laOLoc = (o.closest('.thanh-loc') || (o.closest('form[method="get"]') && o.closest('.khung-ung-dung')))
      && o.name !== 'moi_trang';
    if (!(laOLoc || o.hasAttribute('data-tim-kiem-chon') || o.options.length >= 7)) return;
    o.dataset.daGanChon = '1';
    // eslint-disable-next-line no-new
    new window.Choices(o, {
      allowHTML: false,
      shouldSort: false,
      searchEnabled: true,
      searchResultLimit: 50,
      searchFields: ['label'],
      fuseOptions: { threshold: 0.3, ignoreLocation: true },
      itemSelectText: '',
      position: 'bottom',
      searchPlaceholderValue: 'Gõ để tìm…',
      noResultsText: 'Không có kết quả phù hợp',
      noChoicesText: 'Không còn lựa chọn',
      loadingText: 'Đang tải…',
    });
  });
};

document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) window.lucide.createIcons();
  ganChonCoTim();
});
document.addEventListener("htmx:afterSwap", (suKien) => {
  if (window.lucide) window.lucide.createIcons();
  ganChonCoTim(suKien.target);
});

// Nút data-sao-chep="giá trị": chép vào bộ nhớ tạm, đổi nhãn trong 2 giây.
document.addEventListener('click', async (suKien) => {
  const nut = suKien.target.closest('[data-sao-chep]');
  if (!nut) return;
  try {
    await navigator.clipboard.writeText(nut.dataset.saoChep);
    nut.classList.add('da-sao-chep');
    nut.setAttribute('aria-label', 'Đã chép');
    setTimeout(() => nut.classList.remove('da-sao-chep'), 2000);
  } catch (_) {
    window.prompt('Chép giá trị này:', nut.dataset.saoChep);
  }
});

// Phần tử data-dem-nguoc="giây Unix": hiện mm:ss còn lại, hết giờ thì tải lại trang.
const demNguoc = () => {
  document.querySelectorAll('[data-dem-nguoc]').forEach((o) => {
    const con = Math.max(0, Number(o.dataset.demNguoc) * 1000 - Date.now());
    const phut = Math.floor(con / 60000);
    const giay = Math.floor((con % 60000) / 1000);
    o.textContent = `${String(phut).padStart(2, '0')}:${String(giay).padStart(2, '0')}`;
    if (con === 0 && !o.dataset.daHet) {
      o.dataset.daHet = '1';
      setTimeout(() => window.location.reload(), 1500);
    }
  });
};
if (document.querySelector('[data-dem-nguoc]')) {
  demNguoc();
  setInterval(demNguoc, 1000);
}

// Menu cuộn ngang trên điện thoại: đưa mục đang chọn vào giữa tầm nhìn.
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.menu-trang-thong-tin [aria-current], .menu-tai-khoan nav [aria-current], .menu-khach [aria-current]').forEach((muc) => {
    const khung = muc.parentElement;
    if (khung.scrollWidth > khung.clientWidth) {
      khung.scrollLeft = muc.offsetLeft - (khung.clientWidth - muc.offsetWidth) / 2;
    }
  });
});

// Nút X trên thông báo sau thao tác (components/_thong_bao.html): ẩn thông báo, không gửi gì lên máy chủ.
document.addEventListener('click', (suKien) => {
  const nut = suKien.target.closest('[data-dong-thong-bao]');
  if (nut) nut.closest('[data-thong-bao]')?.remove();
});

// Menu thả xuống dạng <details data-menu-tha> (menu tài khoản khách): đóng khi bấm ra ngoài hoặc nhấn Esc.
document.addEventListener('click', (suKien) => {
  document.querySelectorAll('details[data-menu-tha][open]').forEach((menu) => {
    if (!menu.contains(suKien.target)) menu.open = false;
  });
});
document.addEventListener('keydown', (suKien) => {
  if (suKien.key !== 'Escape') return;
  document.querySelectorAll('details[data-menu-tha][open]').forEach((menu) => {
    menu.open = false;
    menu.querySelector('summary')?.focus();
  });
});

// Liên kết data-quay-lai: về trang trước trong cùng website; không có trang trước thì đi theo href.
document.addEventListener('click', (suKien) => {
  const lienKet = suKien.target.closest('a[data-quay-lai]');
  if (!lienKet || window.history.length < 2) return;
  try {
    if (new URL(document.referrer).origin !== window.location.origin) return;
  } catch (_) {
    return;
  }
  suKien.preventDefault();
  window.history.back();
});

// Hộp thoại xác nhận dùng chung (components/_hop_thoai.html) cho form hoặc nút có data-xac-nhan.
// Chặn ở pha bắt (capture) nên chạy trước HTMX và mọi xử lý gửi form khác; đồng ý thì gửi lại đúng nút đã bấm.
(() => {
  const hop = document.getElementById('hop-thoai-xac-nhan');
  if (!hop || typeof hop.showModal !== 'function') return; // Trình duyệt quá cũ: form gửi thẳng như trước.
  const tieuDe = hop.querySelector('[data-tieu-de]');
  const noiDung = hop.querySelector('[data-noi-dung]');
  const nutDongY = hop.querySelector('[data-nut-dong-y]');
  const nutHuy = hop.querySelector('[data-nut-huy]');
  let dangCho = null;

  document.addEventListener('submit', (suKien) => {
    const form = suKien.target;
    if (!(form instanceof HTMLFormElement) || form.method === 'dialog') return;
    const nut = suKien.submitter;
    const nguon = nut?.hasAttribute('data-xac-nhan') ? nut : form;
    const cauHoi = nguon.getAttribute('data-xac-nhan');
    if (!cauHoi) return;
    if (form.dataset.daXacNhan === '1') {
      delete form.dataset.daXacNhan;
      return;
    }
    suKien.preventDefault();
    suKien.stopPropagation();
    dangCho = { form, nut };
    tieuDe.textContent = nguon.dataset.xacNhanTieuDe || 'Xác nhận thao tác';
    noiDung.textContent = cauHoi;
    nutDongY.textContent = nguon.dataset.xacNhanNut || nut?.textContent.trim() || nut?.value || 'Đồng ý';
    const nguyHiem = nguon.dataset.xacNhanKieu === 'nguy-hiem';
    hop.dataset.kieu = nguyHiem ? 'nguy-hiem' : 'thuong';
    nutDongY.classList.toggle('nut-nguy-hiem', nguyHiem);
    hop.returnValue = '';
    hop.showModal();
    nutHuy.focus();
  }, true);

  hop.addEventListener('close', () => {
    const cho = dangCho;
    dangCho = null;
    if (!cho || hop.returnValue !== 'dong-y') {
      cho?.nut?.focus();
      return;
    }
    cho.form.dataset.daXacNhan = '1';
    const nut = cho.nut && cho.nut.form === cho.form ? cho.nut : null;
    if (typeof cho.form.requestSubmit === 'function') cho.form.requestSubmit(nut);
    else cho.form.submit();
  });
})();

// Chống gửi trùng cho form data-gui-mot-lan: sau khi gửi, nút đã bấm hiện vòng xoay và mọi nút gửi bị khóa.
// Mở lại khi HTMX trả kết quả, khi quay lại trang bằng nút Back, hoặc sau 15 giây (ví dụ form tải tệp về máy).
(() => {
  const khoa = (form, nut, bat) => {
    form.querySelectorAll('button[type="submit"], button:not([type]), input[type="submit"]').forEach((n) => {
      n.disabled = bat;
    });
    if (nut) {
      if (bat) nut.setAttribute('aria-busy', 'true');
      else nut.removeAttribute('aria-busy');
    }
    if (bat) form.dataset.dangGui = '1';
    else delete form.dataset.dangGui;
  };
  document.addEventListener('submit', (suKien) => {
    const form = suKien.target;
    if (!(form instanceof HTMLFormElement) || !form.matches('[data-gui-mot-lan]')) return;
    if (form.dataset.dangGui === '1') {
      suKien.preventDefault();
      return;
    }
    const nut = suKien.submitter;
    const laHtmx = form.matches('[hx-post], [hx-put], [hx-get], [data-hx-post]');
    // Đợi mọi xử lý khác chạy xong: form bị chặn (kiểm tra lỗi) thì không khóa nút.
    setTimeout(() => {
      if (suKien.defaultPrevented && !laHtmx) return;
      khoa(form, nut, true);
      form._moLai = setTimeout(() => khoa(form, nut, false), 15000);
    }, 0);
  });
  const moLaiTatCa = () => {
    document.querySelectorAll('form[data-dang-gui="1"]').forEach((form) => {
      clearTimeout(form._moLai);
      khoa(form, form.querySelector('[aria-busy="true"]'), false);
    });
  };
  document.addEventListener('htmx:afterRequest', moLaiTatCa);
  window.addEventListener('pageshow', (suKien) => {
    if (suKien.persisted) moLaiTatCa();
  });
})();
