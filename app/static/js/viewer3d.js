// 3D view of a device: model generated from the sheet, or a supplied model (.glb, .gltf, .stl).
// Scene units are millimetres. The sheet's x and y become X and Z; Y points up.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { pinPositions } from "./geometry.js";
import { pinType, escapeHtml as h, isLightColor } from "./common.js";

const TEXTURE_PX_PER_MM = 24;

const materials = {
  gold: () => new THREE.MeshStandardMaterial({ color: 0xd6aa52, metalness: 1, roughness: 0.28 }),
  tin: () => new THREE.MeshStandardMaterial({ color: 0xc6cad2, metalness: 1, roughness: 0.32 }),
  plastic: () => new THREE.MeshStandardMaterial({ color: 0x141518, roughness: 0.75 }),
  invisible: () => new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }),
};

function canvasTexture(widthMm, lengthMm, draw) {
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(16, Math.round(widthMm * TEXTURE_PX_PER_MM));
  canvas.height = Math.max(16, Math.round(lengthMm * TEXTURE_PX_PER_MM));
  const ctx = canvas.getContext("2d");
  ctx.scale(TEXTURE_PX_PER_MM, TEXTURE_PX_PER_MM);
  draw(ctx);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  return texture;
}

function fitText(ctx, text, x, y, maxWidth, maxSize) {
  let size = maxSize;
  ctx.font = `600 ${size}px Inter, system-ui, sans-serif`;
  const measured = ctx.measureText(text).width;
  if (measured > maxWidth) {
    size *= maxWidth / measured;
    ctx.font = `600 ${size}px Inter, system-ui, sans-serif`;
  }
  ctx.fillText(text, x, y);
}

// Box whose top face carries a texture.
function texturedBox(width, height, length, color, topTexture, roughness = 0.6) {
  const side = new THREE.MeshStandardMaterial({ color, roughness });
  const top = new THREE.MeshStandardMaterial({ map: topTexture, roughness });
  return new THREE.Mesh(new THREE.BoxGeometry(width, height, length), [side, side, top, side, side, side]);
}

// ---------- Generated model ----------

function buildBoard(sheet, positions, group, registerPin, X, Z) {
  const pkg = sheet.package;
  const t = pkg.thickness;
  const ink = isLightColor(pkg.color) ? "#1b1d22" : "#f1f3f6";
  const silkscreen = canvasTexture(pkg.width, pkg.length, (ctx) => {
    ctx.fillStyle = pkg.color;
    ctx.fillRect(0, 0, pkg.width, pkg.length);
    ctx.fillStyle = ink;
    ctx.textBaseline = "middle";
    for (const p of positions) {
      const size = Math.min(p.row.pitch * 0.42, 1.05);
      const gap = 1.35;
      ctx.save();
      if (p.side === "left") { ctx.textAlign = "left"; fitText(ctx, p.pin.name, p.x + gap, p.y, 4.5, size); }
      else if (p.side === "right") { ctx.textAlign = "right"; fitText(ctx, p.pin.name, p.x - gap, p.y, 4.5, size); }
      else {
        ctx.translate(p.x, p.y);
        ctx.rotate(-Math.PI / 2);
        ctx.textAlign = p.side === "top" ? "right" : "left";
        fitText(ctx, p.pin.name, p.side === "top" ? -gap : gap, 0, 4.5, size);
      }
      ctx.restore();
    }
    if (pkg.marking) {
      ctx.textAlign = "center";
      fitText(ctx, pkg.marking, pkg.width / 2, pkg.length - 1.8, pkg.width * 0.7, 1.6);
    }
    ctx.strokeStyle = ink;
    ctx.globalAlpha = 0.5;
    ctx.lineWidth = 0.15;
    ctx.strokeRect(0.5, 0.5, pkg.width - 1, pkg.length - 1);
  });
  const pcb = texturedBox(pkg.width, t, pkg.length, pkg.color, silkscreen, 0.55);
  pcb.position.y = t / 2;
  group.add(pcb);

  // Male pin headers soldered underneath.
  for (const p of positions) {
    const metal = materials.gold();
    const pad = new THREE.Mesh(new THREE.CylinderGeometry(0.85, 0.85, 0.06, 24), metal);
    pad.position.set(X(p.x), t + 0.03, Z(p.y));
    const tip = new THREE.Mesh(new THREE.BoxGeometry(0.64, 1.1, 0.64), metal);
    tip.position.set(X(p.x), t + 0.55, Z(p.y));
    const spacer = new THREE.Mesh(new THREE.BoxGeometry(p.row.pitch * 0.98, 2.5, p.row.pitch * 0.98), materials.plastic());
    spacer.position.set(X(p.x), -1.25, Z(p.y));
    const leg = new THREE.Mesh(new THREE.BoxGeometry(0.64, 6, 0.64), metal);
    leg.position.set(X(p.x), -5.5, Z(p.y));
    group.add(pad, tip, spacer, leg);
    registerPin(p, [pad, tip, leg], metal, [2.3, t + 10, 2.3], new THREE.Vector3(X(p.x), (t + 1.1 - 8.5) / 2, Z(p.y)));
  }
}

