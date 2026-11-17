// Outils partagés : appels à l'API, échappement HTML, notifications, types de broches.

export const TYPES = {
  alim:       { libelle: "Alimentation", couleur: "#ef6461" },
  masse:      { libelle: "Masse",        couleur: "#8b93a1" },
  gpio:       { libelle: "E/S numérique", couleur: "#4cc38a" },
  analogique: { libelle: "Analogique",   couleur: "#ff9548" },
  pwm:        { libelle: "PWM",          couleur: "#3dd6c6" },
  i2c:        { libelle: "I²C",          couleur: "#5eb1ef" },
  spi:        { libelle: "SPI",          couleur: "#9d7ff5" },
  uart:       { libelle: "UART",         couleur: "#ec6fc0" },
  controle:   { libelle: "Contrôle",     couleur: "#f2b84b" },
  reserve:    { libelle: "Réservée",     couleur: "#8a6d3b" },
  nc:         { libelle: "Non connectée", couleur: "#4a5162" },
  autre:      { libelle: "Autre",        couleur: "#c9ced8" },
};

export const type = (t) => TYPES[t] || TYPES.autre;

export function h(valeur) {
  return String(valeur ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

export async function api(chemin, { methode = "GET", corps, brut = false } = {}) {
  const options = { method: methode, headers: {} };
  if (corps instanceof FormData) {
    options.body = corps;
  } else if (corps !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(corps);
  }
  const r = await fetch(`/api${chemin}`, options);
  if (!r.ok) {
    let message = `Erreur ${r.status}`;
    try {
      const d = await r.json();
      if (typeof d.detail === "string") message = d.detail;
      else if (Array.isArray(d.detail)) message = d.detail.map((e) => `${e.loc?.slice(-1)[0]} : ${e.msg}`).join(" ; ");
    } catch { /* réponse non JSON */ }
    throw new Error(message);
  }
  if (r.status === 204) return null;
  return brut ? r.text() : r.json();
}

export function notifier(message, erreur = false) {
  const zone = document.getElementById("notifications");
  const el = document.createElement("div");
  el.className = `notification${erreur ? " erreur" : ""}`;
  el.textContent = message;
  zone.append(el);
  setTimeout(() => el.remove(), erreur ? 6000 : 3000);
}

export function debounce(fn, delai) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), delai); };
}

export function formaterDate(iso) {
  return new Date(iso).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}

export function slug(texte) {
  return texte.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 64);
}
