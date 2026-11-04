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

// ─── Time helpers ─────────────────────────────────────────────────────────────
// Append Z if there is no timezone info, so the backend's naive timestamps are
// treated as UTC and not shifted by the browser's local zone.
function withTz(iso: string) {
  return /[Zz]|[+-]\d{2}:\d{2}$/.test(iso) ? iso : iso + "Z";
}

// ISO string -> epoch ms (UTC-safe)
export function parseTs(iso: string) {
  return new Date(withTz(iso)).getTime();
}

// Bucket size for the chart X axis. Points of different devices that fall into
// the same bucket share one X position. Lower it if agents report more often
// than once per minute.
export const BUCKET_MS = 60_000;

export function toBucket(iso: string) {
  return Math.floor(parseTs(iso) / BUCKET_MS) * BUCKET_MS;
}

// ─── Formatting ───────────────────────────────────────────────────────────────
export function formatTime(iso: string) {
  return new Date(withTz(iso)).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
export function formatDateTime(iso: string) {
  return new Date(withTz(iso)).toLocaleString("ru-RU", {
    day: "2-digit", month: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}