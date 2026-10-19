// 웹 푸시 서비스 워커 (FR-20). 서버가 보낸 알림을 띄우고, 누르면 해당 화면을 연다.
// 푸시 내용은 화면 알림과 같은 글(과목 코드·처리 내용)과 주소뿐이다.
self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = { body: event.data ? event.data.text() : "" };
  }
  event.waitUntil(
    self.registration.showNotification(data.title || "CreditBridge", {
      body: data.body || "",
      icon: "/static/img/apple-touch-icon.png",
      badge: "/static/img/favicon-64.png",
      data: { link: data.link || "/notifications" },
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const link = new URL(event.notification.data.link || "/notifications", self.location.origin).href;
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
      for (const w of windows) {
        if (w.url === link && "focus" in w) return w.focus();
      }
      return self.clients.openWindow(link);
    })
  );
});
