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
