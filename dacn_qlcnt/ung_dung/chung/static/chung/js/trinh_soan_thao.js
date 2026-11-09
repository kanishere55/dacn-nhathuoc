// Gắn trình soạn thảo Quill cho mọi textarea[data-trinh-soan-thao]; textarea vẫn là ô gửi đi.
(() => {
  const NHAN = {
    bold: 'In đậm (Ctrl+B)', italic: 'In nghiêng (Ctrl+I)', underline: 'Gạch chân (Ctrl+U)',
    strike: 'Gạch ngang', link: 'Chèn liên kết', blockquote: 'Trích dẫn', clean: 'Xóa định dạng',
    undo: 'Hoàn tác (Ctrl+Z)', redo: 'Làm lại (Ctrl+Y)',
  };
  const BIEU_TUONG = {
    undo: '<svg viewBox="0 0 18 18"><polyline class="ql-stroke" points="5 4 2 7 5 10"/><path class="ql-stroke" d="M2 7h9a4 4 0 0 1 0 8H8"/></svg>',
    redo: '<svg viewBox="0 0 18 18"><polyline class="ql-stroke" points="13 4 16 7 13 10"/><path class="ql-stroke" d="M16 7H7a4 4 0 0 0 0 8h3"/></svg>',
  };

  const gan = (o) => {
    if (o.dataset.daGan || !window.Quill) return;
    o.dataset.daGan = '1';
    const Quill = window.Quill;
    const icons = Quill.import('ui/icons');
    Object.assign(icons, BIEU_TUONG);
    const khung = document.createElement('div');
    khung.className = 'trinh-soan-thao';
    const vung = document.createElement('div');
    khung.appendChild(vung);
    o.insertAdjacentElement('afterend', khung);
    o.hidden = true;
    const quill = new Quill(vung, {
      theme: 'snow',
      placeholder: o.getAttribute('placeholder') || 'Nhập nội dung…',
      modules: {
        history: { delay: 800, maxStack: 200, userOnly: true },
        toolbar: {
          container: [
            [{ header: [2, 3, false] }],
            ['bold', 'italic', 'underline', 'strike'],
            [{ list: 'ordered' }, { list: 'bullet' }],
            [{ align: [] }],
            ['link', 'blockquote'],
            ['clean'],
            ['undo', 'redo'],
          ],
          handlers: {
            undo() { this.quill.history.undo(); },
            redo() { this.quill.history.redo(); },
          },
        },
      },
    });
    quill.setContents(quill.clipboard.convert({ html: o.value || '' }), 'silent');
    quill.history.clear();
    const thanhCongCu = khung.querySelector('.ql-toolbar');
    Object.entries(NHAN).forEach(([ten, nhan]) => {
      thanhCongCu.querySelectorAll(`.ql-${ten}`).forEach((nut) => {
        nut.title = nhan;
        nut.setAttribute('aria-label', nhan);
      });
    });
    thanhCongCu.querySelectorAll('.ql-list').forEach((nut) => {
      const nhan = nut.value === 'ordered' ? 'Danh sách đánh số' : 'Danh sách gạch đầu dòng';
      nut.title = nhan;
      nut.setAttribute('aria-label', nhan);
    });
    const dongBo = () => {
      const html = quill.getLength() > 1 ? quill.getSemanticHTML().replace(/&nbsp;/g, ' ') : '';
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
