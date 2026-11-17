// Shared helpers: API calls, HTML escaping, notifications, pin types.
// Labels shown to the user are in French.

export const PIN_TYPES = {
  power:    { label: "Alimentation",  color: "#ef6461" },
  ground:   { label: "Masse",         color: "#8b93a1" },
  gpio:     { label: "E/S numérique", color: "#4cc38a" },
  analog:   { label: "Analogique",    color: "#ff9548" },
  pwm:      { label: "PWM",           color: "#3dd6c6" },
  i2c:      { label: "I²C",           color: "#5eb1ef" },
  spi:      { label: "SPI",           color: "#9d7ff5" },
  uart:     { label: "UART",          color: "#ec6fc0" },
  control:  { label: "Contrôle",      color: "#f2b84b" },
  reserved: { label: "Réservée",      color: "#8a6d3b" },
  nc:       { label: "Non connectée", color: "#4a5162" },
  other:    { label: "Autre",         color: "#c9ced8" },
};

export const pinType = (type) => PIN_TYPES[type] || PIN_TYPES.other;

// Sheets are requested with a GitHub issue form (.github/ISSUE_TEMPLATE/fiche.yml).
export const SHEET_REQUEST_URL = "https://github.com/astraeos-dev/Promethee/issues/new?template=fiche.yml";

export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

// Paths are relative so that the UI also works under the Home Assistant Ingress prefix.
export async function api(path, { method = "GET", body, raw = false } = {}) {
  const options = { method, headers: {} };
  if (body instanceof FormData) {
    options.body = body;
  } else if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch(`api${path}`, options);
  if (!response.ok) {
    let message = `Erreur ${response.status}`;
    try {
      const data = await response.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail)) message = data.detail.map((e) => `${e.loc?.slice(-1)[0]} : ${e.msg}`).join(" ; ");
    } catch { /* not a JSON response */ }
    throw new Error(message);
  }
  if (response.status === 204) return null;
  return raw ? response.text() : response.json();
}

export function notify(message, isError = false) {
  const area = document.getElementById("notifications");
  const el = document.createElement("div");
  el.className = `notification${isError ? " error" : ""}`;
  el.textContent = message;
  area.append(el);
  setTimeout(() => el.remove(), isError ? 6000 : 3000);
}

export function debounce(fn, delay) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); };
}

export function formatDate(iso) {
  return new Date(iso).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}

export function isLightColor(hex) {
  const n = parseInt(hex.slice(1), 16);
  const r = (n >> 16) / 255, g = ((n >> 8) & 255) / 255, b = (n & 255) / 255;
  return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.45;
}
