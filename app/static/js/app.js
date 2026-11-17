// Interface de Prométhée : routeur et vues (stock, fiches, fiche détaillée, éditeur).

import { api, h, notifier, debounce, formaterDate, slug, TYPES, type } from "./commun.js";
import { positionsBroches } from "./geometrie.js";
import { creerSchema } from "./schema.js";

const vue = document.getElementById("vue");
let nettoyage = [];

function nettoyer() {
  nettoyage.forEach((f) => { try { f(); } catch { /* déjà détruit */ } });
  nettoyage = [];
}

async function vue3D(conteneur, fiche, options) {
  conteneur.innerHTML = '<div class="scene-chargement">Chargement de la vue 3D…</div>';
  const { creerVue3D } = await import("./vue3d.js");
  const v = creerVue3D(conteneur, fiche, options);
  nettoyage.push(() => v.detruire());
  return v;
}

// ---------- Routeur ----------

const routes = [
  [/^#\/stock$/, vueStock],
  [/^#\/fiches$/, vueFiches],
  [/^#\/fiche\/([a-z0-9-]+)$/, vueFiche],
  [/^#\/nouvelle$/, () => vueEditeur(null)],
  [/^#\/modifier\/([a-z0-9-]+)$/, vueEditeur],
];

async function router() {
  const hash = location.hash || "#/stock";
  nettoyer();
  for (const a of document.querySelectorAll("[data-nav]")) {
    const actif = hash.startsWith(`#/${a.dataset.nav}`) || (a.dataset.nav === "fiches" && /^#\/(fiche|modifier|nouvelle)/.test(hash));
    a.classList.toggle("actif", actif);
  }
  for (const [motif, fn] of routes) {
    const m = hash.match(motif);
    if (m) {
      vue.innerHTML = "";
      try {
        await fn(...m.slice(1));
      } catch (err) {
        vue.innerHTML = `<div class="vide"><b>Impossible d'afficher cette page</b>${h(err.message)}</div>`;
      }
      window.scrollTo(0, 0);
      return;
    }
  }
  location.hash = "#/stock";
}

window.addEventListener("hashchange", router);
router();

// ---------- Stock ----------

async function vueStock() {
  const etat = { q: "", categorie: "", alerte: false };
  vue.innerHTML = `
    <div class="titre-page">
      <div><div class="surtitre">Inventaire</div><h1>Stock</h1><p>Composants, cartes et modules, avec leur emplacement.</p></div>
    </div>
    <div class="indicateurs" id="indicateurs"></div>
    <div class="barre">
      <input class="recherche" type="search" placeholder="Rechercher : nom, valeur, emplacement…" aria-label="Rechercher" id="q">
      <select id="categorie" aria-label="Catégorie"><option value="">Toutes les catégories</option></select>
      <label class="case"><input type="checkbox" id="alerte"> À réapprovisionner</label>
      <span class="espace"></span>
      <button class="bouton" id="importer" type="button">Importer CSV</button>
      <a class="bouton" href="/api/export.csv" download>Exporter CSV</a>
      <button class="bouton bouton-or" id="ajouter" type="button">+ Ajouter</button>
      <input type="file" id="fichier-csv" accept=".csv,text/csv" hidden>
    </div>
    <div class="carte-bloc" id="liste"></div>`;

  const liste = vue.querySelector("#liste");
  const selCategorie = vue.querySelector("#categorie");
  let fiches = [];

  async function indicateurs() {
    const r = await api("/resume");
    vue.querySelector("#indicateurs").innerHTML = `
      <div class="indicateur"><b>${r.articles}</b><span>références</span></div>
      <div class="indicateur"><b>${r.pieces}</b><span>pièces en stock</span></div>
      <div class="indicateur ${r.alertes ? "alerte" : ""}"><b>${r.alertes}</b><span>à réapprovisionner</span></div>
      <div class="indicateur"><b>${r.fiches}</b><span>fiches techniques</span></div>`;
  }

  async function categories() {
    const c = await api("/categories");
    const choisie = selCategorie.value;
    selCategorie.innerHTML = '<option value="">Toutes les catégories</option>' +
      c.stock.map((x) => `<option ${x === choisie ? "selected" : ""}>${h(x)}</option>`).join("");
  }

  async function charger() {
    const p = new URLSearchParams({ q: etat.q, categorie: etat.categorie, alerte: etat.alerte });
    const articles = await api(`/articles?${p}`);
    if (!articles.length) {
      const filtre = etat.q || etat.categorie || etat.alerte;
      liste.innerHTML = `<div class="vide"><b>${filtre ? "Aucun article ne correspond" : "Le stock est vide"}</b>
        ${filtre ? "Modifiez la recherche ou les filtres." : "Ajoutez un premier article, ou importez un fichier CSV."}</div>`;
      return;
    }
    const nomsFiches = new Map(fiches.map((f) => [f.id, f.nom]));
    liste.innerHTML = `<table class="table-stock">
      <thead><tr><th>Article</th><th>Catégorie</th><th>Emplacement</th><th class="nombre">Quantité</th><th class="nombre">Seuil</th><th>Fiche</th><th></th></tr></thead>
      <tbody>${articles.map((a) => {
        const bas = a.quantite <= a.seuil;
        const details = [a.valeur, a.boitier].filter(Boolean).join(" · ");
        return `<tr data-id="${a.id}">
          <td class="col-nom"><b>${h(a.nom)}</b>${details ? `<div class="secondaire">${h(details)}</div>` : ""}</td>
          <td>${a.categorie ? `<span class="pastille">${h(a.categorie)}</span>` : ""}</td>
          <td>${h(a.emplacement) || '<span class="secondaire">—</span>'}</td>
          <td class="nombre"><span class="quantite ${bas ? "bas" : ""}">
            <button class="bouton bouton-icone" data-delta="-1" type="button" aria-label="Retirer une pièce" ${a.quantite ? "" : "disabled"}>−</button>
            <b>${a.quantite}</b>
            <button class="bouton bouton-icone" data-delta="1" type="button" aria-label="Ajouter une pièce">+</button></span></td>
          <td class="nombre col-seuil">${a.seuil}</td>
          <td class="col-fiche">${a.fiche ? (nomsFiches.has(a.fiche)
            ? `<a href="#/fiche/${h(a.fiche)}">${h(nomsFiches.get(a.fiche))}</a>`
            : `<span class="pastille pastille-alerte" title="Fiche introuvable">${h(a.fiche)}</span>`) : ""}</td>
          <td class="actions col-actions">
            <button class="bouton" data-action="historique" type="button">Historique</button>
            <button class="bouton" data-action="modifier" type="button">Modifier</button></td>
        </tr>`;
      }).join("")}</tbody></table>`;
  }

  async function tout() {
    await Promise.all([charger(), indicateurs(), categories()]);
  }

  fiches = (await api("/fiches")).fiches;
  await tout();

  vue.querySelector("#q").addEventListener("input", debounce((e) => { etat.q = e.target.value; charger(); }, 200));
  selCategorie.addEventListener("change", (e) => { etat.categorie = e.target.value; charger(); });
  vue.querySelector("#alerte").addEventListener("change", (e) => { etat.alerte = e.target.checked; charger(); });
  vue.querySelector("#ajouter").addEventListener("click", () => dialogueArticle(null, fiches, tout));
  const fichierCsv = vue.querySelector("#fichier-csv");
  vue.querySelector("#importer").addEventListener("click", () => fichierCsv.click());
  fichierCsv.addEventListener("change", async () => {
    if (!fichierCsv.files[0]) return;
    const fd = new FormData();
    fd.append("fichier", fichierCsv.files[0]);
    try {
      const r = await api("/import", { methode: "POST", corps: fd });
      notifier(`Import terminé : ${r.crees} créé(s), ${r.mis_a_jour} mis à jour.`);
      await tout();
    } catch (err) { notifier(err.message, true); }
    fichierCsv.value = "";
  });

  liste.addEventListener("click", async (e) => {
    const ligne = e.target.closest("tr[data-id]");
    if (!ligne) return;
    const id = Number(ligne.dataset.id);
    const bouton = e.target.closest("button");
    if (!bouton) return;
    try {
      if (bouton.dataset.delta) {
        bouton.disabled = true;
        await api(`/articles/${id}/mouvements`, { methode: "POST", corps: { delta: Number(bouton.dataset.delta), motif: Number(bouton.dataset.delta) > 0 ? "Ajout" : "Sortie" } });
        await Promise.all([charger(), indicateurs()]);
      } else if (bouton.dataset.action === "modifier") {
        dialogueArticle(await api(`/articles/${id}`), fiches, tout);
      } else if (bouton.dataset.action === "historique") {
        dialogueHistorique(await api(`/articles/${id}`));
      }
    } catch (err) { notifier(err.message, true); bouton.disabled = false; }
  });
}

function dialogue(html) {
  const d = document.createElement("dialog");
  d.innerHTML = html;
  document.body.append(d);
  d.addEventListener("close", () => d.remove());
  nettoyage.push(() => d.close());
  d.showModal();
  return d;
}

function dialogueArticle(article, fiches, apres, prerempli = {}) {
  const a = article || { quantite: 0, seuil: 0, ...prerempli };
  const champ = (nom, libelle, attrs = "", classe = "") =>
    `<label class="champ ${classe}"><span>${libelle}</span><input name="${nom}" value="${h(a[nom] ?? "")}" ${attrs}></label>`;
  const d = dialogue(`<form method="dialog">
    <h2>${article ? "Modifier l'article" : "Nouvel article"}</h2>
    <div class="formulaire">
      ${champ("nom", "Nom", 'required autofocus placeholder="Résistance, ESP32…"', "large")}
      ${champ("categorie", "Catégorie", 'list="liste-categories" placeholder="Résistance, Capteur…"')}
      ${champ("valeur", "Valeur", 'placeholder="10 kΩ, 100 nF…"')}
      ${champ("boitier", "Boîtier", 'placeholder="0805, DIP-8, TO-92…"')}
      ${champ("emplacement", "Emplacement", 'placeholder="Tiroir A3"')}
      ${champ("quantite", "Quantité", 'type="number" min="0" step="1" required')}
      ${champ("seuil", "Seuil d'alerte", 'type="number" min="0" step="1"')}
      <label class="champ"><span>Fiche liée</span><select name="fiche"><option value="">Aucune</option>
        ${fiches.map((f) => `<option value="${h(f.id)}" ${f.id === a.fiche ? "selected" : ""}>${h(f.nom)}</option>`).join("")}</select></label>
      ${champ("fournisseur", "Fournisseur")}
      ${champ("prix", "Prix unitaire (€)", 'type="number" min="0" step="0.001"')}
      <label class="champ large"><span>Notes</span><textarea name="notes" rows="3">${h(a.notes ?? "")}</textarea></label>
    </div>
    <datalist id="liste-categories"></datalist>
    <div class="dialogue-pied">
      ${article ? '<button class="bouton bouton-danger" value="supprimer" type="button" data-action="supprimer">Supprimer</button>' : ""}
      <span class="espace"></span>
      <button class="bouton" value="annuler" formnovalidate>Annuler</button>
      <button class="bouton bouton-or" value="enregistrer" type="submit">Enregistrer</button>
    </div></form>`);
  api("/categories").then((c) => {
    const toutes = [...new Set([...c.stock, ...c.fiches])].sort((x, y) => x.localeCompare(y, "fr"));
    d.querySelector("#liste-categories").innerHTML = toutes.map((x) => `<option value="${h(x)}">`).join("");
  });
  const form = d.querySelector("form");
  form.addEventListener("submit", async (e) => {
    if (e.submitter?.value !== "enregistrer") return;
    e.preventDefault();
    const donnees = Object.fromEntries(new FormData(form));
    donnees.quantite = Number(donnees.quantite || 0);
    donnees.seuil = Number(donnees.seuil || 0);
    donnees.prix = donnees.prix === "" ? null : Number(donnees.prix);
    try {
      if (article) await api(`/articles/${article.id}`, { methode: "PUT", corps: donnees });
      else await api("/articles", { methode: "POST", corps: donnees });
      notifier(article ? "Article mis à jour." : "Article ajouté.");
      d.close();
      await apres();
    } catch (err) { notifier(err.message, true); }
  });
  d.querySelector("[data-action=supprimer]")?.addEventListener("click", async () => {
    if (!confirm(`Supprimer « ${article.nom} » et son historique ?`)) return;
    try {
      await api(`/articles/${article.id}`, { methode: "DELETE" });
      notifier("Article supprimé.");
      d.close();
      await apres();
    } catch (err) { notifier(err.message, true); }
  });
}

async function dialogueHistorique(article) {
  const mouvements = await api(`/articles/${article.id}/mouvements`);
  dialogue(`<div>
    <h2>Historique : ${h(article.nom)}</h2>
    <div class="historique carte-bloc">${mouvements.length ? `<table>
      <thead><tr><th>Date</th><th>Motif</th><th class="nombre">Variation</th><th class="nombre">Stock</th></tr></thead>
      <tbody>${mouvements.map((m) => `<tr><td>${formaterDate(m.date)}</td><td>${h(m.motif) || "—"}</td>
        <td class="nombre ${m.delta > 0 ? "positif" : "negatif"}">${m.delta > 0 ? "+" : ""}${m.delta}</td>
        <td class="nombre">${m.quantite}</td></tr>`).join("")}</tbody></table>`
      : '<div class="vide">Aucun mouvement enregistré.</div>'}</div>
    <div class="dialogue-pied"><span class="espace"></span><form method="dialog"><button class="bouton">Fermer</button></form></div></div>`);
}

// ---------- Liste des fiches ----------

async function vueFiches() {
  const { fiches, erreurs } = await api("/fiches");
  const categories = [...new Set(fiches.map((f) => f.categorie))];
  let filtre = "", texte = "";
  vue.innerHTML = `
    <div class="titre-page">
      <div><div class="surtitre">Documentation</div><h1>Fiches techniques</h1>
      <p>Un fichier par appareil dans le dossier <code>fiches/</code>, à écrire à la main ou depuis l'éditeur.</p></div>
      <span class="espace"></span><a class="bouton bouton-or" href="#/nouvelle">+ Nouvelle fiche</a>
    </div>
    ${erreurs.length ? `<div class="erreurs-fiches"><h2>${erreurs.length} fiche(s) illisible(s)</h2><ul>
      ${erreurs.map((e) => `<li><code>${h(e.id)}.md</code> : ${h(e.erreur)} <a href="#/modifier/${h(e.id)}">Corriger</a></li>`).join("")}</ul></div>` : ""}
    <div class="barre">
      <input class="recherche" type="search" placeholder="Rechercher une fiche…" aria-label="Rechercher une fiche" id="q">
      <div class="filtres" id="filtres">
        <button class="bouton actif" data-categorie="" type="button">Toutes</button>
        ${categories.map((c) => `<button class="bouton" data-categorie="${h(c)}" type="button">${h(c)}</button>`).join("")}
      </div>
    </div>
    <div class="grille" id="grille"></div>`;
  const grille = vue.querySelector("#grille");
  function afficher() {
    const t = texte.toLowerCase();
    const visibles = fiches.filter((f) => (!filtre || f.categorie === filtre) &&
      (!t || [f.nom, f.reference, f.fabricant, f.description, ...f.tags].join(" ").toLowerCase().includes(t)));
    grille.innerHTML = visibles.length ? visibles.map((f) => `
      <a class="fiche-carte" href="#/fiche/${h(f.id)}">
        <div class="surtitre">${h(f.categorie)}</div>
        <h3>${h(f.nom)}</h3>
        <p>${h(f.description) || '<span class="secondaire">Pas de description.</span>'}</p>
        <div class="pied">
          ${f.nb_broches ? `<span class="pastille pastille-or">${f.nb_broches} broches</span>` : ""}
          ${f.tags.slice(0, 4).map((x) => `<span class="pastille">${h(x)}</span>`).join("")}
        </div>
      </a>`).join("")
      : `<div class="vide" style="grid-column:1/-1"><b>Aucune fiche</b>${fiches.length ? "Aucune fiche ne correspond à la recherche." : "Créez la première depuis l'éditeur, ou déposez un fichier .md dans le dossier fiches/."}</div>`;
  }
  afficher();
  vue.querySelector("#q").addEventListener("input", (e) => { texte = e.target.value; afficher(); });
  vue.querySelector("#filtres").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    filtre = b.dataset.categorie;
    vue.querySelectorAll("#filtres button").forEach((x) => x.classList.toggle("actif", x === b));
    afficher();
  });
}

// ---------- Fiche détaillée ----------

function blocBrochage(fiche, synchro) {
  const positions = positionsBroches(fiche);
  if (!positions.length) return '<div class="vide"><b>Pas de brochage</b>Ajoutez une section « brochage » à la fiche.</div>';
  const typesPresents = [...new Set(positions.map((p) => p.broche.type))];
  return `
    <div class="legende" role="group" aria-label="Filtrer par type de broche">
      ${typesPresents.map((t) => `<button type="button" data-type="${t}"><span class="puce" style="background:${type(t).couleur}"></span>${h(type(t).libelle)}</button>`).join("")}
    </div>
    <div class="brochage">
      <div class="schema" id="${synchro}-schema"></div>
      <div class="carte-bloc"><table class="table-broches">
        <thead><tr><th>N°</th><th>Nom</th><th>Fonctions</th><th>Description</th></tr></thead>
        <tbody>${positions.map((p) => `<tr data-cle="${p.cle}">
          <td class="secondaire">${fiche.brochage.rangees.length > 1 ? `${h(p.rangee.nom)}·` : ""}${h(p.broche.n)}</td>
          <td><span class="nom-broche"><span class="puce" style="background:${type(p.broche.type).couleur}" title="${h(type(p.broche.type).libelle)}"></span>${h(p.broche.nom)}</span></td>
          <td><div class="fonctions">${p.broche.fonctions.map((f) => `<code>${h(f)}</code>`).join("")}</div></td>
          <td>${h(p.broche.desc)}</td></tr>`).join("")}</tbody></table></div>
    </div>`;
}

// Relie schéma 2D, tableau et vue 3D : survoler l'un éclaire les autres.
function relier(racine, fiche, schemaId, vue3dPromesse) {
  const lignes = new Map([...racine.querySelectorAll(".table-broches tr[data-cle]")].map((tr) => [tr.dataset.cle, tr]));
  let v3d = null;
  let schema = null;
  const survol = (cle, source) => {
    lignes.forEach((tr, c) => tr.classList.toggle("survol", c === cle));
    if (source !== "schema") schema?.survoler(cle);
    if (source !== "3d") v3d?.survoler(cle);
  };
  const conteneurSchema = racine.querySelector(`#${schemaId}`);
  if (conteneurSchema) schema = creerSchema(conteneurSchema, fiche, { surSurvol: (c) => survol(c, "schema") });
  vue3dPromesse?.then((v) => { v3d = v; });
  lignes.forEach((tr, cle) => {
    tr.addEventListener("mouseenter", () => survol(cle, "table"));
    tr.addEventListener("mouseleave", () => survol(null, "table"));
  });
  const positions = positionsBroches(fiche);
  const actifs = new Set();
  racine.querySelector(".legende")?.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-type]");
    if (!b) return;
    actifs.has(b.dataset.type) ? actifs.delete(b.dataset.type) : actifs.add(b.dataset.type);
    b.classList.toggle("actif", actifs.has(b.dataset.type));
    const cles = actifs.size ? new Set(positions.filter((p) => actifs.has(p.broche.type)).map((p) => p.cle)) : null;
    schema?.surligner(cles);
    v3d?.surligner(cles);
    lignes.forEach((tr, c) => tr.classList.toggle("attenuee", Boolean(cles) && !cles.has(c)));
  });
  return { survol: (cle) => survol(cle, "3d") };
}

async function vueFiche(id) {
  const fiche = await api(`/fiches/${id}`);
  const articles = await api(`/articles?fiche=${encodeURIComponent(id)}`);
  const enStock = articles.reduce((n, a) => n + a.quantite, 0);
  document.title = `${fiche.nom} · Prométhée`;
  nettoyage.push(() => { document.title = "Prométhée"; });
  const specs = Object.entries(fiche.caracteristiques);
  vue.innerHTML = `
    <div class="fiche-entete">
      <div class="texte">
        <div class="surtitre">${h(fiche.categorie)}</div>
        <h1>${h(fiche.nom)}</h1>
        ${fiche.fabricant || fiche.reference ? `<div class="secondaire">${h([fiche.fabricant, fiche.reference].filter(Boolean).join(" · "))}</div>` : ""}
        <p>${h(fiche.description)}</p>
        <div class="etiquettes">
          <span class="pastille ${enStock ? "pastille-or" : "pastille-alerte"}">${enStock ? `${enStock} en stock` : "Pas en stock"}</span>
          ${fiche.tags.map((t) => `<span class="pastille">${h(t)}</span>`).join("")}
        </div>
      </div>
      <div class="boutons">
        <button class="bouton" id="ajout-stock" type="button">Ajouter au stock</button>
        <a class="bouton" href="#/modifier/${h(id)}">Modifier la fiche</a>
      </div>
    </div>
    ${fiche.avertissements.length ? `<div class="avertissements"><b>À vérifier dans la fiche</b><ul>${fiche.avertissements.map((a) => `<li>${h(a)}</li>`).join("")}</ul></div>` : ""}
    <div id="scene"></div>
    <div class="onglets" role="tablist">
      <button role="tab" aria-selected="true" data-onglet="brochage" type="button">Brochage</button>
      <button role="tab" aria-selected="false" data-onglet="utilisation" type="button">Utilisation</button>
      <button role="tab" aria-selected="false" data-onglet="caracteristiques" type="button">Caractéristiques</button>
      <button role="tab" aria-selected="false" data-onglet="stock" type="button">Stock (${articles.length})</button>
    </div>
    <section data-panneau="brochage">${blocBrochage(fiche, "fiche")}</section>
    <section data-panneau="utilisation" hidden><div class="contenu">${fiche.html || '<p class="secondaire">Pas de texte dans cette fiche.</p>'}</div></section>
    <section data-panneau="caracteristiques" hidden>
      ${specs.length ? `<dl class="specs">${specs.map(([k, v]) => `<dt>${h(k)}</dt><dd>${h(v)}</dd>`).join("")}</dl>` : '<p class="secondaire">Aucune caractéristique renseignée.</p>'}
      ${fiche.liens.length ? `<ul class="liens">${fiche.liens.map((l) => `<li><a href="${h(l.url)}" target="_blank" rel="noopener noreferrer">${h(l.titre)}</a></li>`).join("")}</ul>` : ""}
    </section>
    <section data-panneau="stock" hidden>
      <div class="carte-bloc">${articles.length ? `<table><thead><tr><th>Article</th><th>Emplacement</th><th class="nombre">Quantité</th></tr></thead><tbody>
        ${articles.map((a) => `<tr><td><b>${h(a.nom)}</b> <span class="secondaire">${h([a.valeur, a.boitier].filter(Boolean).join(" · "))}</span></td>
        <td>${h(a.emplacement) || "—"}</td><td class="nombre">${a.quantite}</td></tr>`).join("")}</tbody></table>`
        : '<div class="vide"><b>Aucun article lié</b>Utilisez « Ajouter au stock » pour en créer un.</div>'}</div>
    </section>`;

  const lien = { survol: () => {} };
  const promesse3d = vue3D(vue.querySelector("#scene"), fiche, { surSurvol: (c) => lien.survol(c) });
  Object.assign(lien, relier(vue, fiche, "fiche-schema", promesse3d));

  vue.querySelector(".onglets").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-onglet]");
    if (!b) return;
    vue.querySelectorAll(".onglets button").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
    vue.querySelectorAll("[data-panneau]").forEach((p) => { p.hidden = p.dataset.panneau !== b.dataset.onglet; });
  });
  vue.querySelector("#ajout-stock").addEventListener("click", async () => {
    const { fiches } = await api("/fiches");
    dialogueArticle(null, fiches, router, { nom: fiche.nom, categorie: fiche.categorie, fiche: id, quantite: 1 });
  });
}

