// Cấu hình Chart.js dùng chung cho các trang phân tích: font, màu, định dạng số tiếng Việt.
(() => {
  if (!window.Chart) return;
  const {Chart} = window;
  const MAU = {
    chinh: '#116b54',
    chu: '#25372f',
    phu: '#66776e',
    luoi: '#e6ece6',
    vien: '#dce4dc',
  };
  // Mỗi chuỗi giữ một màu cố định trên mọi biểu đồ để người xem đối chiếu được.
  const BANG_MAU = ['#116b54', '#2f6db5', '#c27c0e', '#8a4fb0', '#c4452c', '#3f8f8b', '#7a8b2f', '#b0457a'];

  Chart.defaults.font.family = '"Be Vietnam Pro", sans-serif';
  Chart.defaults.font.size = 12;
  Chart.defaults.color = MAU.phu;
  Chart.defaults.borderColor = MAU.luoi;
  Chart.defaults.maintainAspectRatio = false;
  Chart.defaults.animation.duration = 350;
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.legend.labels.boxWidth = 8;
  Chart.defaults.plugins.legend.labels.boxHeight = 8;
  Chart.defaults.plugins.tooltip.backgroundColor = MAU.chu;
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.cornerRadius = 6;
  Chart.defaults.plugins.tooltip.titleFont = {weight: '600'};

  const dinhDangSo = (so, chuSoLe = 1) =>
    so == null || Number.isNaN(so)
      ? '–'
      : Number(so).toLocaleString('vi-VN', {maximumFractionDigits: chuSoLe, minimumFractionDigits: 0});
  const dinhDangTien = so => (so == null ? '–' : Math.round(so).toLocaleString('vi-VN') + ' đ');
  const rutGonTien = so => {
    const tri = Math.abs(so);
    if (tri >= 1e9) return dinhDangSo(so / 1e9) + ' tỷ';
    if (tri >= 1e6) return dinhDangSo(so / 1e6) + ' tr';
    if (tri >= 1e3) return dinhDangSo(so / 1e3, 0) + 'k';
    return dinhDangSo(so, 0);
  };

  // Tô nền các khoảng trên trục x, ví dụ đoạn huấn luyện / xác thực / kiểm thử.
  const nenKhoang = {
    id: 'nenKhoang',
    beforeDatasetsDraw(bieuDo, _, tuyChon) {
      const cacKhoang = tuyChon?.cacKhoang;
      if (!cacKhoang?.length) return;
      const {ctx, chartArea: vung, scales: {x}} = bieuDo;
      // Trục danh mục: tu/den là chỉ số nhãn; nới nửa bước để nền phủ trọn cột đầu và cuối.
      const nuaBuoc = x.width / Math.max(bieuDo.data.labels.length, 1) / 2;
      ctx.save();
      for (const khoang of cacKhoang) {
        const dau = Math.max(x.getPixelForValue(khoang.tu) - nuaBuoc, vung.left);
        const cuoi = Math.min(x.getPixelForValue(khoang.den) + nuaBuoc, vung.right);
        ctx.fillStyle = khoang.mau;
        ctx.fillRect(dau, vung.top, Math.max(cuoi - dau, 0), vung.bottom - vung.top);
        if (khoang.nhan) {
          ctx.fillStyle = MAU.phu;
          ctx.font = '600 11px "Be Vietnam Pro", sans-serif';
          ctx.fillText(khoang.nhan, dau + 6, vung.top + 14);
        }
      }
      ctx.restore();
    },
  };
  Chart.register(nenKhoang);

  // Vẽ lại một biểu đồ trên cùng canvas: hủy bản cũ để không rò bộ nhớ khi đổi bộ lọc.
  const veBieuDo = (canvas, cauHinh) => {
    Chart.getChart(canvas)?.destroy();
    return new Chart(canvas, cauHinh);
  };

  window.BieuDo = {MAU, BANG_MAU, dinhDangSo, dinhDangTien, rutGonTien, veBieuDo};
})();
