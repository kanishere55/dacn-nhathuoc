(() => {
  const nhom = document.querySelector('[data-don-thuoc-tai-quay]');
  if (!nhom) return;
  const form = nhom.closest('form');
  const thuocKeDon = new Set(JSON.parse(document.getElementById('id-thuoc-ke-don').textContent).map(String));
  const capNhat = () => {
    const canDon = Array.from(form.querySelectorAll('[name$="-thuoc"]')).some((o) =>
      thuocKeDon.has(o.value) && !o.closest('.dong-phieu')?.querySelector('[name$="-DELETE"]:checked'));
    nhom.open = canDon || Boolean(nhom.querySelector('.errorlist'));
  };
  form.addEventListener('change', (e) => {
    if (e.target.matches('[name$="-thuoc"], [name$="-DELETE"]')) capNhat();
  });
  capNhat();
})();
