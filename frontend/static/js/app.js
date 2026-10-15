// UTC로 저장된 시각을 보는 사람의 현지 시각으로 표시한다.
function localizeTimes(root) {
  root.querySelectorAll("time[datetime]").forEach((el) => {
    const d = new Date(el.getAttribute("datetime"));
    if (isNaN(d)) return;
    const withTime = el.dataset.format !== "date";
    el.textContent = d.toLocaleString("ko-KR", withTime
      ? { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }
      : { year: "numeric", month: "short", day: "numeric" });
  });
}
document.addEventListener("DOMContentLoaded", () => localizeTimes(document));
document.addEventListener("htmx:afterSwap", (e) => localizeTimes(e.target));

// 근거 구절을 누르면 접혀 있는 원문을 펼치고 해당 위치로 이동한다 (FR-25).
document.addEventListener("click", (e) => {
  const link = e.target.closest("a[data-jump]");
  if (!link) return;
  const panel = document.getElementById(link.dataset.jump);
  const anchor = document.getElementById(link.getAttribute("href").slice(1));
  if (!panel || !anchor) return;
  e.preventDefault();
  panel.open = true;
  document.querySelectorAll(".source-text mark.is-target").forEach((m) => m.classList.remove("is-target"));
  const mark = anchor.closest("mark") || anchor.nextElementSibling;
  if (mark && mark.tagName === "MARK") mark.classList.add("is-target");
  anchor.scrollIntoView({ behavior: "smooth", block: "center" });
  history.replaceState(null, "", link.getAttribute("href"));
});

// 표에서 행을 고르면 일괄 처리 바를 띄우고 선택 수를 보여준다.
document.querySelectorAll("[data-select-form]").forEach((form) => {
  const boxes = () => [...form.querySelectorAll('input[name="evaluation_ids"]:not(:disabled)')];
  const bar = form.querySelector("[data-select-bar]");
  const count = form.querySelector("[data-select-count]");
  const all = form.querySelector("[data-select-all]");
  const update = () => {
    const n = boxes().filter((b) => b.checked).length;
    if (count) count.textContent = n;
    if (bar) bar.hidden = n === 0;
    if (all) all.checked = n > 0 && n === boxes().length;
  };
  form.addEventListener("change", (e) => {
    if (e.target === all) boxes().forEach((b) => { b.checked = all.checked; });
    update();
  });
  update();
});

// 판정 확정 전에 사유 선택 창을 연다: 반려, AI 추천과 다른 수정, 과거 판정과 다른 결과일 때 (FR-09, FR-11).
document.querySelectorAll("[data-decision-form]").forEach((form) => {
  const dialog = form.querySelector("#reason-dialog");
  if (!dialog || typeof dialog.showModal !== "function") return;
  const past = JSON.parse(form.dataset.past || "[]");
  const value = (name) => (form.querySelector(`[name="${name}"]:checked`) || form.elements[name] || {}).value || "";
  const plan = () => {
    const action = value("action");
    const ai = form.dataset.ai;
    let final = ai;
    if (action === "reject") final = "none";
    else if (action === "modify") final = form.elements.result.value || ai;
    const target = form.elements.target_course_id.value;
    const differs = final !== ai || (final === "direct" && target !== form.dataset.candidate);
    const conflicts = past.filter((r) => r !== final).length;
    return { action, reasons: action === "reject" || (action === "modify" && differs), conflicts };
  };
  const open = (p) => {
    const title = p.action === "reject" ? "학점 불인정 사유 선택 및 소명" : p.reasons ? "판정 변경 사유 선택 및 소명" : "과거 판정과 다른 결과 확인";
    dialog.querySelector("[data-reason-title]").textContent = title;
    dialog.querySelector("[data-reason-submit]").textContent =
      p.action === "reject" ? "불인정 사유 저장 및 판정 확정" : p.reasons ? "사유 저장 및 판정 확정" : "확인하고 판정 확정";
    dialog.querySelectorAll("[data-reasons]").forEach((el) => { el.hidden = !p.reasons; });
    const warn = dialog.querySelector("[data-conflict-warning]");
    if (p.conflicts) {
      warn.hidden = false;
      dialog.querySelector("[data-conflict-text]").textContent =
        `같은 강의계획서로 내린 과거 판정 ${p.conflicts}건과 결과가 달라요. 이력을 확인한 뒤 확정해 주세요.`;
    }
    if (!dialog.open) dialog.showModal();
  };
  form.addEventListener("submit", (e) => {
    if (e.submitter && dialog.contains(e.submitter)) return;
    const p = plan();
    if (p.reasons || p.conflicts) {
      e.preventDefault();
      open(p);
    }
  });
  dialog.querySelectorAll("[data-dialog-close]").forEach((el) => el.addEventListener("click", () => dialog.close()));
  const memo = dialog.querySelector("[data-memo]");
  const count = dialog.querySelector("[data-memo-count]");
  if (memo && count) memo.addEventListener("input", () => { count.textContent = memo.value.length; });
  if (dialog.hasAttribute("data-autoopen")) open(plan());
});

// 글자 수 표시: textarea[data-count]가 가리키는 요소에 "현재 / 최대"를 보여준다.
document.querySelectorAll("textarea[data-count]").forEach((el) => {
  const out = document.getElementById(el.dataset.count);
  if (!out) return;
  const update = () => { out.textContent = `${el.value.length} / ${el.maxLength}`; };
  el.addEventListener("input", update);
  update();
});

// 여러 파일 선택 칸의 개수 제한: 넘치면 제출 전에 알려 준다 (서버도 다시 검사한다).
document.querySelectorAll("input[type=file][data-max-files]").forEach((el) => {
  el.addEventListener("change", () => {
    const max = Number(el.dataset.maxFiles);
    el.setCustomValidity(el.files.length > max ? `파일은 ${max}개까지 올릴 수 있어요.` : "");
    el.reportValidity();
  });
});
