"""Build the 3D model of each device sheet.

Two steps, both incremental:

1. Parts. The STEP models listed in tools/parts.yaml (KiCad 3D library) are
   converted to tools/parts/<name>.glb: millimetres, Y up, centred in the
   horizontal plane, board surface at Y = 0. Their sizes are written to
   sheets/models/parts.json for the 2D pinout.
2. Devices. Each sheet's model is built from its description and written to
   sheets/models/<id>.glb: the printed circuit board (outline, plated holes,
   pads, solder mask, silkscreen, solder joints) or the bare package, with
   every part placed on it. Coordinates are the viewer's: X right, Y up,
   Z towards the bottom of the top view, origin at the centre of the board's
   lower face. sheets/models/index.json keeps a fingerprint of each model's
   inputs, so that the tests notice a model that needs rebuilding.

Usage (dev dependencies: pip install -r requirements-dev.txt):
    python tools/build_models.py                    # build what is missing or out of date
    python tools/build_models.py --force            # rebuild everything
    python tools/build_models.py esp32-devkitc-v4   # rebuild one device
"""

from __future__ import annotations

import argparse
import colorsys
import copy
import functools
import json
import math
import sys
import tempfile
import urllib.request
from pathlib import Path

import numpy as np
import trimesh
import yaml
from PIL import Image, ImageDraw, ImageFont, ImageOps
from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union
from trimesh.visual import TextureVisuals
from trimesh.visual.material import PBRMaterial

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.sheets import BOARD_TYPES, Sheet, model_inputs_hash, parse  # noqa: E402

PARTS_MANIFEST = ROOT / "tools" / "parts.yaml"
PARTS_DIR = ROOT / "tools" / "parts"
FONT_PATH = ROOT / "tools" / "fonts" / "DejaVuSans-Bold.ttf"
SHEETS_DIR = ROOT / "sheets"
MODELS_DIR = SHEETS_DIR / "models"

# Bump when the output of the builder changes, so that every model is rebuilt.
BUILDER_VERSION = 6

# KiCad (x right, y up in the footprint view, z out of the board), in metres
# -> viewer (x right, y up out of the board, z down in the top view), in mm.
KICAD_TO_VIEWER = np.array([
    [1000, 0, 0, 0],
    [0, 0, 1000, 0],
    [0, -1000, 0, 0],
    [0, 0, 0, 1],
], dtype=float)

# Printed circuit board, in mm.
PIN_DRILL = 1.0        # hole for a 0.64 mm square header pin
PIN_PAD = 1.7          # pad diameter around it
COPPER = 0.035         # pad thickness
SKIN_GAP = 0.004       # lifts the mask texture off the core faces
SOLDER_HEIGHT = 0.9    # height of a solder joint around a header pin
TEXTURE_PX_PER_MM = 32
LABEL_PX_PER_MM = 48

# name: (sRGB colour, metallic, roughness). glTF stores colour factors in linear light:
# pbr() converts them.
MATERIALS = {
    "tin": ((208, 210, 214), 1.0, 0.30),      # tin-plated pins, shields, HASL pads
    "gold": ((214, 170, 86), 1.0, 0.26),      # ENIG pads, gold-plated contacts
    "solder": ((200, 203, 208), 1.0, 0.20),
    "plastic": ((24, 24, 26), 0.0, 0.78),     # moulded package bodies, matte epoxy
    "fr4": ((176, 166, 130), 0.0, 0.85),      # board core (glass-epoxy), seen on the edges
}
# Flat colours used by the KiCad models (linear values, as converted), mapped to real materials.
KICAD_COLORS = {
    (165, 163, 146): "tin", (164, 163, 146): "tin",
    (181, 129, 54): "gold", (181, 128, 53): "gold",
    (5, 5, 5): "plastic", (6, 6, 6): "plastic",
}


# ---------- Small helpers ----------

def hex_rgb(color: str) -> tuple[int, int, int]:
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def is_light(rgb: tuple[int, int, int]) -> bool:
    return colorsys.rgb_to_hls(*(c / 255 for c in rgb))[1] > 0.6


def srgb_to_linear(rgb) -> list[float]:
    channels = [c / 255 for c in rgb]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]


