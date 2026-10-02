"use client";

import { useCallback, useEffect, useState } from "react";

const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
const STATIC_MODE = process.env.NEXT_PUBLIC_DATA_MODE === "static";
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function bufToB64url(buf: ArrayBuffer | null): string {
  if (!buf) return "";
  const bytes = new Uint8Array(buf);
  let bin = "";
  bytes.forEach((b) => { bin += String.fromCharCode(b); });
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function b64urlToU8(base64: string): Uint8Array {
  const padded = base64.replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(padded + "=".repeat((4 - (padded.length % 4)) % 4));
  return Uint8Array.from(Array.from(bin).map((c) => c.charCodeAt(0)));
}

type State = "unsupported" | "demo" | "off" | "on" | "busy" | "denied" | "error";

export function PushButton() {
  const [state, setState] = useState<State>("off");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
      setState("unsupported");
    } else if (STATIC_MODE) {
      setState("demo");
    }
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready || state === "unsupported" || state === "demo") return;
    navigator.serviceWorker.register(`${BASE_PATH}/sw.js`).then(async (reg) => {
      const sub = await reg.pushManager.getSubscription();
      setState(sub ? "on" : Notification.permission === "denied" ? "denied" : "off");
    }).catch(() => setState("error"));
  }, [ready, state]);

  const enable = useCallback(async () => {
    setState("busy");
    try {
      const perm = await Notification.requestPermission();
      if (perm !== "granted") {
        setState("denied");
        return;
      }
      const keyRes = await fetch(`${API}/api/push/vapid-key`);
      if (!keyRes.ok) throw new Error("push not configured");
      const { publicKey } = await keyRes.json();
      const reg = await navigator.serviceWorker.register(`${BASE_PATH}/sw.js`);
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: b64urlToU8(publicKey) as BufferSource,
      });
      const body = {
        endpoint: sub.endpoint,
        p256dh: bufToB64url(sub.getKey("p256dh")),
        auth: bufToB64url(sub.getKey("auth")),
        label: "web",
      };
      const res = await fetch(`${API}/api/push/subscribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        await sub.unsubscribe();
        throw new Error("subscribe failed");
      }
      setState("on");
    } catch {
      setState("error");
    }
  }, []);

  const disable = useCallback(async () => {
    setState("busy");
    try {
      const reg = await navigator.serviceWorker.getRegistration(`${BASE_PATH}/sw.js`);
      const sub = await reg?.pushManager.getSubscription();
      const endpoint = sub?.endpoint;
      if (sub) await sub.unsubscribe();
      if (endpoint) {
        await fetch(`${API}/api/push/unsubscribe`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ endpoint }),
        });
      }
      setState("off");
    } catch {
      setState("error");
    }
  }, []);

  if (!ready || state === "unsupported") return null;
  if (state === "demo") {
    return <span className="badge border-white/10 bg-white/5 text-muted" title="Goal alerts need the live API, not the static demo">🔕 Demo</span>;
  }
  if (state === "on") {
    return <button onClick={disable} className="badge border-pitch/30 bg-pitch/10 text-green-300 hover:bg-pitch/20">🔔 Alerts on</button>;
  }
  const label = state === "denied" ? "🔕 Blocked" : state === "error" ? "⚠️ Retry alerts" : state === "busy" ? "…" : "🔕 Get goal alerts";
  const disabled = state === "busy" || state === "denied";
  return <button onClick={enable} disabled={disabled} className="badge border-white/10 bg-white/5 text-muted hover:text-white disabled:opacity-60">{label}</button>;
}
