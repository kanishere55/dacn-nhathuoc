// Bộ chọn ảnh dùng chung cho khung chat và form tin đầu: kiểm loại, dung lượng, tối đa 5 ảnh,
// hiện ảnh thu nhỏ để người gửi xem đúng ảnh chưa, bấm X để bỏ từng ảnh rồi chọn ảnh khác.
// Trước khi gửi, ảnh lớn được thu về cạnh dài 1600 px (máy chủ cũng chỉ giữ cỡ này) để ảnh chụp
// điện thoại 5–10 MB không vượt giới hạn tải lên. Máy chủ vẫn kiểm lại toàn bộ.
(() => {
  const SO_ANH_TOI_DA = 5;
  const BYTE_TOI_DA_MOI_ANH = 10 * 1024 * 1024;
  const BYTE_TONG_TOI_DA = 9.5 * 1024 * 1024;
  const CANH_TOI_DA = 1600;
  const KIEU_NHAN = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];

  const coMb = byte =>
    byte < 1024 * 1024
      ? `${Math.max(1, Math.round(byte / 1024))} KB`
      : `${(byte / 1024 / 1024).toLocaleString('vi-VN', {maximumFractionDigits: 1})} MB`;

  async function thuNho(tep) {
    if (tep.type === 'image/gif' || !window.createImageBitmap) return tep;
    let anh;
    try {
      anh = await createImageBitmap(tep, {imageOrientation: 'from-image'});
    } catch {
      return tep;
    }
    const tiLe = Math.min(1, CANH_TOI_DA / Math.max(anh.width, anh.height));
    if (tiLe === 1 && tep.size <= 1.5 * 1024 * 1024) return tep;
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(anh.width * tiLe);
    canvas.height = Math.round(anh.height * tiLe);
    canvas.getContext('2d').drawImage(anh, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise(xong => canvas.toBlob(xong, 'image/jpeg', 0.88));
    if (!blob || blob.size >= tep.size) return tep;
    return new File([blob], tep.name.replace(/\.[^.]+$/, '') + '.jpg', {type: 'image/jpeg'});
  }

  window.taoBoChonAnh = function ({oChon, vung, khiDoi = () => {}, baoLoi = () => {}, dongBoInput = false}) {
    let cacAnh = []; // {tep, url}

    function dongBo() {
      if (!dongBoInput || !window.DataTransfer) return;
      const dt = new DataTransfer();
      cacAnh.forEach(muc => dt.items.add(muc.tep));
      oChon.files = dt.files;
    }

    function ve() {
      vung.replaceChildren(
        ...cacAnh.map((muc, i) => {
          const dong = document.createElement('li');
          const anh = document.createElement('img');
          anh.src = muc.url;
          anh.alt = `Ảnh sẽ gửi ${i + 1}: ${muc.tep.name}`;
          const nut = document.createElement('button');
          nut.type = 'button';
          nut.className = 'nut-bo-anh';
          nut.title = 'Bỏ ảnh này';
          nut.setAttribute('aria-label', `Bỏ ảnh ${muc.tep.name}`);
          nut.textContent = '×';
          nut.addEventListener('click', () => bo(i));
          const ten = document.createElement('small');
          ten.textContent = coMb(muc.tep.size);
          dong.append(anh, nut, ten);
          return dong;
        }),
      );
      vung.hidden = cacAnh.length === 0;
      dongBo();
      khiDoi(cacAnh.length);
    }

    function them(danhSach) {
      const loi = [];
      for (const tep of danhSach) {
        if (!KIEU_NHAN.includes(tep.type)) {
          loi.push(`"${tep.name}" không phải ảnh JPEG, PNG, WebP hoặc GIF.`);
        } else if (tep.size > BYTE_TOI_DA_MOI_ANH) {
          loi.push(`"${tep.name}" nặng ${coMb(tep.size)}, mỗi ảnh tối đa 10 MB.`);
        } else if (cacAnh.length >= SO_ANH_TOI_DA) {
          loi.push(`Mỗi tin gửi tối đa ${SO_ANH_TOI_DA} ảnh. Bỏ bớt ảnh rồi chọn lại.`);
          break;
        } else {
          cacAnh.push({tep, url: URL.createObjectURL(tep)});
        }
      }
      baoLoi(loi.join(' '));
      ve();
    }

    function bo(i) {
      URL.revokeObjectURL(cacAnh[i].url);
      cacAnh.splice(i, 1);
      baoLoi('');
      ve();
    }

    function xoaHet() {
      cacAnh.forEach(muc => URL.revokeObjectURL(muc.url));
      cacAnh = [];
      ve();
    }

    // Thu nhỏ rồi trả danh sách tệp sẵn sàng gửi; báo lỗi khi tổng vẫn vượt giới hạn.
    async function chuanBi() {
      const cacTep = await Promise.all(cacAnh.map(muc => thuNho(muc.tep)));
      const tong = cacTep.reduce((cong, tep) => cong + tep.size, 0);
      if (tong > BYTE_TONG_TOI_DA) {
        throw new Error(`Các ảnh nặng tổng cộng ${coMb(tong)}, vượt giới hạn 9,5 MB. Hãy bỏ bớt ảnh.`);
      }
      return cacTep;
    }

    oChon.addEventListener('change', () => {
      // Trình duyệt chỉ giữ lần chọn mới nhất trong ô tệp; danh sách đầy đủ nằm ở cacAnh
      // (chọn thêm lần nữa thì nối vào), ô tệp được dựng lại từ cacAnh khi cần gửi bằng form.
      const moi = [...oChon.files];
      if (!dongBoInput) oChon.value = '';
      them(moi);
    });

    return {them, xoaHet, chuanBi, soLuong: () => cacAnh.length, dongBo};
  };
})();
