// Promethee UI: router and views (inventory, sheet list, sheet page).
// Sheets are read-only: new sheets and corrections are requested as GitHub issues.
// Code is in English; every text shown to the user is in French.

import { api, escapeHtml as h, notify, debounce, formatDate, pinType } from "./common.js";
import { pinPositions } from "./geometry.js";
import { createPinoutDiagram } from "./pinout.js";

const view = document.getElementById("view");
let cleanups = [];

function cleanup() {
  cleanups.forEach((fn) => { try { fn(); } catch { /* already disposed */ } });
  cleanups = [];
}

// Three.js is only loaded when a 3D view is shown.
async function mountViewer(container, sheet, options) {
  container.innerHTML = '<div class="scene-loading">Chargement de la vue 3D…</div>';
  const { createViewer3D } = await import("./viewer3d.js");
  const viewer = createViewer3D(container, sheet, options);
  cleanups.push(() => viewer.dispose());
  return viewer;
}

const fetchSheets = async () => (await api("/sheets")).sheets;

// ---------- Router ----------

const routes = [
  [/^#\/stock$/, renderInventory],
  [/^#\/sheets$/, renderSheetList],
  [/^#\/sheet\/([a-z0-9-]+)$/, renderSheet],
  [/^#\/requests$/, renderRequests],
];

async function route() {
  const hash = location.hash || "#/stock";
  cleanup();
  for (const link of document.querySelectorAll("[data-nav]")) {
    const isSheetPage = link.dataset.nav === "sheets" && /^#\/(sheet\/|requests)/.test(hash);
    link.classList.toggle("active", hash.startsWith(`#/${link.dataset.nav}`) || isSheetPage);
  }
  for (const [pattern, render] of routes) {
    const match = hash.match(pattern);
    if (!match) continue;
    view.innerHTML = "";
    try {
      await render(...match.slice(1));
    } catch (err) {
      view.innerHTML = `<div class="empty"><b>Impossible d'afficher cette page</b>${h(err.message)}</div>`;
    }
    window.scrollTo(0, 0);
    return;
  }
  location.hash = "#/stock";
}

window.addEventListener("hashchange", route);
route();

// ---------- Inventory ----------

async function renderInventory() {
  const filters = { q: "", category: "", lowStock: false };
  view.innerHTML = `
    <div class="page-title">
      <div><div class="eyebrow">Inventaire</div><h1>Stock</h1><p>Composants, cartes et modules, avec leur emplacement.</p></div>
    </div>
    <div class="stats" id="stats"></div>
    <div class="toolbar">
      <input class="search" type="search" placeholder="Rechercher : nom, valeur, emplacement…" aria-label="Rechercher" id="search">
      <select id="category-filter" aria-label="Catégorie"><option value="">Toutes les catégories</option></select>
      <label class="checkbox"><input type="checkbox" id="low-stock"> À réapprovisionner</label>
      <span class="spacer"></span>
      <button class="btn" id="import" type="button">Importer CSV</button>
      <a class="btn" href="api/export.csv" download>Exporter CSV</a>
      <button class="btn btn-primary" id="add" type="button">+ Ajouter</button>
      <input type="file" id="csv-file" accept=".csv,text/csv" hidden>
    </div>
    <div class="card" id="item-list"></div>`;

  const list = view.querySelector("#item-list");
  const categorySelect = view.querySelector("#category-filter");
  const sheets = await fetchSheets();

  async function loadStats() {
    const s = await api("/summary");
    view.querySelector("#stats").innerHTML = `
      <div class="stat"><b>${s.items}</b><span>références</span></div>
      <div class="stat"><b>${s.parts}</b><span>pièces en stock</span></div>
      <div class="stat ${s.low_stock ? "alert" : ""}"><b>${s.low_stock}</b><span>à réapprovisionner</span></div>
      <div class="stat"><b>${s.sheets}</b><span>fiches techniques</span></div>`;
  }

  async function loadCategories() {
    const { items } = await api("/categories");
    const selected = categorySelect.value;
    categorySelect.innerHTML = '<option value="">Toutes les catégories</option>' +
      items.map((c) => `<option ${c === selected ? "selected" : ""}>${h(c)}</option>`).join("");
  }

  async function loadItems() {
    const params = new URLSearchParams({ q: filters.q, category: filters.category, low_stock: filters.lowStock });
    const items = await api(`/items?${params}`);
    if (!items.length) {
      const filtered = filters.q || filters.category || filters.lowStock;
      list.innerHTML = `<div class="empty"><b>${filtered ? "Aucun article ne correspond" : "Le stock est vide"}</b>
        ${filtered ? "Modifiez la recherche ou les filtres." : "Ajoutez un premier article, ou importez un fichier CSV."}</div>`;
      return;
    }
    const sheetNames = new Map(sheets.map((s) => [s.id, s.name]));
    list.innerHTML = `<table class="stock-table">
      <thead><tr><th>Article</th><th>Catégorie</th><th>Emplacement</th><th class="num">Quantité</th><th class="num">Seuil</th><th>Fiche</th><th></th></tr></thead>
      <tbody>${items.map((item) => itemRow(item, sheetNames)).join("")}</tbody></table>`;
  }

  async function reloadAll() {
    await Promise.all([loadItems(), loadStats(), loadCategories()]);
  }
  await reloadAll();

  view.querySelector("#search").addEventListener("input", debounce((e) => { filters.q = e.target.value; loadItems(); }, 200));
  categorySelect.addEventListener("change", (e) => { filters.category = e.target.value; loadItems(); });
  view.querySelector("#low-stock").addEventListener("change", (e) => { filters.lowStock = e.target.checked; loadItems(); });
  view.querySelector("#add").addEventListener("click", () => openItemDialog(null, sheets, reloadAll));

  const csvInput = view.querySelector("#csv-file");
  view.querySelector("#import").addEventListener("click", () => csvInput.click());
  csvInput.addEventListener("change", async () => {
    if (!csvInput.files[0]) return;
    const form = new FormData();
    form.append("file", csvInput.files[0]);
    try {
      const result = await api("/import", { method: "POST", body: form });
      notify(`Import terminé : ${result.created} créé(s), ${result.updated} mis à jour.`);
      await reloadAll();
    } catch (err) { notify(err.message, true); }
    csvInput.value = "";
  });

  list.addEventListener("click", async (e) => {
    const row = e.target.closest("tr[data-id]");
    const button = e.target.closest("button");
    if (!row || !button) return;
    const id = Number(row.dataset.id);
    try {
      if (button.dataset.delta) {
        button.disabled = true;
        const delta = Number(button.dataset.delta);
        await api(`/items/${id}/movements`, { method: "POST", body: { delta, reason: delta > 0 ? "Ajout" : "Sortie" } });
        await Promise.all([loadItems(), loadStats()]);
      } else if (button.dataset.action === "edit") {
        openItemDialog(await api(`/items/${id}`), sheets, reloadAll);
      } else if (button.dataset.action === "history") {
        openHistoryDialog(await api(`/items/${id}`));
      }
    } catch (err) { notify(err.message, true); button.disabled = false; }
  });
}

function itemRow(item, sheetNames) {
  const low = item.quantity <= item.threshold;
  const details = [item.value, item.package].filter(Boolean).join(" · ");
  let sheetCell = "";
  if (item.sheet) {
    sheetCell = sheetNames.has(item.sheet)
      ? `<a href="#/sheet/${h(item.sheet)}">${h(sheetNames.get(item.sheet))}</a>`
      : `<span class="badge badge-danger" title="Fiche introuvable">${h(item.sheet)}</span>`;
  }
  return `<tr data-id="${item.id}">
    <td class="col-name"><b>${h(item.name)}</b>${details ? `<div class="muted">${h(details)}</div>` : ""}</td>
    <td>${item.category ? `<span class="badge">${h(item.category)}</span>` : ""}</td>
    <td>${h(item.location) || '<span class="muted">—</span>'}</td>
    <td class="num"><span class="qty ${low ? "low" : ""}">
      <button class="btn btn-icon" data-delta="-1" type="button" aria-label="Retirer une pièce" ${item.quantity ? "" : "disabled"}>−</button>
      <b>${item.quantity}</b>
      <button class="btn btn-icon" data-delta="1" type="button" aria-label="Ajouter une pièce">+</button></span></td>
    <td class="num col-threshold">${item.threshold}</td>
    <td class="col-sheet">${sheetCell}</td>
    <td class="actions col-actions">
      <button class="btn" data-action="history" type="button">Historique</button>
      <button class="btn" data-action="edit" type="button">Modifier</button></td>
  </tr>`;
}

function openDialog(html) {
  const dialog = document.createElement("dialog");
  dialog.innerHTML = html;
  document.body.append(dialog);
  dialog.addEventListener("close", () => dialog.remove());
  cleanups.push(() => dialog.close());
  dialog.showModal();
  return dialog;
}

function openItemDialog(item, sheets, onSaved, defaults = {}) {
  const data = item || { quantity: 0, threshold: 0, ...defaults };
  const field = (name, label, attrs = "", cls = "") =>
    `<label class="field ${cls}"><span>${label}</span><input name="${name}" value="${h(data[name] ?? "")}" ${attrs}></label>`;
  const dialog = openDialog(`<form method="dialog">
    <h2>${item ? "Modifier l'article" : "Nouvel article"}</h2>
    <div class="form-grid">
      ${field("name", "Nom", 'required autofocus placeholder="Résistance, ESP32…"', "wide")}
      ${field("category", "Catégorie", 'list="category-options" placeholder="Résistance, Capteur…"')}
      ${field("value", "Valeur", 'placeholder="10 kΩ, 100 nF…"')}
      ${field("package", "Boîtier", 'placeholder="0805, DIP-8, TO-92…"')}
      ${field("location", "Emplacement", 'placeholder="Tiroir A3"')}
      ${field("quantity", "Quantité", 'type="number" min="0" step="1" required')}
      ${field("threshold", "Seuil d'alerte", 'type="number" min="0" step="1"')}
      <label class="field"><span>Fiche liée</span><select name="sheet"><option value="">Aucune</option>
        ${sheets.map((s) => `<option value="${h(s.id)}" ${s.id === data.sheet ? "selected" : ""}>${h(s.name)}</option>`).join("")}</select></label>
      ${field("supplier", "Fournisseur")}
      ${field("price", "Prix unitaire (€)", 'type="number" min="0" step="0.001"')}
      <label class="field wide"><span>Notes</span><textarea name="notes" rows="3">${h(data.notes ?? "")}</textarea></label>
    </div>
    <datalist id="category-options"></datalist>
    <div class="dialog-footer">
      ${item ? '<button class="btn btn-danger" type="button" data-action="delete">Supprimer</button>' : ""}
      <span class="spacer"></span>
      <button class="btn" value="cancel" formnovalidate>Annuler</button>
      <button class="btn btn-primary" value="save" type="submit">Enregistrer</button>
    </div></form>`);

  api("/categories").then((c) => {
    const all = [...new Set([...c.items, ...c.sheets])].sort((a, b) => a.localeCompare(b, "fr"));
    dialog.querySelector("#category-options").innerHTML = all.map((x) => `<option value="${h(x)}">`).join("");
  });

  const form = dialog.querySelector("form");
  form.addEventListener("submit", async (e) => {
    if (e.submitter?.value !== "save") return;
    e.preventDefault();
    const values = Object.fromEntries(new FormData(form));
    values.quantity = Number(values.quantity || 0);
    values.threshold = Number(values.threshold || 0);
    values.price = values.price === "" ? null : Number(values.price);
    try {
      if (item) await api(`/items/${item.id}`, { method: "PUT", body: values });
      else await api("/items", { method: "POST", body: values });
      notify(item ? "Article mis à jour." : "Article ajouté.");
      dialog.close();
      await onSaved();
    } catch (err) { notify(err.message, true); }
  });

  dialog.querySelector("[data-action=delete]")?.addEventListener("click", async () => {
    if (!confirm(`Supprimer « ${item.name} » et son historique ?`)) return;
    try {
      await api(`/items/${item.id}`, { method: "DELETE" });
      notify("Article supprimé.");
      dialog.close();
      await onSaved();
    } catch (err) { notify(err.message, true); }
  });
}

async function openHistoryDialog(item) {
  const movements = await api(`/items/${item.id}/movements`);
  const rows = movements.map((m) => `<tr><td>${formatDate(m.created_at)}</td><td>${h(m.reason) || "—"}</td>
    <td class="num ${m.delta > 0 ? "positive" : "negative"}">${m.delta > 0 ? "+" : ""}${m.delta}</td>
    <td class="num">${m.quantity}</td></tr>`).join("");
  openDialog(`<div>
    <h2>Historique : ${h(item.name)}</h2>
    <div class="history card">${movements.length ? `<table>
      <thead><tr><th>Date</th><th>Motif</th><th class="num">Variation</th><th class="num">Stock</th></tr></thead>
      <tbody>${rows}</tbody></table>` : '<div class="empty">Aucun mouvement enregistré.</div>'}</div>
    <div class="dialog-footer"><span class="spacer"></span><form method="dialog"><button class="btn">Fermer</button></form></div></div>`);
}

// ---------- Sheet list ----------

async function renderSheetList() {
  const { sheets, errors } = await api("/sheets");
  const categories = [...new Set(sheets.map((s) => s.category))];
  let categoryFilter = "";
  let searchText = "";
  view.innerHTML = `
    <div class="page-title">
      <div><div class="eyebrow">Documentation</div><h1>Fiches techniques</h1>
      <p>Livrées avec les mises à jour. Un appareil manque ? Demandez sa fiche.</p></div>
      <span class="spacer"></span><a class="btn btn-primary" href="#/requests">Demander une fiche</a>
    </div>
    ${errors.length ? `<div class="sheet-errors"><h2>${errors.length} fiche(s) illisible(s)</h2><ul>
      ${errors.map((e) => `<li><code>${h(e.id)}.md</code> : ${h(e.error)}</li>`).join("")}</ul></div>` : ""}
    <div class="toolbar">
      <input class="search" type="search" placeholder="Rechercher une fiche…" aria-label="Rechercher une fiche" id="search">
      <div class="filters" id="filters">
        <button class="btn active" data-category="" type="button">Toutes</button>
        ${categories.map((c) => `<button class="btn" data-category="${h(c)}" type="button">${h(c)}</button>`).join("")}
      </div>
    </div>
    <div class="grid" id="sheet-grid"></div>`;

  const grid = view.querySelector("#sheet-grid");
  function render() {
    const text = searchText.toLowerCase();
    const visible = sheets.filter((s) => (!categoryFilter || s.category === categoryFilter) &&
      (!text || [s.name, s.part_number, s.manufacturer, s.description, ...s.tags].join(" ").toLowerCase().includes(text)));
    grid.innerHTML = visible.length ? visible.map((s) => `
      <a class="sheet-card" href="#/sheet/${h(s.id)}">
        <div class="eyebrow">${h(s.category)}</div>
        <h3>${h(s.name)}</h3>
        <p>${h(s.description) || '<span class="muted">Pas de description.</span>'}</p>
        <div class="footer">
          ${s.pin_count ? `<span class="badge badge-accent">${s.pin_count} broches</span>` : ""}
          ${s.tags.slice(0, 4).map((t) => `<span class="badge">${h(t)}</span>`).join("")}
        </div>
      </a>`).join("")
      : `<div class="empty" style="grid-column:1/-1"><b>Aucune fiche</b>${sheets.length
        ? "Aucune fiche ne correspond à la recherche."
        : "Demandez la première depuis « Demander une fiche »."}</div>`;
  }
  render();
  view.querySelector("#search").addEventListener("input", (e) => { searchText = e.target.value; render(); });
  view.querySelector("#filters").addEventListener("click", (e) => {
    const button = e.target.closest("button");
    if (!button) return;
    categoryFilter = button.dataset.category;
    view.querySelectorAll("#filters button").forEach((b) => b.classList.toggle("active", b === button));
    render();
  });
}

// ---------- Sheet requests ----------

// Common hardware (sheets/catalog.yaml): each device opens the GitHub request form
// already filled in. Sheets are written as requests come in.
async function renderRequests() {
  const { devices, categories, other_request_url: otherUrl } = await api("/catalog");
  let categoryFilter = "";
  let searchText = "";
  view.innerHTML = `
    <div class="page-title">
      <div><div class="eyebrow">Fiches techniques</div><h1>Demander une fiche</h1>
      <p>Choisissez un appareil : le formulaire de demande s'ouvre sur GitHub, déjà rempli (nom, référence,
      catégorie, fiche technique, dimensions). La fiche arrive avec une prochaine mise à jour.</p></div>
      <span class="spacer"></span>
      <a class="btn" href="${h(otherUrl)}" target="_blank" rel="noopener">Autre appareil ↗</a>
    </div>
    <div class="toolbar">
      <input class="search" type="search" placeholder="Rechercher : nom, référence, fabricant…" aria-label="Rechercher un appareil" id="search">
      <div class="filters" id="filters">
        <button class="btn active" data-category="" type="button">Tous</button>
        ${categories.map((c) => `<button class="btn" data-category="${h(c)}" type="button">${h(c)}</button>`).join("")}
      </div>
    </div>
    <div class="grid" id="catalog-grid"></div>`;

  const grid = view.querySelector("#catalog-grid");
  function render() {
    const text = searchText.toLowerCase();
    const visible = devices.filter((d) => (!categoryFilter || d.category === categoryFilter) &&
      (!text || [d.name, d.manufacturer, d.part_number, d.description].join(" ").toLowerCase().includes(text)));
    grid.innerHTML = visible.length ? visible.map((d) => `
      <div class="sheet-card catalog-card">
        <div class="eyebrow">${h(d.category)}</div>
        <h3>${h(d.name)}</h3>
        <p>${h(d.description)}</p>
        <div class="muted">${h([d.manufacturer, d.part_number, d.dimensions].filter(Boolean).join(" · "))}</div>
        <div class="footer">
          ${d.has_sheet
            ? `<span class="badge badge-accent">Fiche disponible</span><span class="spacer"></span><a class="btn" href="#/sheet/${h(d.id)}">Voir la fiche</a>`
            : `<span class="spacer"></span><a class="btn btn-primary" href="${h(d.request_url)}" target="_blank" rel="noopener">Demander ↗</a>`}
        </div>
      </div>`).join("")
      : `<div class="empty" style="grid-column:1/-1"><b>Aucun appareil ne correspond</b>
        « Autre appareil » ouvre le formulaire de demande vide.</div>`;
  }
  render();
  view.querySelector("#search").addEventListener("input", (e) => { searchText = e.target.value; render(); });
  view.querySelector("#filters").addEventListener("click", (e) => {
    const button = e.target.closest("button");
    if (!button) return;
    categoryFilter = button.dataset.category;
    view.querySelectorAll("#filters button").forEach((b) => b.classList.toggle("active", b === button));
    render();
  });
}

// ---------- Sheet page ----------

function pinoutSection(sheet, idPrefix) {
  const positions = pinPositions(sheet);
  if (!positions.length) return '<div class="empty"><b>Pas de brochage</b>Ajoutez une section « pinout » à la fiche.</div>';
  const types = [...new Set(positions.map((p) => p.pin.type))];
  const multipleRows = sheet.pinout.rows.length > 1;
  return `
    <div class="legend" role="group" aria-label="Filtrer par type de broche">
      ${types.map((t) => `<button type="button" data-type="${t}"><span class="dot" style="background:${pinType(t).color}"></span>${h(pinType(t).label)}</button>`).join("")}
    </div>
    <div class="pinout">
      <div class="pinout-diagram" id="${idPrefix}-diagram"></div>
      <div class="card"><table class="pin-table">
        <thead><tr><th>N°</th><th>Nom</th><th>Fonctions</th><th>Description</th></tr></thead>
        <tbody>${positions.map((p) => `<tr data-key="${p.key}">
          <td class="muted">${multipleRows ? `${h(p.row.name)}·` : ""}${h(p.pin.n)}</td>
          <td><span class="pin-name"><span class="dot" style="background:${pinType(p.pin.type).color}" title="${h(pinType(p.pin.type).label)}"></span>${h(p.pin.name)}</span></td>
          <td><div class="functions">${p.pin.functions.map((f) => `<code>${h(f)}</code>`).join("")}</div></td>
          <td>${h(p.pin.description)}</td></tr>`).join("")}</tbody></table></div>
    </div>`;
}

// Link the 2D diagram, the pin table and the 3D view: hovering one lights up the others.
function linkPinViews(root, sheet, diagramId, viewerPromise) {
  const rows = new Map([...root.querySelectorAll(".pin-table tr[data-key]")].map((tr) => [tr.dataset.key, tr]));
  let viewer = null;
  let diagram = null;
  const hover = (key, source) => {
    rows.forEach((tr, k) => tr.classList.toggle("hover", k === key));
    if (source !== "diagram") diagram?.hover(key);
    if (source !== "3d") viewer?.hover(key);
  };
  const diagramContainer = root.querySelector(`#${diagramId}`);
  if (diagramContainer) diagram = createPinoutDiagram(diagramContainer, sheet, { onHover: (k) => hover(k, "diagram") });
  viewerPromise?.then((v) => { viewer = v; });
  rows.forEach((tr, key) => {
    tr.addEventListener("mouseenter", () => hover(key, "table"));
    tr.addEventListener("mouseleave", () => hover(null, "table"));
  });

  const positions = pinPositions(sheet);
  const selectedTypes = new Set();
  root.querySelector(".legend")?.addEventListener("click", (e) => {
    const button = e.target.closest("button[data-type]");
    if (!button) return;
    const type = button.dataset.type;
    selectedTypes.has(type) ? selectedTypes.delete(type) : selectedTypes.add(type);
    button.classList.toggle("active", selectedTypes.has(type));
    const keys = selectedTypes.size ? new Set(positions.filter((p) => selectedTypes.has(p.pin.type)).map((p) => p.key)) : null;
    diagram?.highlight(keys);
    viewer?.highlight(keys);
    rows.forEach((tr, k) => tr.classList.toggle("dimmed", Boolean(keys) && !keys.has(k)));
  });
  return { hoverFrom3D: (key) => hover(key, "3d") };
}

function warningsBlock(warnings, title) {
  if (!warnings.length) return "";
  return `<div class="warnings"><b>${title}</b><ul>${warnings.map((w) => `<li>${h(w)}</li>`).join("")}</ul></div>`;
}

async function renderSheet(id) {
  const sheet = await api(`/sheets/${id}`);
  const items = await api(`/items?sheet=${encodeURIComponent(id)}`);
  const inStock = items.reduce((total, item) => total + item.quantity, 0);
  document.title = `${sheet.name} · Prométhée`;
  cleanups.push(() => { document.title = "Prométhée"; });
  const specs = Object.entries(sheet.specs);
  view.innerHTML = `
    <div class="sheet-header">
      <div class="text">
        <div class="eyebrow">${h(sheet.category)}</div>
        <h1>${h(sheet.name)}</h1>
        ${sheet.manufacturer || sheet.part_number ? `<div class="muted">${h([sheet.manufacturer, sheet.part_number].filter(Boolean).join(" · "))}</div>` : ""}
        <p>${h(sheet.description)}</p>
        <div class="tags">
          <span class="badge ${inStock ? "badge-accent" : "badge-danger"}">${inStock ? `${inStock} en stock` : "Pas en stock"}</span>
          ${sheet.tags.map((t) => `<span class="badge">${h(t)}</span>`).join("")}
        </div>
      </div>
      <div class="buttons">
        <button class="btn" id="add-to-stock" type="button">Ajouter au stock</button>
        ${sheet.model ? `<a class="btn" href="api/${h(sheet.model)}" download="${h(id)}.glb" title="Modèle 3D au format glTF (.glb), lisible par Blender, la Visionneuse 3D de Windows…">Modèle 3D ↓</a>` : ""}
        <a class="btn" href="${h(sheet.correction_url)}" target="_blank" rel="noopener">Signaler une erreur ↗</a>
      </div>
    </div>
    ${warningsBlock(sheet.warnings, "À vérifier dans la fiche")}
    <div id="scene"></div>
    <div class="tabs" role="tablist">
      <button role="tab" aria-selected="true" data-tab="pinout" type="button">Brochage</button>
      <button role="tab" aria-selected="false" data-tab="usage" type="button">Utilisation</button>
      <button role="tab" aria-selected="false" data-tab="specs" type="button">Caractéristiques</button>
      <button role="tab" aria-selected="false" data-tab="stock" type="button">Stock (${items.length})</button>
    </div>
    <section data-panel="pinout">${pinoutSection(sheet, "sheet")}</section>
    <section data-panel="usage" hidden><div class="prose">${sheet.html || '<p class="muted">Pas de texte dans cette fiche.</p>'}</div></section>
    <section data-panel="specs" hidden>
      ${specs.length ? `<dl class="specs">${specs.map(([k, v]) => `<dt>${h(k)}</dt><dd>${h(v)}</dd>`).join("")}</dl>` : '<p class="muted">Aucune caractéristique renseignée.</p>'}
      ${sheet.links.length ? `<ul class="links">${sheet.links.map((l) => `<li><a href="${h(l.url)}" target="_blank" rel="noopener noreferrer">${h(l.title)}</a></li>`).join("")}</ul>` : ""}
    </section>
    <section data-panel="stock" hidden>
      <div class="card">${items.length ? `<table><thead><tr><th>Article</th><th>Emplacement</th><th class="num">Quantité</th></tr></thead><tbody>
        ${items.map((i) => `<tr><td><b>${h(i.name)}</b> <span class="muted">${h([i.value, i.package].filter(Boolean).join(" · "))}</span></td>
        <td>${h(i.location) || "—"}</td><td class="num">${i.quantity}</td></tr>`).join("")}</tbody></table>`
        : '<div class="empty"><b>Aucun article lié</b>Utilisez « Ajouter au stock » pour en créer un.</div>'}</div>
    </section>`;

  const link = { hoverFrom3D: () => {} };
  const viewerPromise = mountViewer(view.querySelector("#scene"), sheet, { onHover: (k) => link.hoverFrom3D(k) });
  Object.assign(link, linkPinViews(view, sheet, "sheet-diagram", viewerPromise));

  view.querySelector(".tabs").addEventListener("click", (e) => {
    const tab = e.target.closest("button[data-tab]");
    if (!tab) return;
    view.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", String(b === tab)));
    view.querySelectorAll("[data-panel]").forEach((p) => { p.hidden = p.dataset.panel !== tab.dataset.tab; });
  });
  view.querySelector("#add-to-stock").addEventListener("click", async () => {
    openItemDialog(null, await fetchSheets(), route, { name: sheet.name, category: sheet.category, sheet: id, quantity: 1 });
  });
}
