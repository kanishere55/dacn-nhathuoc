document.querySelectorAll("[data-formset]").forEach(form => {
  form.querySelector("[data-them-dong]")?.addEventListener("click", () => {
    const total = form.querySelector('[name$="-TOTAL_FORMS"]');
    if (Number(total.value) >= 50) return;
    const template = form.querySelector("[data-dong-rong]").innerHTML;
    form.querySelector("[data-cac-dong]").insertAdjacentHTML("beforeend", template.replaceAll("__prefix__", total.value));
    total.value = String(Number(total.value) + 1);
  });
});
