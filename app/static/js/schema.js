// Schéma de brochage en 2D (SVG), vue de dessus.

import { positionsBroches } from "./geometrie.js";
import { type, h } from "./commun.js";

const CAR = 7.3;      // largeur d'un caractère à 12 px en police à chasse fixe
const MARGE_TEXTE = 150;

function couleurClaire(hex) {
  const n = parseInt(hex.slice(1), 16);
  const r = (n >> 16) / 255, g = ((n >> 8) & 255) / 255, b = (n & 255) / 255;
  return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.45;
}

export function creerSchema(conteneur, fiche, { surSurvol = () => {} } = {}) {
  const b = fiche.boitier;
  const positions = positionsBroches(fiche);
  const s = Math.min(40, Math.max(6, 380 / Math.max(b.largeur, b.longueur)));
  const cotes = new Set(positions.map((p) => p.cote));
  const longueurNom = Math.max(4, ...positions.map((p) => p.broche.nom.length));
  const margeTexte = Math.min(MARGE_TEXTE, longueurNom * CAR + 70);
  const marge = {
    gauche: cotes.has("gauche") ? margeTexte : 24,
    droite: cotes.has("droite") ? margeTexte : 24,
    haut: cotes.has("haut") ? margeTexte : 24,
    bas: cotes.has("bas") ? margeTexte : 24,
  };
  const W = b.largeur * s + marge.gauche + marge.droite;
  const H = b.longueur * s + marge.haut + marge.bas;
  const ox = marge.gauche, oy = marge.haut;
  const X = (x) => ox + x * s, Y = (y) => oy + y * s;
  const encre = couleurClaire(b.couleur) ? "#1b1d22" : "#e8ecf2";
  let svg = "";

  // Corps de l'appareil
  if (b.type === "dip") {
    const retrait = 0.635 * s;
    svg += `<rect x="${X(0) + retrait}" y="${Y(0)}" width="${b.largeur * s - 2 * retrait}" height="${b.longueur * s}" rx="4" fill="${b.couleur}" stroke="#3a4560"/>`;
    svg += `<path d="M ${X(b.largeur / 2) - 0.8 * s} ${Y(0)} a ${0.8 * s} ${0.8 * s} 0 0 0 ${1.6 * s} 0" fill="#07090d"/>`;
    svg += `<circle cx="${X(0) + retrait + 1.1 * s}" cy="${Y(1.2)}" r="${0.4 * s}" fill="#07090d"/>`;
    for (const p of positions) {
      const xBord = p.x < b.largeur / 2 ? X(0) + retrait : X(b.largeur) - retrait;
      svg += `<line x1="${xBord}" y1="${Y(p.y)}" x2="${X(p.x)}" y2="${Y(p.y)}" stroke="#c6cad2" stroke-width="${Math.max(3, 0.5 * s)}"/>`;
    }
    if (b.marquage) {
      svg += `<text x="${X(b.largeur / 2)}" y="${Y(b.longueur / 2)}" fill="#c9ced8" font-size="${Math.min(14, s * 0.9)}" text-anchor="middle" dominant-baseline="middle" ${b.longueur > b.largeur ? `transform="rotate(90 ${X(b.largeur / 2)} ${Y(b.longueur / 2)})"` : ""}>${h(b.marquage)}</text>`;
    }
  } else if (b.type === "to92") {
    const r = b.largeur * s / 2;
    svg += `<path d="M ${X(0)} ${Y(b.longueur)} L ${X(0)} ${Y(b.longueur) - Math.max(0, b.longueur * s - r)} A ${r} ${r} 0 0 1 ${X(b.largeur)} ${Y(b.longueur) - Math.max(0, b.longueur * s - r)} L ${X(b.largeur)} ${Y(b.longueur)} Z" fill="${b.couleur}" stroke="#3a4560"/>`;
    svg += `<text x="${X(b.largeur / 2)}" y="${Y(b.longueur) - 10}" fill="#8b93a1" font-size="11" text-anchor="middle">face plate</text>`;
  } else {
    svg += `<rect x="${X(0)}" y="${Y(0)}" width="${b.largeur * s}" height="${b.longueur * s}" rx="${Math.min(10, 1.2 * s)}" fill="${b.couleur}" stroke="#3a4560" stroke-width="1.5"/>`;
  }

  for (const c of fiche.composants || []) {
    const cx = X(c.x), cy = Y(c.y), l = c.largeur * s, L = c.longueur * s;
    const encreC = couleurClaire(c.couleur) ? "#24262c" : "#d5d8de";
    svg += `<g opacity=".92"><title>${h(c.nom)}</title>`;
    svg += c.forme === "cylindre"
      ? `<circle cx="${cx}" cy="${cy}" r="${l / 2}" fill="${c.couleur}" stroke="rgba(0,0,0,.4)"/>`
      : `<rect x="${cx - l / 2}" y="${cy - L / 2}" width="${l}" height="${L}" rx="2" fill="${c.couleur}" stroke="rgba(0,0,0,.4)"/>`;
    if (c.texte) {
      const vertical = L > l * 1.6;
      const place = vertical ? L : l;
      const taille = Math.min(12, (place * 0.85) / (c.texte.length * 0.62), (vertical ? l : L) * 0.4);
      if (taille >= 5) {
        svg += `<text x="${cx}" y="${cy}" fill="${encreC}" font-size="${taille}" font-weight="600" text-anchor="middle" dominant-baseline="middle" ${vertical ? `transform="rotate(90 ${cx} ${cy})"` : ""}>${h(c.texte)}</text>`;
      }
    }
    svg += "</g>";
  }

  // Broches et étiquettes
  for (const p of positions) {
    const t = type(p.broche.type);
    const px = X(p.x), py = Y(p.y);
    const r = Math.max(4, Math.min(p.rangee.pas * s * 0.32, 9));
    const largeurPastille = p.broche.nom.length * CAR + 16;
    let lx, ly, rotation = 0, ancre;
    const ecart = 16;
    if (p.cote === "gauche") { lx = X(0) - ecart; ly = py; ancre = "end"; }
    else if (p.cote === "droite") { lx = X(b.largeur) + ecart; ly = py; ancre = "start"; }
    else if (p.cote === "haut") { lx = px; ly = Y(0) - ecart; ancre = "start"; rotation = -90; }
    else { lx = px; ly = Y(b.longueur) + ecart; ancre = "end"; rotation = -90; }
    if (b.type === "dip") {
      if (p.cote === "gauche") lx = px - ecart;
      if (p.cote === "droite") lx = px + ecart;
    }
    const sens = ancre === "end" ? -1 : 1;
    const xPastille = ancre === "end" ? -largeurPastille : 0;
    const titre = `${p.broche.nom} — broche ${p.broche.n} (${t.libelle})${p.broche.desc ? ` : ${p.broche.desc}` : ""}`;
    svg += `<g class="broche" data-cle="${p.cle}"><title>${h(titre)}</title>`;
    svg += `<line x1="${px}" y1="${py}" x2="${lx}" y2="${ly}" stroke="${t.couleur}" stroke-opacity=".55" stroke-width="1.2"/>`;
    svg += `<g transform="translate(${lx} ${ly}) rotate(${rotation})">`;
    svg += `<rect class="pastille" x="${xPastille}" y="-10" width="${largeurPastille}" height="20" rx="10" fill="${t.couleur}" fill-opacity=".16" stroke="${t.couleur}"/>`;
    svg += `<text x="${xPastille + largeurPastille / 2}" y="1" fill="#e8ecf2" font-family="var(--mono)" font-size="12" font-weight="600" text-anchor="middle" dominant-baseline="middle">${h(p.broche.nom)}</text>`;
    svg += `<text x="${sens * (largeurPastille + 6)}" y="1" fill="#737e95" font-size="10.5" text-anchor="${ancre}" dominant-baseline="middle">${h(p.broche.n)}</text>`;
    svg += "</g>";
    svg += `<circle class="point" cx="${px}" cy="${py}" r="${r}" fill="${t.couleur}" stroke="#0b0f17" stroke-width="1.5"/>`;
    svg += "</g>";
  }

  conteneur.innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Brochage de ${h(fiche.nom)}" font-family="Inter, system-ui, sans-serif" style="--encre:${encre}">${svg}</svg>`;
  const groupes = new Map([...conteneur.querySelectorAll(".broche")].map((g) => [g.dataset.cle, g]));
  for (const [cle, g] of groupes) {
    g.addEventListener("mouseenter", () => { survoler(cle); surSurvol(cle); });
    g.addEventListener("mouseleave", () => { survoler(null); surSurvol(null); });
  }

  let cleSurvol = null;
  function survoler(cle) {
    if (cleSurvol && groupes.get(cleSurvol)) {
      const g = groupes.get(cleSurvol);
      g.querySelector(".point").setAttribute("stroke", "#0b0f17");
      g.querySelector(".pastille").setAttribute("fill-opacity", ".16");
    }
    cleSurvol = cle;
    const g = groupes.get(cle);
    if (g) {
      g.querySelector(".point").setAttribute("stroke", "#f2b84b");
      g.querySelector(".pastille").setAttribute("fill-opacity", ".45");
    }
  }
  return {
    survoler,
    surligner(cles) {
      for (const [cle, g] of groupes) g.classList.toggle("attenuee", Boolean(cles) && !cles.has(cle));
    },
  };
}