function buildDip(sheet, positions, group, registerPin, X, Z) {
  const pkg = sheet.package;
  const t = pkg.thickness;
  const bodyWidth = Math.max(2, pkg.width - 1.27);
  const bodyLength = Math.max(2, pkg.length - 0.3);
  const standoff = 0.5;
  const top = canvasTexture(bodyWidth, bodyLength, (ctx) => {
    ctx.fillStyle = pkg.color;
    ctx.fillRect(0, 0, bodyWidth, bodyLength);
    ctx.fillStyle = "#0a0b0d";
    ctx.beginPath(); ctx.arc(bodyWidth / 2, 0, 0.8, 0, Math.PI); ctx.fill();   // notch
    ctx.beginPath(); ctx.arc(1.1, 1.3, 0.45, 0, Math.PI * 2); ctx.fill();     // pin 1 dot
    if (pkg.marking) {
      ctx.fillStyle = "#d5d8de";
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.save(); ctx.translate(bodyWidth / 2, bodyLength / 2);
      if (bodyLength > bodyWidth) ctx.rotate(Math.PI / 2);
      fitText(ctx, pkg.marking, 0, 0, Math.max(bodyWidth, bodyLength) * 0.8, Math.min(bodyWidth, bodyLength) * 0.28);
      ctx.restore();
    }
  });
  const body = texturedBox(bodyWidth, t, bodyLength, pkg.color, top, 0.8);
  body.position.y = standoff + t / 2;
  group.add(body);

  const shoulderY = standoff + t * 0.4;
  for (const p of positions) {
    const metal = materials.tin();
    const direction = p.x < pkg.width / 2 ? -1 : 1;
    const bodyEdge = direction * bodyWidth / 2;
    const px = X(p.x);
    const shoulderLength = Math.max(0.2, Math.abs(px - bodyEdge) + 0.15);
    const shoulder = new THREE.Mesh(new THREE.BoxGeometry(shoulderLength, 0.25, 1.4), metal);
    shoulder.position.set(bodyEdge + direction * shoulderLength / 2, shoulderY, Z(p.y));
    const upper = new THREE.Mesh(new THREE.BoxGeometry(0.25, shoulderY + 0.8, 1.4), metal);
    upper.position.set(px, (shoulderY - 0.8) / 2 + 0.1, Z(p.y));
    const lower = new THREE.Mesh(new THREE.BoxGeometry(0.25, 3, 0.5), metal);
    lower.position.set(px, -2.2, Z(p.y));
    group.add(shoulder, upper, lower);
    registerPin(p, [shoulder, upper, lower], metal, [1.6, t + 5, 2], new THREE.Vector3(px, (standoff + t - 3.7) / 2, Z(p.y)));
  }
}

