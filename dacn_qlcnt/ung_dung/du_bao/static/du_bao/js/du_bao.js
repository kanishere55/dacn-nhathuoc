// Trang dự báo: chọn nhóm ATC → Fetch dữ liệu nhóm → vẽ biểu đồ và nhận xét; tính thử kịch bản thiếu hàng.
(() => {
  const {MAU, BANG_MAU, dinhDangSo, veBieuDo} = window.BieuDo;
  const khung = document.getElementById('chi-tiet-nhom');
  if (!khung) return;

  const cacThe = [...document.querySelectorAll('[data-nhom]')];
  const urlMau = khung.dataset.urlMau;
  const bao = khung.querySelector('[data-trang-thai]');
  const canvas = ten => khung.querySelector(`[data-bieu-do="${ten}"]`);
  const boNho = new Map();
  const dangBat = new Set();
  let duLieu = null;
  let dangTai = null;

  const hep = () => window.matchMedia('(max-width: 600px)').matches;
  const THANG = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12'];
  const THU = ['', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];
  const ngayVN = iso => {
    const [nam, thang, ngay] = iso.split('-');
    return `${ngay}/${thang}/${nam}`;
  };
  const congNgay = (iso, soNgay) => {
    const ngay = new Date(iso + 'T00:00:00');
    ngay.setDate(ngay.getDate() + soNgay);
    return ngay.toLocaleDateString('vi-VN');
  };
  const mauMoHinh = ma => BANG_MAU[1 + duLieu.cac_mo_hinh.findIndex(m => m.ma === ma)] || MAU.phu;
  const tao = (the, lop, chu) => {
    const phanTu = document.createElement(the);
    if (lop) phanTu.className = lop;
    if (chu != null) phanTu.textContent = chu;
    return phanTu;
  };

  // Ngày gốc liên tiếp cho các tổng 7 ngày chồng lấp nhau; lấy mỗi 7 ngày một điểm (tính từ
  // ngày cuối) để mỗi điểm là một tuần riêng biệt, biểu đồ đỡ dày và dễ đọc.
  function layTheoTuan(kt) {
    const chiSo = [];
    for (let i = kt.ngay.length - 1; i >= 0; i -= 7) chiSo.unshift(i);
    const lay = mang => chiSo.map(i => mang[i]);
    return {
      ngay: lay(kt.ngay),
      thuc_te: lay(kt.thuc_te),
      du_bao: Object.fromEntries(Object.entries(kt.du_bao).map(([ma, mang]) => [ma, lay(mang)])),
    };
  }

  function veKiemThu() {
    const kt = layTheoTuan(duLieu.kiem_thu);
    const cacDuong = [
      {
        label: 'Thực tế',
        data: kt.thuc_te,
        borderColor: MAU.chu,
        backgroundColor: MAU.chu,
        borderWidth: 2,
        pointRadius: 2,
        tension: 0.25,
        order: 0,
      },
      ...duLieu.cac_mo_hinh
        .filter(m => dangBat.has(m.ma))
        .map(m => ({
          label: m.ten + (m.duoc_chon ? ' (được chọn)' : ''),
          data: kt.du_bao[m.ma],
          borderColor: mauMoHinh(m.ma),
          backgroundColor: mauMoHinh(m.ma),
          borderWidth: m.duoc_chon ? 2.2 : 1.4,
          borderDash: m.duoc_chon ? [] : [5, 4],
          pointRadius: 0,
          tension: 0.25,
          order: m.duoc_chon ? 1 : 2,
        })),
    ];
    veBieuDo(canvas('kiem_thu'), {
      type: 'line',
      data: {labels: kt.ngay.map(ngayVN), datasets: cacDuong},
      options: {
        interaction: {mode: 'index', intersect: false},
        scales: {
          x: {
            grid: {display: false},
            ticks: {
              maxRotation: 0,
              maxTicksLimit: hep() ? 4 : 8,
              // Trục chỉ cần tháng/năm; ngày đầy đủ vẫn có trong tooltip.
              callback(giaTri) {
                return this.getLabelForValue(giaTri).slice(3);
              },
            },
          },
          y: {title: {display: !hep(), text: 'Tổng 7 ngày (đơn vị nguồn)'}, beginAtZero: true},
        },
        plugins: {
          legend: {position: 'bottom'},
          tooltip: {
            callbacks: {
              title: muc => `Tuần sau ngày ${muc[0].label}`,
              label: muc => ` ${muc.dataset.label}: ${dinhDangSo(muc.parsed.y)}`,
            },
          },
        },
      },
    });
  }

  function veCongTac() {
    const vung = khung.querySelector('[data-cong-tac]');
    vung.replaceChildren(
      ...duLieu.cac_mo_hinh.map(m => {
        const nut = tao('button', 'cong-tac-mo-hinh');
        nut.type = 'button';
        nut.setAttribute('aria-pressed', String(dangBat.has(m.ma)));
        nut.style.setProperty('--mau', mauMoHinh(m.ma));
        nut.append(tao('span', 'cham'), m.ten + (m.duoc_chon ? ' · được chọn' : ''));
        nut.addEventListener('click', () => {
          dangBat.has(m.ma) ? dangBat.delete(m.ma) : dangBat.add(m.ma);
          nut.setAttribute('aria-pressed', String(dangBat.has(m.ma)));
          veKiemThu();
        });
        return nut;
      }),
    );
  }

  function veSaiSo() {
    const cacMoHinh = duLieu.cac_mo_hinh;
    veBieuDo(canvas('sai_so'), {
      type: 'bar',
      data: {
        labels: cacMoHinh.map(m => (m.duoc_chon ? `${m.ten} ✓` : m.ten)),
        datasets: [
          {
            label: 'MAE kiểm thử',
            data: cacMoHinh.map(m => m.mae_kiem_thu),
            backgroundColor: cacMoHinh.map(m => (m.duoc_chon ? MAU.chinh : '#8fbfae')),
            borderRadius: 4,
          },
          {
            label: 'RMSE kiểm thử',
            data: cacMoHinh.map(m => m.rmse_kiem_thu),
            backgroundColor: cacMoHinh.map(m => (m.duoc_chon ? '#c27c0e' : '#e8c58f')),
            borderRadius: 4,
          },
        ],
      },
      options: {
        indexAxis: 'y',
        scales: {
          x: {beginAtZero: true},
          y: {grid: {display: false}, ticks: {color: MAU.chu}},
        },
        plugins: {
          legend: {position: 'bottom'},
          tooltip: {callbacks: {label: muc => ` ${muc.dataset.label}: ${dinhDangSo(muc.parsed.x, 2)}`}},
        },
      },
    });
  }

  function veMuaVu() {
    const cacThang = duLieu.mua_vu;
    const lonNhat = Math.max(...cacThang.map(t => t.tb));
    const nhoNhat = Math.min(...cacThang.map(t => t.tb));
    veBieuDo(canvas('mua_vu'), {
      type: 'bar',
      data: {
        labels: cacThang.map(t => THANG[t.thang - 1]),
        datasets: [
          {
            label: 'Trung bình mỗi ngày',
            data: cacThang.map(t => t.tb),
            backgroundColor: cacThang.map(t =>
              t.tb === lonNhat ? MAU.chinh : t.tb === nhoNhat ? '#c4452c' : '#a9cfc0',
            ),
            borderRadius: 4,
          },
        ],
      },
      options: {
        scales: {x: {grid: {display: false}}, y: {beginAtZero: true}},
        plugins: {
          legend: {display: false},
          tooltip: {callbacks: {label: muc => ` ${dinhDangSo(muc.parsed.y, 2)} mỗi ngày`}},
        },
      },
    });
  }

  function veTheoThang() {
    const cacThang = duLieu.theo_thang;
    const nhan = cacThang.map(t => t.thang.slice(5) + '/' + t.thang.slice(0, 4));
    const viTri = iso => Math.max(0, cacThang.findIndex(t => t.thang === iso.slice(0, 7)));
    const {huan_luyen: hl, xac_thuc: xt, kiem_thu: kt} = duLieu.moc;
    veBieuDo(canvas('theo_thang'), {
      type: 'line',
      data: {
        labels: nhan,
        datasets: [
          {
            label: 'Trung bình mỗi ngày trong tháng',
            data: cacThang.map(t => t.tb),
            borderColor: MAU.chinh,
            backgroundColor: 'rgba(17, 107, 84, 0.12)',
            fill: true,
            borderWidth: 2,
            pointRadius: 2,
            tension: 0.3,
          },
        ],
      },
      options: {
        interaction: {mode: 'index', intersect: false},
        scales: {
          x: {ticks: {maxTicksLimit: hep() ? 5 : 12, maxRotation: 0}, grid: {display: false}},
          y: {beginAtZero: true},
        },
        plugins: {
          legend: {display: false},
          nenKhoang: {
            cacKhoang: [
              {tu: 0, den: viTri(hl), mau: 'rgba(17, 107, 84, 0.04)', nhan: 'Huấn luyện'},
              {tu: viTri(hl) + 1, den: viTri(xt), mau: 'rgba(194, 124, 14, 0.09)', nhan: 'Xác thực'},
              {tu: viTri(xt) + 1, den: viTri(kt), mau: 'rgba(47, 109, 181, 0.09)', nhan: 'Kiểm thử'},
            ],
          },
          tooltip: {
            callbacks: {
              title: muc => `Tháng ${muc[0].label}`,
              label: muc => {
                const thang = cacThang[muc.dataIndex];
                return ` ${dinhDangSo(thang.tb, 2)} mỗi ngày · ${thang.so_ngay} ngày dữ liệu`;
              },
            },
          },
        },
      },
    });
  }

  function veTheoThu() {
    veBieuDo(canvas('theo_thu'), {
      type: 'bar',
      data: {
        labels: duLieu.theo_thu.map(t => THU[t.thu]),
        datasets: [{data: duLieu.theo_thu.map(t => t.tb), backgroundColor: '#7fb3a1', borderRadius: 4}],
      },
      options: {
        scales: {x: {grid: {display: false}}, y: {beginAtZero: true}},
        plugins: {
          legend: {display: false},
          tooltip: {callbacks: {label: muc => ` ${dinhDangSo(muc.parsed.y, 2)} mỗi ngày`}},
        },
      },
    });
  }

  // Bảng sai số luôn ghi đủ hai chữ số thập phân (29,70 thay vì 29,7) để các cột so được với nhau.
  const soHaiChuSo = so =>
    so == null || Number.isNaN(so) ? '–' : Number(so).toLocaleString('vi-VN', {minimumFractionDigits: 2, maximumFractionDigits: 2});

  function veBang() {
    const bang = khung.querySelector('[data-bang-sai-so]');
    const dau = tao('thead');
    const hang = tao('tr');
    ['Mô hình', 'MAE xác thực', 'MAE kiểm thử', 'RMSE kiểm thử'].forEach((ten, i) => {
      const o = tao('th', i ? 'o-so' : '', ten);
      o.scope = 'col';
      hang.append(o);
    });
    dau.append(hang);
    const than = tao('tbody');
    const minXacThuc = Math.min(...duLieu.cac_mo_hinh.map(m => m.mae_xac_thuc));
    for (const m of duLieu.cac_mo_hinh) {
      const dong = tao('tr', m.duoc_chon ? 'dong-duoc-chon' : '');
      const ten = tao('th');
      ten.scope = 'row';
      ten.append(m.ten, tao('small', '', m.duoc_chon ? 'Được chọn' : m.loai));
      dong.append(ten);
      [m.mae_xac_thuc, m.mae_kiem_thu, m.rmse_kiem_thu].forEach((so, i) => {
        dong.append(tao('td', 'o-so' + (i === 0 && m.mae_xac_thuc === minXacThuc ? ' so-nho-nhat' : ''), soHaiChuSo(so)));
      });
      than.append(dong);
    }
    bang.replaceChildren(dau, than);
  }

  function veTomTat() {
    const chon = duLieu.cac_mo_hinh.find(m => m.duoc_chon);
    const tuongLai = duLieu.tuong_lai;
    const the = khung.querySelector('[data-du-bao-toi]');
    if (tuongLai) {
      const thap = Math.max(0, tuongLai.so_luong - tuongLai.mae);
      const cao = tuongLai.so_luong + tuongLai.mae;
      the.replaceChildren(
        tao('span', 'nhan-the-du-bao', 'Dự báo 7 ngày tới'),
        tao('strong', '', dinhDangSo(tuongLai.so_luong)),
        tao('span', 'khoang-du-bao', `Khoảng thường gặp ${dinhDangSo(thap)} – ${dinhDangSo(cao)}`),
        tao('small', '', `${congNgay(tuongLai.ngay_goc, 1)} – ${congNgay(tuongLai.ngay_goc, 7)} · ${chon.ten}`),
      );
    } else {
      the.replaceChildren(tao('span', 'nhan-the-du-bao', 'Chưa có dự báo kỳ tới.'));
    }

    const kt = duLieu.kiem_thu.thuc_te.filter(so => so != null);
    const trungBinh = kt.reduce((tong, so) => tong + so, 0) / (kt.length || 1);
    const xepXacThuc = [...duLieu.cac_mo_hinh].sort((a, b) => a.mae_xac_thuc - b.mae_xac_thuc);
    const thu2 = xepXacThuc[1];
    const tot = [...duLieu.cac_mo_hinh].sort((a, b) => a.mae_kiem_thu - b.mae_kiem_thu)[0];
    const muaVu = [...duLieu.mua_vu].sort((a, b) => b.tb - a.tb);
    const cao = muaVu[0];
    const thap = muaVu[muaVu.length - 1];
    const cacY = [
      `Chọn ${chon.ten} vì MAE ở đoạn xác thực thấp nhất (${dinhDangSo(chon.mae_xac_thuc, 2)}, kế tiếp là ${thu2.ten} ${dinhDangSo(thu2.mae_xac_thuc, 2)}).`,
      `Trên đoạn kiểm thử, dự báo lệch trung bình ±${dinhDangSo(chon.mae_kiem_thu)} so với tổng thực tế 7 ngày, khoảng ${dinhDangSo((chon.mae_kiem_thu / trungBinh) * 100, 0)}% mức bán trung bình ${dinhDangSo(trungBinh)}.`,
      tot.ma === chon.ma
        ? `${chon.ten} cũng là mô hình có sai số kiểm thử thấp nhất.`
        : `${tot.ten} có sai số kiểm thử thấp hơn (${dinhDangSo(tot.mae_kiem_thu, 2)}), nhưng không được chọn vì việc chọn dựa trên đoạn xác thực, trước khi xem đoạn kiểm thử.`,
      thap.tb > 0
        ? `Mùa vụ: bán nhiều nhất vào ${THANG[cao.thang - 1].replace('T', 'tháng ')} (${dinhDangSo(cao.tb, 2)}/ngày), ít nhất ${THANG[thap.thang - 1].replace('T', 'tháng ')} (${dinhDangSo(thap.tb, 2)}/ngày), chênh ${dinhDangSo(cao.tb / thap.tb, 1)} lần.`
        : '',
    ].filter(Boolean);
    khung.querySelector('[data-nhan-xet]').replaceChildren(...cacY.map(y => tao('li', '', y)));
  }

  function hienThi() {
    khung.querySelector('[data-ma-nhom]').textContent = 'NHÓM ' + duLieu.ma;
    khung.querySelector('[data-ten-nhom]').textContent = duLieu.ten || duLieu.ma;
    dangBat.clear();
    dangBat.add(duLieu.mo_hinh_chon);
    veTomTat();
    veCongTac();
    veKiemThu();
    veSaiSo();
    veMuaVu();
    veTheoThang();
    veTheoThu();
    veBang();
  }

  async function chonNhom(ma, {cuon = false} = {}) {
    cacThe.forEach(the => the.setAttribute('aria-selected', String(the.dataset.nhom === ma)));
    history.replaceState(null, '', '#nhom-' + ma);
    if (cuon) khung.scrollIntoView({behavior: 'smooth', block: 'start'});
    dangTai?.abort();
    if (boNho.has(ma)) {
      duLieu = boNho.get(ma);
      bao.textContent = '';
      hienThi();
      return;
    }
    const luot = new AbortController();
    dangTai = luot;
    bao.textContent = 'Đang tải dữ liệu nhóm…';
    khung.setAttribute('aria-busy', 'true');
    try {
      const phanHoi = await fetch(urlMau.replace('MA_ATC', encodeURIComponent(ma)), {
        signal: luot.signal,
        headers: {Accept: 'application/json'},
      });
      if (!phanHoi.ok) throw new Error(String(phanHoi.status));
      const ketQua = await phanHoi.json();
      boNho.set(ma, ketQua);
      if (luot !== dangTai) return;
      duLieu = ketQua;
      bao.textContent = '';
      hienThi();
    } catch (loi) {
      if (loi.name !== 'AbortError') bao.textContent = 'Không tải được dữ liệu nhóm. Hãy thử lại.';
    } finally {
      if (luot === dangTai) khung.removeAttribute('aria-busy');
    }
  }

  cacThe.forEach(the => the.addEventListener('click', () => chonNhom(the.dataset.nhom, {cuon: true})));
  const tuDuongDan = location.hash.startsWith('#nhom-') ? location.hash.slice(6) : null;
  const banDau = cacThe.find(the => the.dataset.nhom === tuDuongDan) || cacThe[0];
  if (banDau) chonNhom(banDau.dataset.nhom);

  // Tính thử kịch bản thiếu hàng ngay khi nhập, trước khi lưu.
  const form = document.querySelector('[data-form-kich-ban]');
  const xemTruoc = document.querySelector('[data-xem-truoc]');
  const duBaoTheoLuaChon = JSON.parse(document.getElementById('du-lieu-kich-ban')?.textContent || '{}');
  if (form && xemTruoc) {
    const o = ten => xemTruoc.querySelector(`[data-kq="${ten}"]`);
    const so = ten => {
      const gia = parseFloat(form.elements[ten]?.value);
      return Number.isFinite(gia) ? gia : null;
    };
    const tinh = () => {
      const duBao = duBaoTheoLuaChon[form.elements.du_bao?.value];
      const ton = so('so_luong_ton');
      const giu = so('so_luong_dang_giu');
      const duTru = so('so_luong_du_tru');
      const ketLuan = xemTruoc.querySelector('[data-ket-luan]');
      o('du_bao').textContent = duBao == null ? '–' : dinhDangSo(duBao);
      if (duBao == null || ton == null || giu == null || duTru == null) {
        ['kha_dung', 'sau_du_tru'].forEach(ten => (o(ten).textContent = '–'));
        ketLuan.textContent = 'Nhập đủ tồn, lượng giữ và mức dự trữ để xem kết luận.';
        xemTruoc.dataset.ketQua = '';
        return;
      }
      const khaDung = ton - giu;
      const sauDuTru = khaDung - duTru;
      const chenh = sauDuTru - duBao;
      o('kha_dung').textContent = dinhDangSo(khaDung);
      o('sau_du_tru').textContent = dinhDangSo(sauDuTru);
      const lon = Math.max(sauDuTru, duBao, 1);
      xemTruoc.querySelector('[data-thanh="co"]').style.width = `${(Math.max(sauDuTru, 0) / lon) * 100}%`;
      xemTruoc.querySelector('[data-thanh="can"]').style.width = `${(duBao / lon) * 100}%`;
      xemTruoc.dataset.ketQua = chenh < 0 ? 'thieu' : 'du';
      ketLuan.textContent =
        chenh < 0
          ? `Có nguy cơ thiếu khoảng ${dinhDangSo(-chenh)} trong 7 ngày tới. Người quản lý cân nhắc nhập thêm hoặc điều chuyển.`
          : `Đủ theo kịch bản, còn dư khoảng ${dinhDangSo(chenh)} sau khi giữ mức dự trữ.`;
    };
    form.addEventListener('input', tinh);
    form.addEventListener('change', tinh);
    tinh();
  }
})();
