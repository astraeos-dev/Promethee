// 3D view of a device. The model itself, sheets/models/<id>.glb, is built from the sheet by
// tools/build_models.py (board, plated holes, silkscreen, solder joints, real parts); this view
// adds what makes it interactive: pin markers and picking, labels and camera presets.
// Scene units are millimetres. The sheet's x and y become X and Z; Y points up.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { pinPositions } from "./geometry.js";
import { pinType, escapeHtml as h } from "./common.js";

// ---------- Pins ----------

// Each pin gets an invisible box that is easy to point at, and a glowing marker shown
// when the pin is hovered or selected.
function buildPins(sheet) {
  const pkg = sheet.package;
  const onBoard = pkg.type === "board" || pkg.type === "module";
  const group = new THREE.Group();
  const pins = new Map();
  for (const p of pinPositions(sheet)) {
    const x = p.x - pkg.width / 2;
    const z = p.y - pkg.length / 2;
    let hitSize, hitY, marker;
    const glow = new THREE.MeshBasicMaterial({ color: pinType(p.pin.type).color, transparent: true, opacity: 0.85, depthWrite: false });
    if (onBoard) {
      // Header pin: the tail and its solder joint above the board, the pin below.
      hitSize = [2.3, pkg.thickness + 10, 2.3];
      hitY = (pkg.thickness + 1.1 - 8.5) / 2;
      marker = new THREE.Mesh(new THREE.CylinderGeometry(1.05, 1.05, 2.2, 28), glow);
      marker.position.set(x, pkg.thickness + 1.1, z);
    } else if (pkg.type === "dip") {
      hitSize = [1.6, pkg.thickness + 5, 2];
      hitY = (pkg.thickness - 3.3) / 2;
      marker = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.55, 3.4, 20), glow);
      marker.position.set(x, -1.7, z);
    } else {
      // TO-92: long leads under the body.
      hitSize = [1, 14, 1.2];
      hitY = -6.5;
      marker = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 4, 20), glow);
      marker.position.set(x, -5, z);
    }
    const hitBox = new THREE.Mesh(new THREE.BoxGeometry(...hitSize),
      new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }));
    hitBox.position.set(x, hitY, z);
    hitBox.userData.key = p.key;
    marker.visible = false;
    marker.renderOrder = 5;
    group.add(hitBox, marker);
    pins.set(p.key, { ...p, hitBox, marker, center: new THREE.Vector3(x, hitY, z) });
  }
  return { group, pins };
}

function loadDeviceModel(sheet) {
  if (!sheet.model) return Promise.reject(new Error("Modèle 3D non disponible pour cette fiche."));
  const url = `api/${sheet.model.split("/").map(encodeURIComponent).join("/")}`;
  return new GLTFLoader().loadAsync(url).then((gltf) => gltf.scene);
}

// ---------- Labels ----------

function labelSprite(text, color) {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  const fontSize = 44;
  ctx.font = `600 ${fontSize}px Inter, system-ui, sans-serif`;
  const width = Math.ceil(ctx.measureText(text).width) + 36;
  canvas.width = width;
  canvas.height = fontSize + 24;
  ctx.font = `600 ${fontSize}px Inter, system-ui, sans-serif`;
  ctx.fillStyle = "rgba(11,15,23,0.92)";
  ctx.strokeStyle = color;
  ctx.lineWidth = 5;
  ctx.beginPath(); ctx.roundRect(3, 3, width - 6, canvas.height - 6, 16); ctx.fill(); ctx.stroke();
  ctx.fillStyle = "#e8ecf2"; ctx.textBaseline = "middle"; ctx.textAlign = "center";
  ctx.fillText(text, width / 2, canvas.height / 2 + 2);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, depthTest: false }));
  const heightMm = 1.5;
  sprite.scale.set(heightMm * width / canvas.height, heightMm, 1);
  sprite.renderOrder = 10;
  return sprite;
}

// ---------- Viewer ----------

const SIDE_OFFSETS = { left: [-1, 0], right: [1, 0], top: [0, -1], bottom: [0, 1] };