function buildTo92(sheet, positions, group, registerPin, X) {
  const pkg = sheet.package;
  const radius = pkg.width / 2;
  const height = pkg.thickness;
  // Half cylinder, flat face towards +Z (the bottom of the top view).
  const body = new THREE.Mesh(
    new THREE.CylinderGeometry(radius, radius, height, 40, 1, false, Math.PI / 2, Math.PI),
    new THREE.MeshStandardMaterial({ color: pkg.color, roughness: 0.8, side: THREE.DoubleSide }),
  );
  body.position.y = height / 2;
  const faceTexture = canvasTexture(2 * radius, height, (ctx) => {
    ctx.fillStyle = pkg.color;
    ctx.fillRect(0, 0, 2 * radius, height);
    if (pkg.marking) {
      ctx.fillStyle = "#d5d8de";
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      fitText(ctx, pkg.marking, radius, height * 0.45, 2 * radius * 0.85, 0.9);
    }
  });
  const face = new THREE.Mesh(new THREE.PlaneGeometry(2 * radius, height), new THREE.MeshStandardMaterial({ map: faceTexture, roughness: 0.8 }));
  face.position.set(0, height / 2, 0.001);
  group.add(body, face);
  for (const p of positions) {
    const metal = materials.tin();
    const leg = new THREE.Mesh(new THREE.BoxGeometry(0.45, 12.7, 0.4), metal);
    leg.position.set(X(p.x), -6.35, -radius * 0.35);
    group.add(leg);
    registerPin(p, [leg], metal, [1, 13, 1.2], leg.position.clone());
  }
}

function buildComponents(sheet, group, X, Z) {
  const pkg = sheet.package;
  const baseY = pkg.type === "board" || pkg.type === "module" ? pkg.thickness : 0;
  for (const c of sheet.components || []) {
    let mesh;
    if (c.shape === "cylinder") {
      mesh = new THREE.Mesh(
        new THREE.CylinderGeometry(c.width / 2, c.width / 2, c.height, 32),
        new THREE.MeshStandardMaterial({ color: c.color, roughness: 0.5 }),
      );
    } else {
      const ink = isLightColor(c.color) ? "#24262c" : "#d5d8de";
      const top = canvasTexture(c.width, c.length, (ctx) => {
        ctx.fillStyle = c.color;
        ctx.fillRect(0, 0, c.width, c.length);
        if (c.label) {
          const vertical = c.length > c.width * 1.6;
          ctx.fillStyle = ink;
          ctx.textAlign = "center"; ctx.textBaseline = "middle";
          ctx.save(); ctx.translate(c.width / 2, c.length / 2);
          if (vertical) ctx.rotate(Math.PI / 2);
          fitText(ctx, c.label, 0, 0, (vertical ? c.length : c.width) * 0.85, Math.min(c.width, c.length) * 0.22);
          ctx.restore();
        }
      });
      const metallic = isLightColor(c.color) && !c.label; // connectors, shields
      mesh = texturedBox(c.width, c.height, c.length, c.color, top, metallic ? 0.3 : 0.6);
      if (metallic) mesh.material.forEach((m) => { m.metalness = 0.8; });
    }
    mesh.position.set(X(c.x), baseY + c.height / 2, Z(c.y));
    group.add(mesh);
  }
}