// ---------- Éditeur ----------

async function vueEditeur(id) {
  const nouvelle = !id;
  const source = nouvelle ? await api("/fiches/modele-vierge", { brut: true }) : await api(`/fiches/${id}/source`, { brut: true });
  vue.innerHTML = `
    <div class="titre-page">
      <div><div class="surtitre">${nouvelle ? "Nouvelle fiche" : "Modifier"}</div>
      <h1>${nouvelle ? "Créer une fiche" : `<code>${h(id)}.md</code>`}</h1>
      <p>En-tête YAML (boîtier, brochage, caractéristiques) puis texte en Markdown. Format détaillé dans <code>docs/format-fiche.md</code>.</p></div>
    </div>
    <div class="editeur-champs">
      ${nouvelle ? `<label class="champ"><span>Identifiant (nom du fichier)</span><input id="identifiant" placeholder="mon-appareil" pattern="[a-z0-9][a-z0-9-]*"></label>` : ""}
      <button class="bouton" id="modele" type="button">Joindre un modèle 3D…</button>
      <input type="file" id="fichier-modele" accept=".glb,.gltf,.stl" hidden>
      <span class="espace"></span>
      ${nouvelle ? "" : '<button class="bouton bouton-danger" id="supprimer" type="button">Supprimer</button>'}
      <a class="bouton" href="${nouvelle ? "#/fiches" : `#/fiche/${h(id)}`}">Annuler</a>
      <button class="bouton bouton-or" id="enregistrer" type="button">Enregistrer <kbd>Ctrl+S</kbd></button>
    </div>
    <div class="editeur">
      <textarea id="source" spellcheck="false" aria-label="Contenu de la fiche">${h(source)}</textarea>
      <div class="apercu" id="apercu"><div class="secondaire">Aperçu…</div></div>
    </div>`;
  const zone = vue.querySelector("#source");
  const apercu = vue.querySelector("#apercu");
  const champId = vue.querySelector("#identifiant");
  let idModifie = false;
  let modifie = false;
  let v3d = null;

  async function rafraichir() {
    try {
      const f = await api("/fiches/apercu", { methode: "POST", corps: { source: zone.value } });
      if (champId && !idModifie) champId.value = slug(f.nom);
      v3d?.detruire();
      apercu.innerHTML = `
        ${f.avertissements.length ? `<div class="avertissements"><b>À vérifier</b><ul>${f.avertissements.map((a) => `<li>${h(a)}</li>`).join("")}</ul></div>` : ""}
        <div id="apercu-scene"></div>
        ${blocBrochage(f, "apercu")}`;
      const lien = { survol: () => {} };
      const promesse = vue3D(apercu.querySelector("#apercu-scene"), f, { surSurvol: (c) => lien.survol(c) });
      Object.assign(lien, relier(apercu, f, "apercu-schema", promesse));
      v3d = await promesse;
    } catch (err) {
      v3d?.detruire();
      v3d = null;
      apercu.innerHTML = `<div class="erreur-apercu">${h(err.message)}</div>`;
    }
  }
  const rafraichirPlusTard = debounce(rafraichir, 500);
  await rafraichir();

  zone.addEventListener("input", () => { modifie = true; rafraichirPlusTard(); });
  zone.addEventListener("keydown", (e) => {
    if (e.key === "Tab" && !e.shiftKey) {
      e.preventDefault();
      zone.setRangeText("  ", zone.selectionStart, zone.selectionEnd, "end");
      rafraichirPlusTard();
    }
  });
  champId?.addEventListener("input", () => { idModifie = true; });

  async function enregistrer() {
    try {
      let f;
      if (nouvelle) {
        const ident = champId.value.trim() || undefined;
        f = await api("/fiches", { methode: "POST", corps: { source: zone.value, id: ident } });
      } else {
        f = await api(`/fiches/${id}`, { methode: "PUT", corps: { source: zone.value } });
      }
      modifie = false;
      notifier("Fiche enregistrée.");
      location.hash = `#/fiche/${f.id}`;
    } catch (err) { notifier(err.message, true); }
  }
  vue.querySelector("#enregistrer").addEventListener("click", enregistrer);
  const raccourci = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); enregistrer(); }
  };
  document.addEventListener("keydown", raccourci);
  const avantDepart = (e) => { if (modifie) { e.preventDefault(); e.returnValue = ""; } };
  window.addEventListener("beforeunload", avantDepart);
  nettoyage.push(() => {
    document.removeEventListener("keydown", raccourci);
    window.removeEventListener("beforeunload", avantDepart);
    v3d?.detruire();
  });

  vue.querySelector("#supprimer")?.addEventListener("click", async () => {
    if (!confirm(`Supprimer le fichier ${id}.md ? Les articles du stock liés seront conservés.`)) return;
    try {
      await api(`/fiches/${id}`, { methode: "DELETE" });
      modifie = false;
      notifier("Fiche supprimée.");
      location.hash = "#/fiches";
    } catch (err) { notifier(err.message, true); }
  });

  const fichierModele = vue.querySelector("#fichier-modele");
  vue.querySelector("#modele").addEventListener("click", () => fichierModele.click());
  fichierModele.addEventListener("change", async () => {
    const f = fichierModele.files[0];
    if (!f) return;
    const fd = new FormData();
    fd.append("fichier", f);
    try {
      const { chemin } = await api("/modeles", { methode: "POST", corps: fd });
      const ligne = `modele3d: ${chemin}`;
      if (/^modele3d:.*$/m.test(zone.value)) zone.value = zone.value.replace(/^modele3d:.*$/m, ligne);
      else zone.value = zone.value.replace(/^(---\r?\n[\s\S]*?)(\r?\n---)/, `$1\n${ligne}$2`);
      modifie = true;
      notifier(`Modèle enregistré dans fiches/${chemin}.`);
      rafraichir();
    } catch (err) { notifier(err.message, true); }
    fichierModele.value = "";
  });
}

export { TYPES };
