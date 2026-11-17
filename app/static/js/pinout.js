// 2D pinout diagram (SVG), seen from above.

import { pinPositions } from "./geometry.js";
import { pinType, escapeHtml as h, isLightColor } from "./common.js";

const CHAR_WIDTH = 7.3;   // width of one 12 px monospace character
const MAX_LABEL_MARGIN = 150;
const LABEL_GAP = 16;

export function createPinoutDiagram(container, sheet, { onHover = () => {} } = {}) {
  const pkg = sheet.package;
  const positions = pinPositions(sheet);
  const scale = Math.min(40, Math.max(6, 380 / Math.max(pkg.width, pkg.length))); // px per mm
  const sides = new Set(positions.map((p) => p.side));
  const longestName = Math.max(4, ...positions.map((p) => p.pin.name.length));
  const labelMargin = Math.min(MAX_LABEL_MARGIN, longestName * CHAR_WIDTH + 70);
  const margin = Object.fromEntries(["left", "right", "top", "bottom"].map((s) => [s, sides.has(s) ? labelMargin : 24]));
  const svgWidth = pkg.width * scale + margin.left + margin.right;
  const svgHeight = pkg.length * scale + margin.top + margin.bottom;
  const X = (x) => margin.left + x * scale;
  const Y = (y) => margin.top + y * scale;
  let svg = "";

  // Device body
  if (pkg.type === "dip") {
    const inset = 0.635 * scale;
    svg += `<rect x="${X(0) + inset}" y="${Y(0)}" width="${pkg.width * scale - 2 * inset}" height="${pkg.length * scale}" rx="4" fill="${pkg.color}" stroke="#3a4560"/>`;
    svg += `<path d="M ${X(pkg.width / 2) - 0.8 * scale} ${Y(0)} a ${0.8 * scale} ${0.8 * scale} 0 0 0 ${1.6 * scale} 0" fill="#07090d"/>`;
    svg += `<circle cx="${X(0) + inset + 1.1 * scale}" cy="${Y(1.2)}" r="${0.4 * scale}" fill="#07090d"/>`;
    for (const p of positions) {
      const edge = p.x < pkg.width / 2 ? X(0) + inset : X(pkg.width) - inset;
      svg += `<line x1="${edge}" y1="${Y(p.y)}" x2="${X(p.x)}" y2="${Y(p.y)}" stroke="#c6cad2" stroke-width="${Math.max(3, 0.5 * scale)}"/>`;
    }
    if (pkg.marking) {
      const cx = X(pkg.width / 2), cy = Y(pkg.length / 2);
      svg += `<text x="${cx}" y="${cy}" fill="#c9ced8" font-size="${Math.min(14, scale * 0.9)}" text-anchor="middle" dominant-baseline="middle" ${pkg.length > pkg.width ? `transform="rotate(90 ${cx} ${cy})"` : ""}>${h(pkg.marking)}</text>`;
    }
  } else if (pkg.type === "to92") {
    const r = pkg.width * scale / 2;
    const flatTop = Y(pkg.length) - Math.max(0, pkg.length * scale - r);
    svg += `<path d="M ${X(0)} ${Y(pkg.length)} L ${X(0)} ${flatTop} A ${r} ${r} 0 0 1 ${X(pkg.width)} ${flatTop} L ${X(pkg.width)} ${Y(pkg.length)} Z" fill="${pkg.color}" stroke="#3a4560"/>`;
    svg += `<text x="${X(pkg.width / 2)}" y="${Y(pkg.length) - 10}" fill="#8b93a1" font-size="11" text-anchor="middle">face plate</text>`;
  } else {
    svg += `<rect x="${X(0)}" y="${Y(0)}" width="${pkg.width * scale}" height="${pkg.length * scale}" rx="${Math.min(10, 1.2 * scale)}" fill="${pkg.color}" stroke="#3a4560" stroke-width="1.5"/>`;
  }

  for (const c of sheet.components || []) {
    const cx = X(c.x), cy = Y(c.y), w = c.width * scale, l = c.length * scale;
    svg += `<g opacity=".92"><title>${h(c.name)}</title>`;
    svg += c.shape === "cylinder"
      ? `<circle cx="${cx}" cy="${cy}" r="${w / 2}" fill="${c.color}" stroke="rgba(0,0,0,.4)"/>`
      : `<rect x="${cx - w / 2}" y="${cy - l / 2}" width="${w}" height="${l}" rx="2" fill="${c.color}" stroke="rgba(0,0,0,.4)"/>`;
    if (c.label) {
      const vertical = l > w * 1.6;
      const room = vertical ? l : w;
      const size = Math.min(12, (room * 0.85) / (c.label.length * 0.62), (vertical ? w : l) * 0.4);
      if (size >= 5) {
        svg += `<text x="${cx}" y="${cy}" fill="${isLightColor(c.color) ? "#24262c" : "#d5d8de"}" font-size="${size}" font-weight="600" text-anchor="middle" dominant-baseline="middle" ${vertical ? `transform="rotate(90 ${cx} ${cy})"` : ""}>${h(c.label)}</text>`;
      }
    }
    svg += "</g>";
  }

  // Real parts seen from above (sizes come from sheets/models/index.json).
  // On a DIP or TO-92 the part is the package itself, already drawn.
  if (pkg.type === "board" || pkg.type === "module") {
    for (const part of sheet.parts || []) {
      if (!part.size || part.side === "bottom") continue;
      const quarterTurn = Math.round(part.rotation / 90) % 2 !== 0;
      const turned = Math.abs(part.rotation % 90) > 1; // e.g. a QFP set at 45°
      const [sx, , sz] = part.size;
      const w = (quarterTurn ? sz : sx) * scale, l = (quarterTurn ? sx : sz) * scale;
      const cx = X(part.x), cy = Y(part.y);
      const transform = turned ? `transform="rotate(${-part.rotation} ${cx} ${cy})"` : "";
      svg += `<g opacity=".95"><title>${h(part.name)}</title>`;
      svg += `<rect x="${cx - w / 2}" y="${cy - l / 2}" width="${w}" height="${l}" rx="1.5" fill="${part.color}" stroke="rgba(0,0,0,.45)" ${transform}/>`;
      if (part.label) {
        const vertical = l > w * 1.4 && !turned;
        const size = Math.min(12, ((vertical ? l : w) * 0.85) / (part.label.length * 0.62), (vertical ? w : l) * 0.35);
        if (size >= 5) {
          svg += `<text x="${cx}" y="${cy}" fill="${isLightColor(part.color) ? "#4a4e57" : "#d5d8de"}" font-size="${size}" font-weight="600" text-anchor="middle" dominant-baseline="middle" ${vertical ? `transform="rotate(90 ${cx} ${cy})"` : ""}>${h(part.label)}</text>`;
        }
      }
      svg += "</g>";
    }
  }

  // Pins and their labels
  for (const p of positions) {
    const type = pinType(p.pin.type);
    const px = X(p.x), py = Y(p.y);
    const radius = Math.max(4, Math.min(p.row.pitch * scale * 0.32, 9));
    const pillWidth = p.pin.name.length * CHAR_WIDTH + 16;
    let lx, ly, anchor, rotation = 0;
    if (p.side === "left") { lx = (pkg.type === "dip" ? px : X(0)) - LABEL_GAP; ly = py; anchor = "end"; }
    else if (p.side === "right") { lx = (pkg.type === "dip" ? px : X(pkg.width)) + LABEL_GAP; ly = py; anchor = "start"; }
    else if (p.side === "top") { lx = px; ly = Y(0) - LABEL_GAP; anchor = "start"; rotation = -90; }
    else { lx = px; ly = Y(pkg.length) + LABEL_GAP; anchor = "end"; rotation = -90; }
    const direction = anchor === "end" ? -1 : 1;
    const pillX = anchor === "end" ? -pillWidth : 0;
    const title = `${p.pin.name} — broche ${p.pin.n} (${type.label})${p.pin.description ? ` : ${p.pin.description}` : ""}`;
    svg += `<g class="pin" data-key="${p.key}"><title>${h(title)}</title>`;
    svg += `<line x1="${px}" y1="${py}" x2="${lx}" y2="${ly}" stroke="${type.color}" stroke-opacity=".55" stroke-width="1.2"/>`;
    svg += `<g transform="translate(${lx} ${ly}) rotate(${rotation})">`;
    svg += `<rect class="pill" x="${pillX}" y="-10" width="${pillWidth}" height="20" rx="10" fill="${type.color}" fill-opacity=".16" stroke="${type.color}"/>`;
    svg += `<text x="${pillX + pillWidth / 2}" y="1" fill="#e8ecf2" font-family="var(--mono)" font-size="12" font-weight="600" text-anchor="middle" dominant-baseline="middle">${h(p.pin.name)}</text>`;
    svg += `<text x="${direction * (pillWidth + 6)}" y="1" fill="#737e95" font-size="10.5" text-anchor="${anchor}" dominant-baseline="middle">${h(p.pin.n)}</text>`;
    svg += "</g>";
    svg += `<circle class="pin-dot" cx="${px}" cy="${py}" r="${radius}" fill="${type.color}" stroke="#0b0f17" stroke-width="1.5"/>`;
    svg += "</g>";
  }

  container.innerHTML = `<svg viewBox="0 0 ${svgWidth} ${svgHeight}" width="${svgWidth}" height="${svgHeight}" role="img" aria-label="Brochage de ${h(sheet.name)}" font-family="Inter, system-ui, sans-serif">${svg}</svg>`;
  const groups = new Map([...container.querySelectorAll(".pin")].map((g) => [g.dataset.key, g]));
  for (const [key, g] of groups) {
    g.addEventListener("mouseenter", () => { hover(key); onHover(key); });
    g.addEventListener("mouseleave", () => { hover(null); onHover(null); });
  }

  let hoveredKey = null;
  function hover(key) {
    const previous = groups.get(hoveredKey);
    if (previous) {
      previous.querySelector(".pin-dot").setAttribute("stroke", "#0b0f17");
      previous.querySelector(".pill").setAttribute("fill-opacity", ".16");
    }
    hoveredKey = key;
    const current = groups.get(key);
    if (current) {
      current.querySelector(".pin-dot").setAttribute("stroke", "#f2b84b");
      current.querySelector(".pill").setAttribute("fill-opacity", ".45");
    }
  }
  return {
    hover,
    highlight(keys) {
      for (const [key, g] of groups) g.classList.toggle("dimmed", Boolean(keys) && !keys.has(key));
    },
  };
}
