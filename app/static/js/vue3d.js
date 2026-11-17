// Vue 3D d'un appareil : modèle généré à partir de la fiche, ou modèle fourni (.glb, .gltf, .stl).
// Unités de la scène : le millimètre. x et y de la fiche deviennent X et Z ; Y monte.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { positionsBroches } from "./geometrie.js";
import { type, h } from "./commun.js";

const PX_MM = 24; // résolution des textures dessinées (pixels par millimètre)

const mat = {
  or: () => new THREE.MeshStandardMaterial({ color: 0xd6aa52, metalness: 1, roughness: 0.28 }),
  etain: () => new THREE.MeshStandardMaterial({ color: 0xc6cad2, metalness: 1, roughness: 0.32 }),
  plastique: () => new THREE.MeshStandardMaterial({ color: 0x141518, roughness: 0.75 }),
  invisible: () => new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }),
};

function couleurClaire(hex) {
  const c = new THREE.Color(hex);
  return (0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b) > 0.45;
}

function texture(largeurMm, longueurMm, dessiner) {
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(16, Math.round(largeurMm * PX_MM));
  canvas.height = Math.max(16, Math.round(longueurMm * PX_MM));
  const ctx = canvas.getContext("2d");
  ctx.scale(PX_MM, PX_MM);
  dessiner(ctx);
  const t = new THREE.CanvasTexture(canvas);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

function texteAjuste(ctx, texte, x, y, largeurMax, tailleMax) {
  let taille = tailleMax;
  ctx.font = `600 ${taille}px Inter, system-ui, sans-serif`;
  const mesure = ctx.measureText(texte).width;
  if (mesure > largeurMax) {
    taille *= largeurMax / mesure;
    ctx.font = `600 ${taille}px Inter, system-ui, sans-serif`;
  }
  ctx.fillText(texte, x, y);
}

// Boîte dont la face du dessus porte une texture.
function boiteTexturee(l, ep, L, couleur, dessus, rugosite = 0.6) {
  const cote = new THREE.MeshStandardMaterial({ color: couleur, roughness: rugosite });
  const haut = new THREE.MeshStandardMaterial({ map: dessus, roughness: rugosite });
  return new THREE.Mesh(new THREE.BoxGeometry(l, ep, L), [cote, cote, haut, cote, cote, cote]);
}

// ---------- Construction du modèle généré ----------

function construire(fiche) {
  const b = fiche.boitier;
  const groupe = new THREE.Group();
  const broches = new Map();
  const positions = positionsBroches(fiche);
  const X = (x) => x - b.largeur / 2;
  const Z = (y) => y - b.longueur / 2;

  const enregistrer = (p, meshes, materiau, boite, centre) => {
    const zone = new THREE.Mesh(new THREE.BoxGeometry(...boite), mat.invisible());
    zone.position.copy(centre);
    zone.userData.cle = p.cle;
    groupe.add(zone);
    broches.set(p.cle, { ...p, meshes, materiau, zone, centre: centre.clone() });
  };

  if (b.type === "carte" || b.type === "module") {
    const ep = b.epaisseur;
    const encre = couleurClaire(b.couleur) ? "#1b1d22" : "#f1f3f6";
    const dessus = texture(b.largeur, b.longueur, (ctx) => {
      ctx.fillStyle = b.couleur;
      ctx.fillRect(0, 0, b.largeur, b.longueur);
      ctx.fillStyle = encre;
      ctx.textBaseline = "middle";
      for (const p of positions) {
        const taille = Math.min(p.rangee.pas * 0.42, 1.05);
        const ecart = 1.35;
        ctx.save();
        if (p.cote === "gauche") { ctx.textAlign = "left"; texteAjuste(ctx, p.broche.nom, p.x + ecart, p.y, 4.5, taille); }
        else if (p.cote === "droite") { ctx.textAlign = "right"; texteAjuste(ctx, p.broche.nom, p.x - ecart, p.y, 4.5, taille); }
        else {
          ctx.translate(p.x, p.y);
          ctx.rotate(-Math.PI / 2);
          ctx.textAlign = p.cote === "haut" ? "right" : "left";
          texteAjuste(ctx, p.broche.nom, p.cote === "haut" ? -ecart : ecart, 0, 4.5, taille);
        }
        ctx.restore();
      }
      if (b.marquage) {
        ctx.textAlign = "center";
        texteAjuste(ctx, b.marquage, b.largeur / 2, b.longueur - 1.8, b.largeur * 0.7, 1.6);
      }
      ctx.strokeStyle = encre;
      ctx.globalAlpha = 0.5;
      ctx.lineWidth = 0.15;
      ctx.strokeRect(0.5, 0.5, b.largeur - 1, b.longueur - 1);
    });
    const pcb = boiteTexturee(b.largeur, ep, b.longueur, b.couleur, dessus, 0.55);
    pcb.position.y = ep / 2;
    groupe.add(pcb);

    for (const p of positions) {
      const m = mat.or();
      const pastille = new THREE.Mesh(new THREE.CylinderGeometry(0.85, 0.85, 0.06, 24), m);
      pastille.position.set(X(p.x), ep + 0.03, Z(p.y));
      const tete = new THREE.Mesh(new THREE.BoxGeometry(0.64, 1.1, 0.64), m);
      tete.position.set(X(p.x), ep + 0.55, Z(p.y));
      const corps = new THREE.Mesh(new THREE.BoxGeometry(p.rangee.pas * 0.98, 2.5, p.rangee.pas * 0.98), mat.plastique());
      corps.position.set(X(p.x), -1.25, Z(p.y));
      const patte = new THREE.Mesh(new THREE.BoxGeometry(0.64, 6, 0.64), m);
      patte.position.set(X(p.x), -5.5, Z(p.y));
      groupe.add(pastille, tete, corps, patte);
      enregistrer(p, [pastille, tete, patte], m, [2.3, ep + 10, 2.3], new THREE.Vector3(X(p.x), (ep + 1.1 - 8.5) / 2, Z(p.y)));
    }
  } else if (b.type === "dip") {
    const ep = b.epaisseur;
    const lc = Math.max(2, b.largeur - 1.27);
    const Lc = Math.max(2, b.longueur - 0.3);
    const hc = 0.5;
    const dessus = texture(lc, Lc, (ctx) => {
      ctx.fillStyle = b.couleur;
      ctx.fillRect(0, 0, lc, Lc);
      ctx.fillStyle = "#0a0b0d";
      ctx.beginPath(); ctx.arc(lc / 2, 0, 0.8, 0, Math.PI); ctx.fill();
      ctx.beginPath(); ctx.arc(1.1, 1.3, 0.45, 0, Math.PI * 2); ctx.fill();
      if (b.marquage) {
        ctx.fillStyle = "#d5d8de";
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.save(); ctx.translate(lc / 2, Lc / 2);
        if (Lc > lc) ctx.rotate(Math.PI / 2);
        texteAjuste(ctx, b.marquage, 0, 0, Math.max(lc, Lc) * 0.8, Math.min(lc, Lc) * 0.28);
        ctx.restore();
      }
    });
    const corps = boiteTexturee(lc, ep, Lc, b.couleur, dessus, 0.8);
    corps.position.y = hc + ep / 2;
    groupe.add(corps);
    const yEpaule = hc + ep * 0.4;
    for (const p of positions) {
      const m = mat.etain();
      const sens = p.x < b.largeur / 2 ? -1 : 1;
      const bord = sens * lc / 2;
      const xp = X(p.x);
      const longEpaule = Math.max(0.2, Math.abs(xp - bord) + 0.15);
      const epaule = new THREE.Mesh(new THREE.BoxGeometry(longEpaule, 0.25, 1.4), m);
      epaule.position.set(bord + sens * longEpaule / 2, yEpaule, Z(p.y));
      const haut = new THREE.Mesh(new THREE.BoxGeometry(0.25, yEpaule + 0.8, 1.4), m);
      haut.position.set(xp, (yEpaule - 0.8) / 2 + 0.1, Z(p.y));
      const bas = new THREE.Mesh(new THREE.BoxGeometry(0.25, 3, 0.5), m);
      bas.position.set(xp, -2.2, Z(p.y));
      groupe.add(epaule, haut, bas);
      enregistrer(p, [epaule, haut, bas], m, [1.6, ep + 5, 2], new THREE.Vector3(xp, (hc + ep - 3.7) / 2, Z(p.y)));
    }
  } else if (b.type === "to92") {
    const R = b.largeur / 2;
    const H = b.epaisseur;
    const couleur = b.couleur;
    const corps = new THREE.Mesh(
      new THREE.CylinderGeometry(R, R, H, 40, 1, false, Math.PI / 2, Math.PI),
      new THREE.MeshStandardMaterial({ color: couleur, roughness: 0.8, side: THREE.DoubleSide }),
    );
    corps.position.y = H / 2;
    const face = texture(2 * R, H, (ctx) => {
      ctx.fillStyle = couleur;
      ctx.fillRect(0, 0, 2 * R, H);
      if (b.marquage) {
        ctx.fillStyle = "#d5d8de";
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        texteAjuste(ctx, b.marquage, R, H * 0.45, 2 * R * 0.85, 0.9);
      }
    });
    const plat = new THREE.Mesh(new THREE.PlaneGeometry(2 * R, H), new THREE.MeshStandardMaterial({ map: face, roughness: 0.8 }));
    plat.position.set(0, H / 2, 0.001);
    groupe.add(corps, plat);
    for (const p of positions) {
      const m = mat.etain();
      const patte = new THREE.Mesh(new THREE.BoxGeometry(0.45, 12.7, 0.4), m);
      patte.position.set(X(p.x), -6.35, -R * 0.35);
      groupe.add(patte);
      enregistrer(p, [patte], m, [1, 13, 1.2], new THREE.Vector3(X(p.x), -6.35, -R * 0.35));
    }
  }

  // Composants posés sur la carte.
  const dessusCarte = b.type === "carte" || b.type === "module" ? b.epaisseur : 0;
  for (const c of fiche.composants || []) {
    let mesh;
    if (c.forme === "cylindre") {
      mesh = new THREE.Mesh(
        new THREE.CylinderGeometry(c.largeur / 2, c.largeur / 2, c.hauteur, 32),
        new THREE.MeshStandardMaterial({ color: c.couleur, roughness: 0.5 }),
      );
    } else {
      const encre = couleurClaire(c.couleur) ? "#24262c" : "#d5d8de";
      const dessus = texture(c.largeur, c.longueur, (ctx) => {
        ctx.fillStyle = c.couleur;
        ctx.fillRect(0, 0, c.largeur, c.longueur);
        if (c.texte) {
          ctx.fillStyle = encre;
          ctx.textAlign = "center"; ctx.textBaseline = "middle";
          ctx.save(); ctx.translate(c.largeur / 2, c.longueur / 2);
          if (c.longueur > c.largeur * 1.6) ctx.rotate(Math.PI / 2);
          const l = Math.max(c.largeur, c.longueur) > c.largeur * 1.6 ? c.longueur : c.largeur;
          texteAjuste(ctx, c.texte, 0, 0, l * 0.85, Math.min(c.largeur, c.longueur) * 0.22);
          ctx.restore();
        }
      });
      const metal = couleurClaire(c.couleur) && !c.texte;
      mesh = boiteTexturee(c.largeur, c.hauteur, c.longueur, c.couleur, dessus, metal ? 0.3 : 0.6);
      if (metal) mesh.material.forEach((m) => { m.metalness = 0.8; });
    }
    mesh.position.set(X(c.x), dessusCarte + c.hauteur / 2, Z(c.y));
    mesh.userData.composant = c.nom;
    groupe.add(mesh);
  }

  return { groupe, broches };
}

// ---------- Étiquettes ----------

function etiquette(texte, couleur) {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  const taille = 44;
  ctx.font = `600 ${taille}px Inter, system-ui, sans-serif`;
  const l = Math.ceil(ctx.measureText(texte).width) + 36;
  canvas.width = l; canvas.height = taille + 24;
  ctx.font = `600 ${taille}px Inter, system-ui, sans-serif`;
  ctx.fillStyle = "rgba(11,15,23,0.92)";
  ctx.strokeStyle = couleur; ctx.lineWidth = 5;
  ctx.beginPath(); ctx.roundRect(3, 3, l - 6, canvas.height - 6, 16); ctx.fill(); ctx.stroke();
  ctx.fillStyle = "#e8ecf2"; ctx.textBaseline = "middle"; ctx.textAlign = "center";
  ctx.fillText(texte, l / 2, canvas.height / 2 + 2);
  const t = new THREE.CanvasTexture(canvas);
  t.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, depthTest: false }));
  const hauteur = 1.5;
  s.scale.set(hauteur * l / canvas.height, hauteur, 1);
  s.renderOrder = 10;
  return s;
}

