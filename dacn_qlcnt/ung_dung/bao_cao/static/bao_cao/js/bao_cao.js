// Báo cáo vận hành: vẽ biểu đồ từ số liệu server nhúng sẵn; vẽ lại sau mỗi lần HTMX lọc kỳ.
(() => {
  const {MAU, BANG_MAU, dinhDangSo, dinhDangTien, rutGonTien, veBieuDo} = window.BieuDo;

  const nhanMoc = (iso, donVi) => {
    const [nam, thang, ngay] = iso.split('-');
    return donVi === 'thang' ? `${thang}/${nam}` : `${ngay}/${thang}`;
  };

  // Khi kỳ chưa có dữ liệu, thay canvas bằng một dòng giải thích thay vì trục trống.
  function trongHoacVe(canvas, coDuLieu, cauHinh) {
    const vung = canvas.parentElement;
    vung.querySelector('.bieu-do-trong')?.remove();
    canvas.hidden = !coDuLieu;
    if (!coDuLieu) {
      window.Chart.getChart(canvas)?.destroy();
      const thongBao = document.createElement('p');
      thongBao.className = 'bieu-do-trong';
      thongBao.textContent = 'Chưa có dữ liệu trong kỳ đã chọn.';
      vung.append(thongBao);
      return;
    }
    veBieuDo(canvas, cauHinh);
  }

  function veTatCa() {
    const nguon = document.getElementById('du-lieu-bieu-do-bao-cao');
    const khung = document.querySelector('[data-bieu-do-bao-cao]');
    if (!nguon || !khung) return;
    const duLieu = JSON.parse(nguon.textContent);
    const canvas = ten => khung.querySelector(`[data-bieu-do="${ten}"]`);

    const tg = duLieu.theo_thoi_gian;
    trongHoacVe(canvas('thoi_gian'), tg.some(m => m.doanh_thu > 0), {
      type: 'bar',
      data: {
        labels: tg.map(m => nhanMoc(m.moc, duLieu.don_vi_thoi_gian)),
        datasets: [
          {
            type: 'line',
            label: 'Số phiếu bán',
            data: tg.map(m => m.so_phieu),
            yAxisID: 'phieu',
            borderColor: '#c27c0e',
            backgroundColor: '#c27c0e',
            borderWidth: 2,
            pointRadius: 2,
            tension: 0.3,
          },
          {
            label: 'Doanh thu',
            data: tg.map(m => m.doanh_thu),
            yAxisID: 'tien',
            backgroundColor: 'rgba(17, 107, 84, 0.75)',
            borderRadius: 3,
          },
        ],
      },
      options: {
        interaction: {mode: 'index', intersect: false},
        scales: {
          x: {grid: {display: false}, ticks: {maxTicksLimit: 10, maxRotation: 0}},
          tien: {position: 'left', beginAtZero: true, ticks: {callback: rutGonTien}},
          phieu: {position: 'right', beginAtZero: true, grid: {display: false}, ticks: {precision: 0}},
        },
        plugins: {
          legend: {position: 'bottom'},
          tooltip: {
            callbacks: {
              label: muc =>
                muc.dataset.yAxisID === 'tien'
                  ? ` Doanh thu: ${dinhDangTien(muc.parsed.y)}`
                  : ` Số phiếu: ${muc.parsed.y}`,
            },
          },
        },
      },
    });

    const banhVong = (ten, cacMuc, truong) =>
      trongHoacVe(canvas(ten), cacMuc.some(m => m[truong] > 0), {
        type: 'doughnut',
        data: {
          labels: cacMuc.map(m => m.ten),
          datasets: [{data: cacMuc.map(m => m[truong]), backgroundColor: BANG_MAU, borderWidth: 2, borderColor: '#fff'}],
        },
        options: {
          cutout: '62%',
          plugins: {
            legend: {position: 'bottom'},
            tooltip: {
              callbacks: {
                label: muc => {
                  const tong = muc.dataset.data.reduce((a, b) => a + b, 0) || 1;
                  return ` ${muc.label}: ${dinhDangTien(muc.parsed)} (${dinhDangSo((muc.parsed / tong) * 100, 0)}%)`;
                },
              },
            },
          },
        },
      });
    banhVong('kenh', duLieu.theo_kenh, 'doanh_thu');

    const banChay = duLieu.ban_chay;
    trongHoacVe(canvas('ban_chay'), banChay.length > 0, {
      type: 'bar',
      data: {
        labels: banChay.map(m => (m.ten.length > 20 ? m.ten.slice(0, 19) + '…' : m.ten)),
        datasets: [{label: 'Doanh thu', data: banChay.map(m => m.doanh_thu), backgroundColor: MAU.chinh, borderRadius: 3}],
      },
      options: {
        indexAxis: 'y',
        scales: {
          x: {beginAtZero: true, ticks: {callback: rutGonTien}},
          y: {grid: {display: false}, ticks: {color: MAU.chu}},
        },
        plugins: {
          legend: {display: false},
          tooltip: {
            callbacks: {
              title: muc => banChay[muc[0].dataIndex].ten,
              label: muc => {
                const thuoc = banChay[muc.dataIndex];
                return ` ${dinhDangTien(muc.parsed.x)} · ${dinhDangSo(thuoc.so_luong, 0)} ${thuoc.don_vi.toLowerCase()}`;
              },
            },
          },
        },
      },
    });

    if (canvas('chi_nhanh')) {
      const cn = duLieu.theo_chi_nhanh;
      trongHoacVe(canvas('chi_nhanh'), cn.length > 0, {
        type: 'bar',
        data: {
          labels: cn.map(m => m.ten),
          datasets: [{data: cn.map(m => m.doanh_thu), backgroundColor: BANG_MAU, borderRadius: 3}],
        },
        options: {
          indexAxis: 'y',
          scales: {x: {beginAtZero: true, ticks: {callback: rutGonTien}}, y: {grid: {display: false}, ticks: {color: MAU.chu}}},
          plugins: {legend: {display: false}, tooltip: {callbacks: {label: muc => ` ${dinhDangTien(muc.parsed.x)}`}}},
        },
      });
    }
    if (canvas('phuong_thuc')) banhVong('phuong_thuc', duLieu.theo_phuong_thuc, 'so_tien');
  }

  veTatCa();
  // Bộ lọc dùng hx-swap="outerHTML" nên khối kết quả là phần tử mới: vẽ lại theo số liệu mới.
  document.body.addEventListener('htmx:afterSettle', veTatCa);
})();