def pbr(rgb, metallic=0.0, roughness=0.6, texture=None, blend=False, name=None, linear=False) -> PBRMaterial:
    """Material from an sRGB colour (0-255), or from linear values already (linear=True)."""
    factor = [c / 255 for c in rgb] if linear else srgb_to_linear(rgb)
    return PBRMaterial(
        name=name,
        baseColorFactor=[1.0, 1.0, 1.0, 1.0] if texture is not None else [*factor, 1.0],
        baseColorTexture=texture,
        metallicFactor=metallic,
        roughnessFactor=roughness,
        alphaMode="BLEND" if blend else "OPAQUE",
    )


@functools.cache
def named(name: str) -> PBRMaterial:
    rgb, metallic, roughness = MATERIALS[name]
    return pbr(rgb, metallic, roughness, name=name)


def paint(mesh: trimesh.Trimesh, material: PBRMaterial, uv=None) -> trimesh.Trimesh:
    mesh.visual = TextureVisuals(uv=uv, material=material)
    return mesh


def polygons(shape):
    if isinstance(shape, Polygon):
        return [shape] if not shape.is_empty else []
    if isinstance(shape, MultiPolygon):
        return list(shape.geoms)
    return [g for g in getattr(shape, "geoms", []) if isinstance(g, Polygon)]


@functools.cache
def font(size_px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), max(size_px, 6))


class Frame:
    """Sheet coordinates (x right, y down from the top left corner, mm) -> viewer coordinates.

    2D shapes are drawn in the plane (x, -y) and extruded along +z, so that the
    change of frame is a rotation: no mirroring, faces keep their orientation.
    """

    def __init__(self, width: float, length: float):
        self.width, self.length = width, length

    def point(self, x: float, y: float, height: float = 0.0) -> np.ndarray:
        return np.array([x - self.width / 2, height, y - self.length / 2])

    def matrix(self) -> np.ndarray:
        m = np.eye(4)
        m[:3, :3] = [[1, 0, 0], [0, 0, 1], [0, -1, 0]]
        m[:3, 3] = [-self.width / 2, 0, -self.length / 2]
        return m

    def extrude(self, shape, bottom: float, height: float) -> trimesh.Trimesh:
        meshes = [trimesh.creation.extrude_polygon(p, height, engine="earcut") for p in polygons(shape)]
        mesh = trimesh.util.concatenate(meshes)
        mesh.apply_translation([0, 0, bottom])
        mesh.apply_transform(self.matrix())
        return mesh

    def face(self, shape, height: float, facing_up: bool, material: PBRMaterial) -> trimesh.Trimesh:
        """Flat face mapped to a texture covering the whole board."""
        vertices, faces = [], []
        for polygon in polygons(shape):
            v, f = trimesh.creation.triangulate_polygon(polygon, engine="earcut")
            faces.append(f + sum(len(x) for x in vertices))
            vertices.append(v)
        flat = np.vstack(vertices)
        mesh = trimesh.Trimesh(np.column_stack([flat, np.full(len(flat), height)]), np.vstack(faces), process=False)
        if (mesh.face_normals[:, 2].mean() > 0) != facing_up:
            mesh.invert()
        uv = np.column_stack([flat[:, 0] / self.width, 1 + flat[:, 1] / self.length])
        paint(mesh, material, uv)
        mesh.apply_transform(self.matrix())
        return mesh


class Canvas:
    """Texture drawn in millimetres."""

    def __init__(self, width: float, length: float, background, px_per_mm: int = TEXTURE_PX_PER_MM):
        self.ppm = px_per_mm
        mode = "RGBA" if len(background) == 4 else "RGB"
        self.image = Image.new(mode, (round(width * px_per_mm), round(length * px_per_mm)), tuple(background))

    def text(self, text: str, x: float, y: float, size: float, color, anchor: str = "mm",
             rotation: float = 0.0, max_width: float | None = None) -> None:
        px = size * self.ppm
        if max_width and font(round(px)).getlength(text) > max_width * self.ppm:
            px *= max_width * self.ppm / font(round(px)).getlength(text)
        face = font(round(px))
        fill = (*color, 255)
        if not rotation % 360:
            ImageDraw.Draw(self.image).text((x * self.ppm, y * self.ppm), text, fill=fill, font=face, anchor=anchor)
            return
        # Draw on a transparent tile, rotate it, then put its anchor point at (x, y).
        left, top, right, bottom = face.getbbox(text, anchor=anchor)
        tile = Image.new("RGBA", (math.ceil(right - left) + 4, math.ceil(bottom - top) + 4), (0, 0, 0, 0))
        anchor_x, anchor_y = -left + 2, -top + 2
        ImageDraw.Draw(tile).text((anchor_x, anchor_y), text, fill=fill, font=face, anchor=anchor)
        turned = tile.rotate(rotation, expand=True, resample=Image.Resampling.BICUBIC)
        angle = math.radians(rotation)
        dx, dy = anchor_x - tile.width / 2, anchor_y - tile.height / 2
        new_x = turned.width / 2 + dx * math.cos(angle) + dy * math.sin(angle)
        new_y = turned.height / 2 - dx * math.sin(angle) + dy * math.cos(angle)
        position = (round(x * self.ppm - new_x), round(y * self.ppm - new_y))
        self.image.paste(turned, position, turned)


