// Cảnh báo kiểm tra form của trình duyệt bằng tiếng Việt cho mọi trang (khách và /quan-ly/).
// Trình duyệt tự báo theo ngôn ngữ cài máy ("Please fill out this field."); ở đây thay bằng lời
// tiếng Việt cụ thể theo lỗi. Máy chủ vẫn kiểm lại toàn bộ nên tắt JS không làm lọt dữ liệu sai.
(() => {
  const so = giaTri => Number(giaTri).toLocaleString('vi-VN');

  function loiCua(o) {
    const v = o.validity;
    if (v.valueMissing) {
      if (o.type === 'checkbox') return 'Vui lòng đánh dấu ô này để tiếp tục.';
      if (o.tagName === 'SELECT' || o.type === 'radio') return 'Vui lòng chọn một mục.';
      if (o.type === 'file') return 'Vui lòng chọn tệp.';
      return 'Vui lòng nhập thông tin này.';
    }
    if (v.typeMismatch) {
      if (o.type === 'email') return 'Email chưa đúng định dạng. Ví dụ đúng: ten.ban@gmail.com.';
      if (o.type === 'url') return 'Đường dẫn chưa đúng, ví dụ https://nhathuoc.vn/trang.';
      return 'Giá trị chưa đúng định dạng.';
    }
    if (v.badInput) {
      if (o.type === 'number') return 'Vui lòng nhập một số.';
      if (o.type === 'date') return 'Ngày chưa đúng. Hãy chọn ngày trên lịch.';
      if (o.type === 'time') return 'Giờ chưa đúng, ví dụ 07:30.';
      return 'Giá trị không hợp lệ.';
    }
    if (v.patternMismatch) return o.title || 'Giá trị chưa đúng định dạng yêu cầu.';
    if (v.tooShort) return `Cần ít nhất ${o.minLength} ký tự (bạn đã nhập ${o.value.length}).`;
    if (v.tooLong) return `Tối đa ${o.maxLength} ký tự (bạn đã nhập ${o.value.length}).`;
    if (v.rangeUnderflow) {
      return o.type === 'date' ? `Ngày không được trước ${o.min.split('-').reverse().join('/')}.` : `Giá trị tối thiểu là ${so(o.min)}.`;
    }
    if (v.rangeOverflow) {
      return o.type === 'date' ? `Ngày không được sau ${o.max.split('-').reverse().join('/')}.` : `Giá trị tối đa là ${so(o.max)}.`;
    }
    if (v.stepMismatch) {
      return !o.step || o.step === '1' ? 'Vui lòng nhập số nguyên.' : `Giá trị phải là bội số của ${o.step}.`;
    }
    return 'Giá trị không hợp lệ.';
  }

  document.addEventListener(
    'invalid',
    suKien => {
      const o = suKien.target;
      // Lời riêng do script khác đặt (setCustomValidity) thì giữ nguyên.
      if (o.validity.customError && o.dataset.loiViet !== '1') return;
      o.setCustomValidity('');
      if (o.validity.valid) return;
      o.setCustomValidity(loiCua(o));
      o.dataset.loiViet = '1';
    },
    true,
  );

  function xoaLoi(suKien) {
    const o = suKien.target;
    if (o?.dataset?.loiViet !== '1') return;
    o.setCustomValidity('');
    delete o.dataset.loiViet;
    // Nhóm radio: bỏ lỗi ở mọi ô cùng tên.
    if (o.type === 'radio' && o.form && o.name) {
      o.form.querySelectorAll(`input[type=radio][name="${CSS.escape(o.name)}"]`).forEach(ban => {
        ban.setCustomValidity('');
        delete ban.dataset.loiViet;
      });
    }
  }
  document.addEventListener('input', xoaLoi, true);
  document.addEventListener('change', xoaLoi, true);
})();