export function createViewer3D(container, sheet, { onHover = () => {} } = {}) {
  container.classList.add("scene");
  container.innerHTML = `
    <div class="scene-tools">
      <button class="btn" data-action="labels" type="button">Étiquettes</button>
      <button class="btn" data-action="top" type="button">Dessus</button>
      <button class="btn" data-action="front" type="button">Face</button>
      <button class="btn" data-action="bottom" type="button">Dessous</button>
      <button class="btn" data-action="reset" type="button">Recentrer</button>
    </div>
    <div class="scene-info" hidden></div>
    <div class="scene-help">Glisser : tourner · molette : zoom · clic droit : déplacer</div>`;
  const info = container.querySelector(".scene-info");

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  } catch {
    container.insertAdjacentHTML("beforeend", '<div class="scene-loading">La vue 3D nécessite WebGL, indisponible dans ce navigateur.</div>');
    return { hover() {}, highlight() {}, dispose() {} };
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  container.prepend(renderer.domElement);

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  // Soft studio light: the environment gives metals their reflections, without washing out
  // dark solder masks and plastic packages; two lights add highlights and relief.
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.45;
  scene.add(new THREE.HemisphereLight(0xdfe7ff, 0x1a1f2b, 0.5));
  const sun = new THREE.DirectionalLight(0xffffff, 2.2);
  sun.position.set(40, 80, 50);
  const fill = new THREE.DirectionalLight(0xbcd0ff, 0.6);
  fill.position.set(-60, 30, -40);
  scene.add(sun, fill);

  let running = true;
  // Render on demand: only when the camera moves or something changes, not 60 times a second.
  let needsRender = true;
  const invalidate = () => { needsRender = true; };
  const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 5000);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;

  const { group, pins } = buildPins(sheet);
  scene.add(group);
  const labels = new THREE.Group();
  labels.visible = false;
  scene.add(labels);
  const isTo92 = sheet.package.type === "to92";
  for (const p of pins.values()) {
    const sprite = labelSprite(p.pin.name, pinType(p.pin.type).color);
    const [dx, dz] = SIDE_OFFSETS[p.side];
    const offset = isTo92 ? 0 : sprite.scale.x / 2 + 1.6;
    sprite.position.set(p.center.x + dx * offset, isTo92 ? -13.5 : sheet.package.thickness + 2.2, p.center.z + dz * offset);
    labels.add(sprite);
  }
  const grid = new THREE.GridHelper(400, 160, 0x2a3550, 0x1a2234);
  grid.material.transparent = true;
  grid.material.opacity = 0.45;
  scene.add(grid);

  function frame(direction = new THREE.Vector3(0.45, 0.85, 1)) {
    const box = new THREE.Box3().setFromObject(group);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3()).length();
    const distance = size / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))) * 1.0;
    camera.position.copy(center).add(direction.clone().normalize().multiplyScalar(distance));
    camera.near = distance / 100;
    camera.far = distance * 100;
    camera.updateProjectionMatrix();
    controls.target.copy(center);
    controls.update();
    grid.position.y = box.min.y - 0.05;
    invalidate();
  }

  function resize() {
    const { clientWidth: width, clientHeight: height } = container;
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    invalidate();
  }
  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(container);
  resize();
  frame();
  info.hidden = false;
  info.textContent = "Chargement du modèle 3D…";
  loadDeviceModel(sheet).then((model) => {
    if (!running) return;
    group.add(model);
    info.hidden = true;
    frame();
  }).catch((err) => {
    info.hidden = false;
    info.textContent = err.message.startsWith("Modèle") ? err.message : `Modèle 3D illisible : ${err.message}`;
  });

  // Highlighting: hovered pin (strong) and pins selected by type (soft).
  let hoveredKey = null;
  let selection = null;
  function applyHighlight() {
    for (const [key, p] of pins) {
      const hovered = key === hoveredKey;
      const selected = Boolean(selection && selection.has(key));
      p.marker.visible = hovered || selected;
      p.marker.material.opacity = hovered ? 0.85 : 0.5;
    }
    invalidate();
  }
  function showInfo(key) {
    const p = pins.get(key);
    if (!p) { info.hidden = true; return; }
    const type = pinType(p.pin.type);
    info.hidden = false;
    info.innerHTML = `<b><span class="dot" style="background:${type.color}"></span> ${h(p.pin.name)}</b>
      <span class="muted"> · broche ${h(p.pin.n)} · ${h(type.label)}</span>
      ${p.pin.functions.length ? `<div class="muted">${p.pin.functions.map(h).join(", ")}</div>` : ""}
      ${p.pin.description ? `<div>${h(p.pin.description)}</div>` : ""}`;
  }

  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  const hitBoxes = [...pins.values()].map((p) => p.hitBox);
  function pickPin(event) {
    const rect = renderer.domElement.getBoundingClientRect();
    pointer.set(((event.clientX - rect.left) / rect.width) * 2 - 1, -((event.clientY - rect.top) / rect.height) * 2 + 1);
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(hitBoxes, false)[0];
    return hit ? hit.object.userData.key : null;
  }
  function setHovered(key) {
    if (key === hoveredKey) return;
    hoveredKey = key;
    applyHighlight();
    showInfo(key);
    renderer.domElement.style.cursor = key ? "pointer" : "";
    onHover(key);
  }
  renderer.domElement.addEventListener("pointermove", (e) => setHovered(pickPin(e)));
  renderer.domElement.addEventListener("pointerdown", (e) => { if (e.pointerType !== "mouse") setHovered(pickPin(e)); });
  renderer.domElement.addEventListener("pointerleave", () => setHovered(null));

  container.querySelector(".scene-tools").addEventListener("click", (e) => {
    const button = e.target.closest("button[data-action]");
    if (!button) return;
    switch (button.dataset.action) {
      case "labels":
        labels.visible = !labels.visible;
        button.classList.toggle("active", labels.visible);
        invalidate();
        break;
      case "top": frame(new THREE.Vector3(0, 1, 0.0001)); break;
      case "bottom": frame(new THREE.Vector3(0, -1, 0.0001)); break;
      case "front": frame(new THREE.Vector3(0, 0.15, 1)); break;
      case "reset": frame(); break;
    }
  });

  controls.addEventListener("change", invalidate);
  (function loop() {
    if (!running) return;
    // update() also returns true while the damped camera is still gliding.
    if (controls.update() || needsRender) {
      needsRender = false;
      renderer.render(scene, camera);
    }
    requestAnimationFrame(loop);
  })();

  return {
    hover(key) { hoveredKey = key; applyHighlight(); showInfo(key); },
    highlight(keys) { selection = keys; applyHighlight(); },
    dispose() {
      if (!running) return;
      running = false;
      resizeObserver.disconnect();
      controls.dispose();
      scene.traverse((object) => {
        object.geometry?.dispose();
        const list = Array.isArray(object.material) ? object.material : object.material ? [object.material] : [];
        list.forEach((m) => { m.map?.dispose(); m.dispose(); });
      });
      pmrem.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
    },
  };
}
