// Form gửi tin đầu tiên (hỏi dược sĩ, nhắn về đơn): bấm mẫu câu để điền, Enter để gửi,
// chọn ảnh có xem trước và bỏ từng ảnh, khóa nút sau khi bấm để không tạo hai tin vì bấm hai lần.
(() => {
  document.querySelectorAll('[data-soan-tin]').forEach(form => {
    const oNhap = form.querySelector('textarea');
    const nut = form.querySelector('button[type=submit]');
    const oAnh = form.querySelector('[data-chon-anh]');
    const vungAnh = form.querySelector('[data-xem-truoc-anh]');
    const baoLoi = form.querySelector('[data-loi-anh]');
    const boAnh =
      oAnh && vungAnh && window.taoBoChonAnh
        ? window.taoBoChonAnh({
            oChon: oAnh,
            vung: vungAnh,
            dongBoInput: true,
            baoLoi: chu => {
              if (baoLoi) {
                baoLoi.textContent = chu;
                baoLoi.hidden = !chu;
              }
            },
          })
        : null;
    let daChuanBi = false;

    form.querySelectorAll('[data-goi-y-nhanh] button').forEach(nutGoiY =>
      nutGoiY.addEventListener('click', () => {
        oNhap.value = nutGoiY.dataset.cau;
        oNhap.focus();
      }),
    );
    oNhap?.addEventListener('keydown', suKien => {
      if (suKien.key === 'Enter' && !suKien.shiftKey && !suKien.isComposing) {
        suKien.preventDefault();
        form.requestSubmit();
      }
    });
    oNhap?.addEventListener('paste', suKien => {
      const cacTep = [...(suKien.clipboardData?.files || [])];
      if (cacTep.length && boAnh) {
        suKien.preventDefault();
        boAnh.them(cacTep);
      }
    });
    form.addEventListener('submit', async suKien => {
      if (!oNhap.value.trim() && !boAnh?.soLuong()) {
        suKien.preventDefault();
        oNhap.setCustomValidity('Hãy nhập nội dung tin nhắn hoặc chọn ảnh.');
        oNhap.reportValidity();
        oNhap.addEventListener('input', () => oNhap.setCustomValidity(''), {once: true});
        return;
      }
      if (boAnh?.soLuong() && !daChuanBi) {
        // Thu nhỏ ảnh lớn trước khi gửi rồi gửi lại form với các tệp đã thu nhỏ.
        suKien.preventDefault();
        nut.disabled = true;
        try {
          const cacTep = await boAnh.chuanBi();
          const dt = new DataTransfer();
          cacTep.forEach(tep => dt.items.add(tep));
          oAnh.files = dt.files;
          daChuanBi = true;
          form.submit();
        } catch (loi) {
          nut.disabled = false;
          if (baoLoi) {
            baoLoi.textContent = loi.message;
            baoLoi.hidden = false;
          }
        }
        return;
      }
      nut.disabled = true;
      nut.setAttribute('aria-busy', 'true');
    });
  });
})();
