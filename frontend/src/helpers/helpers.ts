const DEVICE_COLORS = [
  "#22d3ee", "#a78bfa", "#fb923c", "#34d399",
  "#f472b6", "#facc15", "#60a5fa", "#f87171",
];
export function getDeviceColor(i: number) { return DEVICE_COLORS[i % DEVICE_COLORS.length]; }

// ─── URL helpers ──────────────────────────────────────────────────────────────
export function getUrlDevices(): string[] {
  const params = new URLSearchParams(window.location.search);
  const raw = params.get("device");
  if (!raw) return [];
  return raw.split(",").map((s) => s.trim()).filter(Boolean);
}

export function setUrlDevices(devices: string[]) {
  const params = new URLSearchParams(window.location.search);
  if (devices.length === 0) {
    params.delete("device");
  } else {
    params.set("device", devices.join(","));
  }
  const newUrl = `${window.location.pathname}${params.toString() ? "?" + params.toString() : ""}`;
  window.history.replaceState(null, "", newUrl);
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
export function formatTime(iso: string) {
  // Append Z if no timezone info to treat as UTC and avoid local-shift
  const s = /[Zz]|[+-]\d{2}:\d{2}$/.test(iso) ? iso : iso + "Z";
  return new Date(s).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
export function formatDateTime(iso: string) {
  const s = /[Zz]|[+-]\d{2}:\d{2}$/.test(iso) ? iso : iso + "Z";
  return new Date(s).toLocaleString("ru-RU", {
    day: "2-digit", month: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}