// Gắn trình soạn thảo Quill cho mọi textarea[data-trinh-soan-thao]; textarea vẫn là ô gửi đi.
// Tính năng: tiêu đề, cỡ chữ, đậm/nghiêng/gạch chân/gạch ngang, màu chữ và màu nền, chỉ số trên/dưới,
// danh sách, thụt lề, căn lề, liên kết, trích dẫn, chèn ảnh (tải lên CSDL) có chỉnh kích thước và vị trí.
(() => {
  const NHAN = {
    bold: 'In đậm (Ctrl+B)', italic: 'In nghiêng (Ctrl+I)', underline: 'Gạch chân (Ctrl+U)',
    strike: 'Gạch ngang', link: 'Chèn liên kết', blockquote: 'Trích dẫn', clean: 'Xóa định dạng',
    undo: 'Hoàn tác (Ctrl+Z)', redo: 'Làm lại (Ctrl+Y)', image: 'Chèn ảnh từ máy tính',
  };
  const NHAN_CHON = {
    'ql-header': 'Kiểu đoạn văn', 'ql-size': 'Cỡ chữ', 'ql-color': 'Màu chữ',
    'ql-background': 'Màu nền chữ', 'ql-align': 'Căn lề',
  };
  const BIEU_TUONG = {
    undo: '<svg viewBox="0 0 18 18"><polyline class="ql-stroke" points="5 4 2 7 5 10"/><path class="ql-stroke" d="M2 7h9a4 4 0 0 1 0 8H8"/></svg>',
    redo: '<svg viewBox="0 0 18 18"><polyline class="ql-stroke" points="13 4 16 7 13 10"/><path class="ql-stroke" d="M16 7H7a4 4 0 0 0 0 8h3"/></svg>',
  };
  const CO_BAN = 'anh-nd-rong-50';
  const LOP_RONG = ['anh-nd-rong-25', 'anh-nd-rong-50', 'anh-nd-rong-75', 'anh-nd-rong-100'];
  const LOP_VI_TRI = ['anh-nd-trai', 'anh-nd-giua', 'anh-nd-phai'];

  let daDangKy = false;
  const dangKyDinhDang = (Quill) => {
    if (daDangKy) return;
    daDangKy = true;
    Object.assign(Quill.import('ui/icons'), BIEU_TUONG);
    // Ảnh giữ thêm lớp kích thước/vị trí để khách thấy đúng như lúc soạn.
    const Anh = Quill.import('formats/image');
    class AnhNoiDung extends Anh {
      static formats(nut) {
        const dinhDang = super.formats(nut);
        const lop = [...nut.classList].filter((l) => l.startsWith('anh-nd-'));
        if (lop.length) dinhDang.lop = lop.join(' ');
        return dinhDang;
      }
      format(ten, giaTri) {
        if (ten === 'lop') {
          if (giaTri) this.domNode.className = giaTri;
          else this.domNode.removeAttribute('class');
        } else {
          super.format(ten, giaTri);
        }
      }
    }
    AnhNoiDung.blotName = 'image';
    AnhNoiDung.tagName = 'IMG';
    Quill.register(AnhNoiDung, true);
  };

  const layCsrf = () =>
    document.querySelector('input[name=csrfmiddlewaretoken]')?.value ||
    document.cookie.split('; ').find((c) => c.startsWith('csrftoken='))?.split('=')[1] || '';

  const taiAnhLen = async (url, tep) => {
    const du = new FormData();
    du.append('anh', tep);
    const phanHoi = await fetch(url, {
      method: 'POST', body: du, credentials: 'same-origin',
      headers: { 'X-CSRFToken': layCsrf(), 'X-Requested-With': 'XMLHttpRequest' },
    });
    let ketQua = {};
    try { ketQua = await phanHoi.json(); } catch (_) { /* phản hồi không phải JSON */ }
    if (!phanHoi.ok || !ketQua.ok) throw new Error(ketQua.thong_diep || 'Không tải được ảnh lên.');
    return ketQua.url;
  };

  const gan = (o) => {
    if (o.dataset.daGan || !window.Quill) return;
    o.dataset.daGan = '1';
    const Quill = window.Quill;
    dangKyDinhDang(Quill);
    const khung = document.createElement('div');
    khung.className = 'trinh-soan-thao';
    const vung = document.createElement('div');
    khung.appendChild(vung);
    o.insertAdjacentElement('afterend', khung);
    o.hidden = true;
    const urlTaiAnh = o.dataset.urlTaiAnh;
    const thanhCongCu = [
      [{ header: [2, 3, 4, false] }, { size: ['small', false, 'large', 'huge'] }],
      ['bold', 'italic', 'underline', 'strike'],
      [{ color: [] }, { background: [] }],
      [{ script: 'sub' }, { script: 'super' }],
      [{ list: 'ordered' }, { list: 'bullet' }, { indent: '-1' }, { indent: '+1' }],
      [{ align: [] }],
      ['link', 'blockquote', ...(urlTaiAnh ? ['image'] : [])],
      ['clean'],
      ['undo', 'redo'],
    ];
    const quill = new Quill(vung, {
      theme: 'snow',
      placeholder: o.getAttribute('placeholder') || 'Nhập nội dung…',
      modules: {
        history: { delay: 800, maxStack: 200, userOnly: true },
        toolbar: {
          container: thanhCongCu,
          handlers: {
            undo() { this.quill.history.undo(); },
            redo() { this.quill.history.redo(); },
            image() { chonVaChenAnh(); },
          },
        },
      },
    });
    quill.setContents(quill.clipboard.convert({ html: o.value || '' }), 'silent');
    quill.history.clear();

    const thanh = khung.querySelector('.ql-toolbar');
    Object.entries(NHAN).forEach(([ten, nhan]) => {
      thanh.querySelectorAll(`.ql-${ten}`).forEach((nut) => {
        nut.title = nhan;
        nut.setAttribute('aria-label', nhan);
      });
    });
    Object.entries(NHAN_CHON).forEach(([lop, nhan]) => {
      thanh.querySelectorAll(`.ql-picker.${lop}`).forEach((chon) => { chon.title = nhan; });
    });
    thanh.querySelectorAll('.ql-list').forEach((nut) => {
      const nhan = nut.value === 'ordered' ? 'Danh sách đánh số' : 'Danh sách gạch đầu dòng';
      nut.title = nhan;
      nut.setAttribute('aria-label', nhan);
    });
    thanh.querySelectorAll('.ql-indent').forEach((nut) => {
      nut.title = nut.value === '+1' ? 'Thụt vào' : 'Thụt ra';
    });
    thanh.querySelectorAll('.ql-script').forEach((nut) => {
      nut.title = nut.value === 'sub' ? 'Chỉ số dưới' : 'Chỉ số trên';
    });

    // Báo lỗi và tiến trình ngay dưới khung soạn.
    const thongBao = document.createElement('p');
    thongBao.className = 'thong-bao-anh';
    thongBao.setAttribute('role', 'status');
    khung.insertAdjacentElement('afterend', thongBao);
    const bao = (chu, loi = false) => {
      thongBao.textContent = chu;
      thongBao.classList.toggle('loi', loi);
    };

    const chenAnh = async (tep) => {
      if (!tep || !tep.type.startsWith('image/')) { bao('Chỉ chèn được tệp ảnh.', true); return; }
      bao('Đang tải ảnh lên…');
      try {
        const url = await taiAnhLen(urlTaiAnh, tep);
        const vitri = (quill.getSelection(true) || { index: quill.getLength() }).index;
        quill.insertEmbed(vitri, 'image', url, 'user');
        quill.formatText(vitri, 1, 'lop', CO_BAN, 'user');
        quill.formatText(vitri, 1, 'alt', tep.name.replace(/\.[^.]+$/, ''), 'user');
        quill.setSelection(vitri + 1, 0, 'silent');
        bao('Đã chèn ảnh. Bấm vào ảnh để chỉnh kích thước và vị trí.');
      } catch (loi) {
        bao(loi.message, true);
      }
    };
    const chonVaChenAnh = () => {
      const chon = document.createElement('input');
      chon.type = 'file';
      chon.accept = 'image/jpeg,image/png,image/webp,image/gif';
      chon.addEventListener('change', () => chenAnh(chon.files[0]));
      chon.click();
    };
    if (urlTaiAnh) {
      // Dán hoặc kéo thả ảnh thẳng vào khung soạn cũng tải lên CSDL.
      // Giai đoạn capture + stopImmediatePropagation để Quill không chèn thêm bản ảnh data: của riêng nó.
      const chanVaChen = (e, danhSachTep) => {
        const tep = [...(danhSachTep || [])].find((t) => t.type.startsWith('image/'));
        if (!tep) return;
        e.preventDefault();
        e.stopImmediatePropagation();
        chenAnh(tep);
      };
      quill.root.addEventListener('paste', (e) => chanVaChen(e, e.clipboardData?.files), true);
      quill.root.addEventListener('drop', (e) => chanVaChen(e, e.dataTransfer?.files), true);
    }

    // Thanh chỉnh ảnh nổi: kích thước, vị trí, chữ thay thế, xóa.
    const thanhAnh = document.createElement('div');
    thanhAnh.className = 'thanh-chinh-anh';
    thanhAnh.hidden = true;
    thanhAnh.innerHTML = [
      '<span>Rộng</span>',
      ...[25, 50, 75, 100].map((p) => `<button type="button" data-rong="${p}">${p}%</button>`),
      '<span>Vị trí</span>',
      '<button type="button" data-vi-tri="trai" title="Ảnh bên trái, chữ chạy quanh">Trái</button>',
      '<button type="button" data-vi-tri="giua" title="Ảnh ở giữa, tách dòng">Giữa</button>',
      '<button type="button" data-vi-tri="phai" title="Ảnh bên phải, chữ chạy quanh">Phải</button>',
      '<button type="button" data-hanh-dong="alt">Mô tả ảnh</button>',
      '<button type="button" data-hanh-dong="xoa" class="nguy-hiem">Xóa ảnh</button>',
    ].join('');
    khung.appendChild(thanhAnh);
    let anhDangChon = null;
    const hienThanhAnh = (anh) => {
      anhDangChon = anh;
      quill.root.querySelectorAll('img.dang-chon').forEach((a) => a.classList.remove('dang-chon'));
      if (!anh) { thanhAnh.hidden = true; return; }
      anh.classList.add('dang-chon');
      thanhAnh.hidden = false;
      const lop = [...anh.classList];
      thanhAnh.querySelectorAll('[data-rong]').forEach((n) => n.classList.toggle('dang-chon', lop.includes(`anh-nd-rong-${n.dataset.rong}`)));
      thanhAnh.querySelectorAll('[data-vi-tri]').forEach((n) => n.classList.toggle('dang-chon', lop.includes(`anh-nd-${n.dataset.viTri}`)));
    };
    const doiLop = (nhomLop, lopMoi) => {
      if (!anhDangChon) return;
      const blot = Quill.find(anhDangChon);
      if (!blot) return;
      const chiSo = quill.getIndex(blot);
      const lop = [...anhDangChon.classList].filter((l) => l.startsWith('anh-nd-') && !nhomLop.includes(l));
      quill.formatText(chiSo, 1, 'lop', [...lop, lopMoi].join(' '), 'user');
      hienThanhAnh(anhDangChon);
    };
    quill.root.addEventListener('click', (e) => hienThanhAnh(e.target.tagName === 'IMG' ? e.target : null));
    thanhAnh.addEventListener('click', (e) => {
      const nut = e.target.closest('button');
      if (!nut || !anhDangChon) return;
      if (nut.dataset.rong) doiLop(LOP_RONG, `anh-nd-rong-${nut.dataset.rong}`);
      else if (nut.dataset.viTri) doiLop(LOP_VI_TRI, `anh-nd-${nut.dataset.viTri}`);
      else if (nut.dataset.hanhDong === 'alt') {
        const blot = Quill.find(anhDangChon);
        const moi = window.prompt('Mô tả ảnh (cho người khiếm thị và khi ảnh không tải được):', anhDangChon.getAttribute('alt') || '');
        if (blot && moi !== null) quill.formatText(quill.getIndex(blot), 1, 'alt', moi.slice(0, 200), 'user');
      } else if (nut.dataset.hanhDong === 'xoa') {
        const blot = Quill.find(anhDangChon);
        if (blot) quill.deleteText(quill.getIndex(blot), 1, 'user');
        hienThanhAnh(null);
      }
    });

    const dongBo = () => {
      const html = quill.getLength() > 1 || quill.root.querySelector('img')
        ? quill.getSemanticHTML().replace(/&nbsp;/g, ' ')
        : '';
      o.value = html;
    };
    quill.on('text-change', dongBo);
    o.form?.addEventListener('submit', dongBo);
    const nhan = document.querySelector(`label[for="${o.id}"]`);
    nhan?.addEventListener('click', (e) => { e.preventDefault(); quill.focus(); });
  };

  const ganTatCa = () => document.querySelectorAll('textarea[data-trinh-soan-thao]').forEach(gan);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ganTatCa);
  else ganTatCa();
})();