# ---------- Parts (KiCad models) ----------

def load_manifest() -> dict:
    manifest = yaml.safe_load(PARTS_MANIFEST.read_text(encoding="utf-8"))
    parts = {}
    for name, entry in manifest["parts"].items():
        entry = {"step": entry} if isinstance(entry, str) else dict(entry)
        entry["materials"] = {
            tuple(int(c) for c in key.split(",")): value for key, value in (entry.get("materials") or {}).items()
        }
        parts[name] = entry
    manifest["parts"] = parts
    return manifest


def convert_step(step_path: Path, glb_path: Path) -> None:
    import cascadio  # only needed to convert new parts

    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.glb"
        cascadio.step_to_glb(str(step_path), str(raw), 0.01, 0.3)
        scene = trimesh.load(raw, force="scene")
    scene.apply_transform(KICAD_TO_VIEWER)
    (min_x, _, min_z), (max_x, _, max_z) = scene.bounds
    scene.apply_translation([-(min_x + max_x) / 2, 0, -(min_z + max_z) / 2])
    glb_path.write_bytes(scene.export(file_type="glb"))


def convert_parts(manifest: dict, force: bool) -> None:
    base_url = f"{manifest['source']}/{manifest['revision']}"
    PARTS_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for name, entry in manifest["parts"].items():
            target = PARTS_DIR / f"{name}.glb"
            if target.exists() and not force:
                continue
            step = Path(tmp) / f"{name}.step"
            print(f"part {name}: {entry['step']}", flush=True)
            urllib.request.urlretrieve(f"{base_url}/{entry['step']}", step)
            convert_step(step, target)
    sizes = {}
    for glb in sorted(PARTS_DIR.glob("*.glb")):
        (min_x, min_y, min_z), (max_x, max_y, max_z) = trimesh.load(glb, force="scene").bounds
        sizes[glb.stem] = [round(max_x - min_x, 2), round(max_y - min_y, 2), round(max_z - min_z, 2)]
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    (MODELS_DIR / "parts.json").write_text(json.dumps(sizes, indent=1) + "\n", encoding="utf-8")


@functools.cache
def _part_meshes(name: str, remap_items: tuple) -> tuple[trimesh.Trimesh, ...]:
    remap = dict(remap_items)
    meshes = []
    for mesh in trimesh.load(PARTS_DIR / f"{name}.glb", force="scene").dump(concatenate=False):
        rgb = tuple(int(c) for c in mesh.visual.material.baseColorFactor[:3])
        material_name = remap.get(rgb) or KICAD_COLORS.get(rgb)
        paint(mesh, named(material_name) if material_name else pbr(rgb, 0.0, 0.55, linear=True))
        meshes.append(mesh)
    return tuple(meshes)


def part_meshes(part: dict, manifest: dict) -> list[trimesh.Trimesh]:
    """Meshes of a part in its own frame (centred, resting on Y = 0)."""
    if part["model"]:
        entry = manifest["parts"].get(part["model"])
        if entry is None or not (PARTS_DIR / f"{part['model']}.glb").exists():
            raise SystemExit(f"Unknown part model '{part['model']}': add it to tools/parts.yaml.")
        return [m.copy() for m in _part_meshes(part["model"], tuple(sorted(entry["materials"].items())))]
    rgb = hex_rgb(part["color"])
    material = named("tin") if is_light(rgb) and max(rgb) - min(rgb) < 30 else pbr(rgb, 0.0, 0.5)
    if part["shape"] == "cylinder":
        mesh = trimesh.creation.cylinder(radius=part["width"] / 2, height=part["height"], sections=40)
        mesh.apply_transform(trimesh.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0]))
    else:
        mesh = trimesh.creation.box(extents=(part["width"], part["height"], part["length"]))
    mesh.apply_translation([0, part["height"] / 2, 0])
    return [paint(mesh, material)]


