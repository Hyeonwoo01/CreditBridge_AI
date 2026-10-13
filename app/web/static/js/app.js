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