function buildDevice(sheet) {
  const pkg = sheet.package;
  const group = new THREE.Group();
  const pins = new Map();
  const positions = pinPositions(sheet);
  const X = (x) => x - pkg.width / 2;
  const Z = (y) => y - pkg.length / 2;

  // Each pin gets an invisible, larger box to make pointer picking easy.
  const registerPin = (p, meshes, material, hitSize, center) => {
    const hitBox = new THREE.Mesh(new THREE.BoxGeometry(...hitSize), materials.invisible());
    hitBox.position.copy(center);
    hitBox.userData.key = p.key;
    group.add(hitBox);
    pins.set(p.key, { ...p, meshes, material, hitBox, center: center.clone() });
  };

  if (pkg.type === "dip") buildDip(sheet, positions, group, registerPin, X, Z);
  else if (pkg.type === "to92") buildTo92(sheet, positions, group, registerPin, X);
  else buildBoard(sheet, positions, group, registerPin, X, Z);
  buildComponents(sheet, group, X, Z);
  return { group, pins };
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
      ${sheet.model3d ? '<button class="btn" data-action="model" type="button">Modèle fourni</button>' : ""}
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
  renderer.toneMappingExposure = 1.1;
  container.prepend(renderer.domElement);

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.add(new THREE.HemisphereLight(0xdfe7ff, 0x1a1f2b, 0.8));
  const sun = new THREE.DirectionalLight(0xffffff, 1.6);
  sun.position.set(40, 80, 50);
  scene.add(sun);

  const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 5000);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;

  const { group, pins } = buildDevice(sheet);
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

  let activeObject = group;
  let suppliedModel = null;

  function frame(direction = new THREE.Vector3(0.45, 0.85, 1)) {
    const box = new THREE.Box3().setFromObject(activeObject);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3()).length();
    const distance = size / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))) * 0.85;
    camera.position.copy(center).add(direction.clone().normalize().multiplyScalar(distance));
    camera.near = distance / 100;
    camera.far = distance * 100;
    camera.updateProjectionMatrix();
    controls.target.copy(center);
    controls.update();
    grid.position.y = box.min.y - 0.05;
  }

  function resize() {
    const { clientWidth: width, clientHeight: height } = container;
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }
  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(container);
  resize();
  frame();

  // Highlighting: hovered pin (strong) and pins selected by type (soft).
  let hoveredKey = null;
  let selection = null;
  function applyHighlight() {
    for (const [key, p] of pins) {
      const color = new THREE.Color(pinType(p.pin.type).color);
      if (key === hoveredKey) {
        p.material.emissive.copy(color); p.material.emissiveIntensity = 1.4;
      } else if (selection && selection.has(key)) {
        p.material.emissive.copy(color); p.material.emissiveIntensity = 0.8;
      } else {
        p.material.emissive.setHex(0); p.material.emissiveIntensity = 0;
      }
      const s = key === hoveredKey ? 1.35 : 1;
      p.meshes.forEach((m) => m.scale.set(s, 1, s));
    }
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
    if (activeObject !== group) return null;
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

  async function toggleSuppliedModel(button) {
    if (activeObject === group) {
      button.disabled = true;
      try {
        suppliedModel = suppliedModel || await loadModel(sheet.model3d);
        scene.add(suppliedModel);
        group.visible = false;
        labels.visible = false;
        activeObject = suppliedModel;
        button.textContent = "Modèle généré";
        setHovered(null);
      } catch (err) {
        info.hidden = false;
        info.textContent = `Modèle 3D illisible : ${err.message}`;
      }
      button.disabled = false;
    } else {
      scene.remove(suppliedModel);
      group.visible = true;
      activeObject = group;
      button.textContent = "Modèle fourni";
    }
    frame();
  }

  container.querySelector(".scene-tools").addEventListener("click", (e) => {
    const button = e.target.closest("button[data-action]");
    if (!button) return;
    switch (button.dataset.action) {
      case "labels":
        labels.visible = !labels.visible;
        button.classList.toggle("active", labels.visible);
        break;
      case "top": frame(new THREE.Vector3(0, 1, 0.0001)); break;
      case "bottom": frame(new THREE.Vector3(0, -1, 0.0001)); break;
      case "front": frame(new THREE.Vector3(0, 0.15, 1)); break;
      case "reset": frame(); break;
      case "model": toggleSuppliedModel(button); break;
    }
  });

  let running = true;
  (function loop() {
    if (!running) return;
    controls.update();
    renderer.render(scene, camera);
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

async function loadModel(path) {
  const url = `api/models/${path.split("/").map(encodeURIComponent).join("/")}`;
  let object;
  if (/\.stl$/i.test(path)) {
    const { STLLoader } = await import("three/addons/loaders/STLLoader.js");
    const geometry = await new STLLoader().loadAsync(url);
    geometry.computeVertexNormals();
    object = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color: 0x9aa3b5, roughness: 0.5, metalness: 0.2 }));
    object.rotation.x = -Math.PI / 2; // STL files are usually Z-up
  } else {
    const { GLTFLoader } = await import("three/addons/loaders/GLTFLoader.js");
    object = (await new GLTFLoader().loadAsync(url)).scene;
  }
  // Center the model horizontally and rest it on the grid.
  const wrapper = new THREE.Group();
  wrapper.add(object);
  const box = new THREE.Box3().setFromObject(wrapper);
  const center = box.getCenter(new THREE.Vector3());
  object.position.sub(new THREE.Vector3(center.x, box.min.y, center.z));
  return wrapper;
}