def decal(text: str, size_x: float, size_z: float, height: float, color, along_z: bool) -> trimesh.Trimesh:
    """Text printed on the top face of a part (laser marking, ink), centred in its frame."""
    canvas = Canvas(size_x, size_z, (0, 0, 0, 0), LABEL_PX_PER_MM)
    if along_z:  # reads from top to bottom of the top view, like a DIP marking
        canvas.text(text, size_x / 2, size_z / 2, size_x * 0.3, color, rotation=-90, max_width=size_z * 0.85)
    else:
        canvas.text(text, size_x / 2, size_z / 2, size_z * 0.3, color, max_width=size_x * 0.85)
    hx, hz = size_x / 2, size_z / 2
    vertices = [(-hx, height, -hz), (hx, height, -hz), (hx, height, hz), (-hx, height, hz)]
    mesh = trimesh.Trimesh(vertices, [[0, 2, 1], [0, 3, 2]], process=False)
    uv = [(0, 1), (1, 1), (1, 0), (0, 0)]
    return paint(mesh, pbr((255, 255, 255), 0.0, 0.5, texture=canvas.image, blend=True), uv)


def face_decal(text: str, width: float, height: float, center_y: float, face_z: float, color) -> trimesh.Trimesh:
    """Text printed on a face turned towards +Z (the flat face of a TO-92)."""
    canvas = Canvas(width, height, (0, 0, 0, 0), LABEL_PX_PER_MM)
    canvas.text(text, width / 2, height / 2, height * 0.6, color, max_width=width * 0.92)
    hx, hy = width / 2, height / 2
    vertices = [(-hx, center_y + hy, face_z), (hx, center_y + hy, face_z),
                (hx, center_y - hy, face_z), (-hx, center_y - hy, face_z)]
    mesh = trimesh.Trimesh(vertices, [[0, 2, 1], [0, 3, 2]], process=False)
    uv = [(0, 1), (1, 1), (1, 0), (0, 0)]
    return paint(mesh, pbr((255, 255, 255), 0.0, 0.5, texture=canvas.image, blend=True), uv)


def part_matrix(frame: Frame, package: dict, part: dict) -> np.ndarray:
    on_board = package["type"] in BOARD_TYPES
    base = package["thickness"] if on_board and part["side"] == "top" else 0.0
    matrix = trimesh.transformations.translation_matrix(frame.point(part["x"], part["y"], base + part["z"]))
    matrix = matrix @ trimesh.transformations.rotation_matrix(math.radians(part["rotation"]), [0, 1, 0])
    if part["side"] == "bottom":  # mounted under the board: turned over around its length
        matrix = matrix @ trimesh.transformations.rotation_matrix(math.pi, [0, 0, 1])
    return matrix


# ---------- Printed circuit board ----------

def board_outline(package: dict) -> Polygon:
    width, length, radius = package["width"], package["length"], package["corner_radius"]
    if radius <= 0:
        return box(0, -length, width, 0)
    return box(radius, -length + radius, width - radius, -radius).buffer(radius, quad_segs=12)


def board_holes(sheet: Sheet) -> list[dict]:
    """Plated holes of the pins (square pad for pin 1), then the sheet's other holes."""
    holes = [
        {"x": pin["x"], "y": pin["y"], "drill": PIN_DRILL, "pad": PIN_PAD, "square": pin["n"] == "1"}
        for row in sheet.meta["pinout"]["rows"] for pin in row["pins"]
    ]
    return holes + sheet.meta["package"]["holes"]


def pad_shape(hole: dict):
    x, y, pad, drill = hole["x"], -hole["y"], hole["pad"], hole["drill"]
    outer = box(x - pad / 2, y - pad / 2, x + pad / 2, y + pad / 2) if hole["square"] else Point(x, y).buffer(pad / 2, quad_segs=10)
    return outer.difference(Point(x, y).buffer(drill / 2, quad_segs=10))