// ---------- Vue ----------

export function creerVue3D(conteneur, fiche, { surSurvol = () => {} } = {}) {
  conteneur.classList.add("scene");
  conteneur.innerHTML = `
    <div class="scene-outils">
      <button class="bouton" data-action="etiquettes" type="button">Étiquettes</button>
      <button class="bouton" data-action="dessus" type="button">Dessus</button>
      <button class="bouton" data-action="face" type="button">Face</button>
      <button class="bouton" data-action="dessous" type="button">Dessous</button>
      <button class="bouton" data-action="recentrer" type="button">Recentrer</button>
      ${fiche.modele3d ? '<button class="bouton" data-action="modele" type="button">Modèle fourni</button>' : ""}
    </div>
    <div class="scene-info" hidden></div>
    <div class="scene-aide">Glisser : tourner · molette : zoom · clic droit : déplacer</div>`;
  const info = conteneur.querySelector(".scene-info");

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  } catch {
    conteneur.insertAdjacentHTML("beforeend", '<div class="scene-chargement">La vue 3D nécessite WebGL, indisponible dans ce navigateur.</div>');
    return { survoler() {}, surligner() {}, detruire() {} };
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;
  conteneur.prepend(renderer.domElement);

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.add(new THREE.HemisphereLight(0xdfe7ff, 0x1a1f2b, 0.8));
  const soleil = new THREE.DirectionalLight(0xffffff, 1.6);
  soleil.position.set(40, 80, 50);
  scene.add(soleil);

  const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 5000);
  const controles = new OrbitControls(camera, renderer.domElement);
  controles.enableDamping = true;
  controles.dampingFactor = 0.08;

  const { groupe, broches } = construire(fiche);
  scene.add(groupe);
  const groupeEtiquettes = new THREE.Group();
  groupeEtiquettes.visible = false;
  scene.add(groupeEtiquettes);
  const decalages = { gauche: [-1, 0], droite: [1, 0], haut: [0, -1], bas: [0, 1] };
  for (const p of broches.values()) {
    const s = etiquette(p.broche.nom, type(p.broche.type).couleur);
    const [dx, dz] = decalages[p.cote];
    const hauteur = fiche.boitier.type === "to92" ? -13.5 : fiche.boitier.epaisseur + 2.2;
    const ecart = fiche.boitier.type === "to92" ? 0 : s.scale.x / 2 + 1.6;
    s.position.set(p.centre.x + dx * ecart, hauteur, p.centre.z + dz * ecart);
    groupeEtiquettes.add(s);
  }
  const grille = new THREE.GridHelper(400, 160, 0x2a3550, 0x1a2234);
  grille.material.transparent = true;
  grille.material.opacity = 0.45;
  scene.add(grille);

  let objetActif = groupe;
  let modeleFourni = null;

  function cadrer(direction = new THREE.Vector3(0.45, 0.85, 1)) {
    const boite = new THREE.Box3().setFromObject(objetActif);
    const centre = boite.getCenter(new THREE.Vector3());
    const taille = boite.getSize(new THREE.Vector3()).length();
    const distance = taille / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))) * 0.85;
    camera.position.copy(centre).add(direction.clone().normalize().multiplyScalar(distance));
    camera.near = distance / 100; camera.far = distance * 100;
    camera.updateProjectionMatrix();
    controles.target.copy(centre);
    controles.update();
    grille.position.y = boite.min.y - 0.05;
  }

  function redimensionner() {
    const { clientWidth: l, clientHeight: hh } = conteneur;
    if (!l || !hh) return;
    renderer.setSize(l, hh, false);
    camera.aspect = l / hh;
    camera.updateProjectionMatrix();
  }
  const observateur = new ResizeObserver(redimensionner);
  observateur.observe(conteneur);
  redimensionner();
  cadrer();

  // Surlignage : survol (fort) et sélection par type (doux).
  let cleSurvol = null;
  let selection = null;
  function appliquer() {
    for (const [cle, p] of broches) {
      const couleur = new THREE.Color(type(p.broche.type).couleur);
      if (cle === cleSurvol) {
        p.materiau.emissive.copy(couleur); p.materiau.emissiveIntensity = 1.4;
      } else if (selection && selection.has(cle)) {
        p.materiau.emissive.copy(couleur); p.materiau.emissiveIntensity = 0.8;
      } else {
        p.materiau.emissive.setHex(0); p.materiau.emissiveIntensity = 0;
      }
      const echelle = cle === cleSurvol ? 1.35 : 1;
      p.meshes.forEach((m) => m.scale.set(echelle, 1, echelle));
    }
  }
  function montrerInfo(cle) {
    const p = broches.get(cle);
    if (!p) { info.hidden = true; return; }
    const t = type(p.broche.type);
    info.hidden = false;
    info.innerHTML = `<b><span class="puce" style="background:${t.couleur}"></span> ${h(p.broche.nom)}</b>
      <span class="secondaire"> · broche ${h(p.broche.n)} · ${h(t.libelle)}</span>
      ${p.broche.fonctions.length ? `<div class="secondaire">${p.broche.fonctions.map(h).join(", ")}</div>` : ""}
      ${p.broche.desc ? `<div>${h(p.broche.desc)}</div>` : ""}`;
  }

  const raycaster = new THREE.Raycaster();
  const pointeur = new THREE.Vector2();
  const zones = [...broches.values()].map((p) => p.zone);
  function chercher(evenement) {
    if (objetActif !== groupe) return null;
    const r = renderer.domElement.getBoundingClientRect();
    pointeur.set(((evenement.clientX - r.left) / r.width) * 2 - 1, -((evenement.clientY - r.top) / r.height) * 2 + 1);
    raycaster.setFromCamera(pointeur, camera);
    const touche = raycaster.intersectObjects(zones, false)[0];
    return touche ? touche.object.userData.cle : null;
  }
  function survolInterne(cle) {
    if (cle === cleSurvol) return;
    cleSurvol = cle;
    appliquer();
    montrerInfo(cle);
    renderer.domElement.style.cursor = cle ? "pointer" : "";
    surSurvol(cle);
  }
  renderer.domElement.addEventListener("pointermove", (e) => survolInterne(chercher(e)));
  renderer.domElement.addEventListener("pointerdown", (e) => { if (e.pointerType !== "mouse") survolInterne(chercher(e)); });
  renderer.domElement.addEventListener("pointerleave", () => survolInterne(null));

  conteneur.querySelector(".scene-outils").addEventListener("click", async (e) => {
    const bouton = e.target.closest("button[data-action]");
    if (!bouton) return;
    const action = bouton.dataset.action;
    if (action === "etiquettes") {
      groupeEtiquettes.visible = !groupeEtiquettes.visible;
      bouton.classList.toggle("actif", groupeEtiquettes.visible);
    } else if (action === "dessus") cadrer(new THREE.Vector3(0, 1, 0.0001));
    else if (action === "dessous") cadrer(new THREE.Vector3(0, -1, 0.0001));
    else if (action === "face") cadrer(new THREE.Vector3(0, 0.15, 1));
    else if (action === "recentrer") cadrer();
    else if (action === "modele") {
      if (objetActif === groupe) {
        bouton.disabled = true;
        try {
          modeleFourni = modeleFourni || await chargerModele(fiche.modele3d);
          scene.add(modeleFourni);
          groupe.visible = false; groupeEtiquettes.visible = false;
          objetActif = modeleFourni;
          bouton.textContent = "Modèle généré";
          survolInterne(null);
        } catch (err) {
          info.hidden = false;
          info.textContent = `Modèle 3D illisible : ${err.message}`;
        }
        bouton.disabled = false;
      } else {
        scene.remove(modeleFourni);
        groupe.visible = true;
        objetActif = groupe;
        bouton.textContent = "Modèle fourni";
      }
      cadrer();
    }
  });

  let actif = true;
  (function boucle() {
    if (!actif) return;
    controles.update();
    renderer.render(scene, camera);
    requestAnimationFrame(boucle);
  })();

  return {
    survoler(cle) { cleSurvol = cle; appliquer(); montrerInfo(cle); },
    surligner(cles) { selection = cles; appliquer(); },
    detruire() {
      if (!actif) return;
      actif = false;
      observateur.disconnect();
      controles.dispose();
      scene.traverse((o) => {
        o.geometry?.dispose();
        const ms = Array.isArray(o.material) ? o.material : o.material ? [o.material] : [];
        ms.forEach((m) => { m.map?.dispose(); m.dispose(); });
      });
      pmrem.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
    },
  };
}

async function chargerModele(chemin) {
  const url = `/api/modeles/${chemin.split("/").map(encodeURIComponent).join("/")}`;
  let objet;
  if (/\.stl$/i.test(chemin)) {
    const { STLLoader } = await import("three/addons/loaders/STLLoader.js");
    const geometrie = await new STLLoader().loadAsync(url);
    geometrie.computeVertexNormals();
    objet = new THREE.Mesh(geometrie, new THREE.MeshStandardMaterial({ color: 0x9aa3b5, roughness: 0.5, metalness: 0.2 }));
    objet.rotation.x = -Math.PI / 2; // les STL sont souvent en Z vers le haut
  } else {
    const { GLTFLoader } = await import("three/addons/loaders/GLTFLoader.js");
    objet = (await new GLTFLoader().loadAsync(url)).scene;
  }
  const conteneur = new THREE.Group();
  conteneur.add(objet);
  const boite = new THREE.Box3().setFromObject(conteneur);
  const centre = boite.getCenter(new THREE.Vector3());
  objet.position.sub(new THREE.Vector3(centre.x, boite.min.y, centre.z));
  return conteneur;
}
