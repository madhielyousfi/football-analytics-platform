/* Football Intelligence service worker: Web Push goal alerts. */

self.addEventListener("push", (event) => {
  let data = { title: "Football Intelligence", body: "", url: "/" };
  try {
    if (event.data) data = { ...data, ...event.data.json() };
  } catch {
    if (event.data) data.body = event.data.text();
  }
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body || "",
      icon: "/icon.png",
      badge: "/icon.png",
      data: { url: data.url || "/" },
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
      for (const w of windows) {
        if (w.url.includes(new URL(url, self.location.origin).pathname) && "focus" in w) return w.focus();
      }
      return self.clients.openWindow(url);
    }),
  );
});