def silkscreen(sheet: Sheet, side: str) -> Image.Image:
    """Solder mask colour with the silkscreen printed on it, for one face of the board."""
    package = sheet.meta["package"]
    width, length = package["width"], package["length"]
    canvas = Canvas(width, length, hex_rgb(package["color"]))
    ink = hex_rgb(package["silkscreen_color"])
    if side == "top":
        gap = 1.35
        for row in sheet.meta["pinout"]["rows"]:
            size = min(row["pitch"] * 0.42, 1.05)
            for pin in row["pins"]:
                text, x, y = pin["silkscreen"], pin["x"], pin["y"]
                if row["side"] == "left":
                    canvas.text(text, x + gap, y, size, ink, "lm", max_width=4.6)
                elif row["side"] == "right":
                    canvas.text(text, x - gap, y, size, ink, "rm", max_width=4.6)
                elif row["side"] == "top":
                    canvas.text(text, x, y + gap, size, ink, "rm", rotation=90, max_width=4.6)
                else:
                    canvas.text(text, x, y - gap, size, ink, "lm", rotation=90, max_width=4.6)
    for item in package["silkscreen"]:
        if item["side"] != side:
            continue
        x = item["x"] if side == "top" else width - item["x"]
        canvas.text(item["text"], x, item["y"], item["size"], ink, rotation=item["rotation"])
    # The bottom face is seen from below: mirror it so that its text reads correctly.
    return canvas.image if side == "top" else ImageOps.mirror(canvas.image)


def solder_joint(pad_radius: float, pin_radius: float, height: float) -> trimesh.Trimesh:
    """Concave solder fillet around a pin, standing on its pad (revolved profile)."""
    steps = np.linspace(0, 1, 10)
    curve = [(pin_radius + (pad_radius - pin_radius) * (1 - math.sin(t * math.pi / 2)),
              height * (1 - math.cos(t * math.pi / 2))) for t in steps]
    profile = np.array([(0.0, 0.0), *curve, (0.0, height)])
    return trimesh.creation.revolve(profile, sections=28)


def board_meshes(frame: Frame, sheet: Sheet) -> list[trimesh.Trimesh]:
    package = sheet.meta["package"]
    thickness = package["thickness"]
    holes = board_holes(sheet)
    drills = unary_union([Point(h["x"], -h["y"]).buffer(h["drill"] / 2, quad_segs=10) for h in holes])
    board = board_outline(package).difference(drills)

    meshes = [paint(frame.extrude(board, 0, thickness), named("fr4"))]
    for side in ("top", "bottom"):
        material = pbr((255, 255, 255), 0.0, 0.5, texture=silkscreen(sheet, side))
        height = thickness + SKIN_GAP if side == "top" else -SKIN_GAP
        meshes.append(frame.face(board, height, side == "top", material))

    plated = [h for h in holes if h["pad"] > 0]
    if plated:
        finish = named(package["finish"])
        pads = unary_union([pad_shape(h) for h in plated])
        meshes.append(paint(frame.extrude(pads, thickness, COPPER), finish))
        meshes.append(paint(frame.extrude(pads, -COPPER, COPPER), finish))
        barrels = unary_union([
            Point(h["x"], -h["y"]).buffer(h["drill"] / 2 + 0.03, quad_segs=10).difference(
                Point(h["x"], -h["y"]).buffer(h["drill"] / 2, quad_segs=10))
            for h in plated
        ])
        meshes.append(paint(frame.extrude(barrels, 0, thickness), finish))

    # Header pins are soldered on the face opposite to the header's plastic body.
    header_sides = {p["side"] for p in sheet.meta["parts"] if p["model"].startswith("pin-header")}
    pins = [pin for row in sheet.meta["pinout"]["rows"] for pin in row["pins"]]
    if pins and len(header_sides) == 1:
        on_top = header_sides == {"bottom"}
        joint = solder_joint(PIN_PAD / 2 * 0.96, 0.42, SOLDER_HEIGHT)
        if not on_top:
            joint.apply_transform(np.diag([1, 1, -1, 1]))
            joint.invert()
        base = thickness + COPPER if on_top else -COPPER
        joints = []
        for pin in pins:
            placed = joint.copy()
            placed.apply_translation([pin["x"], -pin["y"], base])
            joints.append(placed)
        solder = trimesh.util.concatenate(joints)
        solder.apply_transform(frame.matrix())
        meshes.append(paint(solder, named("solder")))
    return meshes


# ---------- Device ----------

def merge_by_material(meshes: list[trimesh.Trimesh]) -> list[trimesh.Trimesh]:
    """One mesh per material: a few draw calls instead of one per part, for small devices."""
    groups: dict[tuple, tuple[PBRMaterial, list]] = {}
    merged = []
    for mesh in meshes:
        material = mesh.visual.material
        if material.baseColorTexture is not None:  # board faces and printed text keep their UVs
            merged.append(mesh)
            continue
        key = (tuple(material.baseColorFactor), material.metallicFactor, material.roughnessFactor)
        groups.setdefault(key, (material, []))[1].append(mesh)
    for material, items in groups.values():
        geometry = trimesh.util.concatenate([
            trimesh.Trimesh(m.vertices, m.faces, vertex_normals=m.vertex_normals, process=False) for m in items
        ])
        merged.append(paint(geometry, material))
    return merged


def build_device(sheet: Sheet, manifest: dict) -> trimesh.Scene:
    package = sheet.meta["package"]
    frame = Frame(package["width"], package["length"])
    meshes = board_meshes(frame, sheet) if package["type"] in BOARD_TYPES else []

    body_meshes = []
    for index, part in enumerate(sheet.meta["parts"]):
        part_meshes_list = part_meshes(part, manifest)
        (min_x, _, min_z), (max_x, max_y, max_z) = trimesh.util.concatenate(part_meshes_list).bounds
        is_body = index == 0 and package["type"] in {"dip", "to92"}
        label = part["label"] or (package["marking"] if is_body else "")
        ink = (74, 78, 87) if is_light(hex_rgb(part["color"])) else (201, 206, 216)
        if label and package["type"] == "to92" and is_body:
            part_meshes_list.append(face_decal(label, (max_x - min_x) * 0.8, 1.3, max_y * 0.6, max_z + 0.01, ink))
        elif label:
            along_z = is_body and package["type"] == "dip"
            part_meshes_list.append(decal(label, (max_x - min_x) * 0.82, (max_z - min_z) * 0.82, max_y + 0.01, ink, along_z))
        matrix = part_matrix(frame, package, part)
        for mesh in part_meshes_list:
            mesh.apply_transform(matrix)
        meshes.extend(part_meshes_list)
        if is_body:
            body_meshes = part_meshes_list

    # KiCad cuts TO-92 leads at board level: a loose transistor gets its full-length leads.
    if package["type"] == "to92" and body_meshes:
        lead_top = trimesh.util.concatenate(body_meshes).bounds[0][1] + 0.05
        length = 12.7
        leads = []
        for row in sheet.meta["pinout"]["rows"]:
            for pin in row["pins"]:
                lead = trimesh.creation.box(extents=(0.43, length, 0.38))
                lead.apply_translation(frame.point(pin["x"], pin["y"], lead_top - length / 2))
                leads.append(lead)
        meshes.append(paint(trimesh.util.concatenate(leads), named("tin")))

    scene = trimesh.Scene()
    for i, mesh in enumerate(merge_by_material(meshes)):
        scene.add_geometry(mesh, geom_name=f"{sheet.id}-{i}")
    return scene


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the 3D models of the device sheets.")
    parser.add_argument("sheets", nargs="*", help="sheet identifiers (default: all)")
    parser.add_argument("--force", action="store_true", help="rebuild even when up to date")
    args = parser.parse_args()

    manifest = load_manifest()
    convert_parts(manifest, force=False)
    index_path = MODELS_DIR / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    for path in sorted(SHEETS_DIR.glob("*.md")):
        if path.name.startswith("_") or (args.sheets and path.stem not in args.sheets):
            continue
        sheet = parse(path.stem, path.read_text(encoding="utf-8"))
        fingerprint = {"inputs": model_inputs_hash(sheet.meta), "builder": BUILDER_VERSION}
        target = MODELS_DIR / f"{sheet.id}.glb"
        if target.exists() and index.get(sheet.id) == fingerprint and not args.force:
            continue
        target.write_bytes(build_device(sheet, manifest).export(file_type="glb"))
        index[sheet.id] = fingerprint
        print(f"{sheet.id}: {target.relative_to(ROOT)} ({target.stat().st_size // 1024} KiB)", flush=True)
    index = {k: index[k] for k in sorted(index) if (SHEETS_DIR / f"{k}.md").exists()}
    index_path.write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
