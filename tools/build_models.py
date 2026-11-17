"""Download the STEP models listed in tools/models.yaml and convert them to GLB.

The output files go to sheets/models/<name>.glb, normalised for the viewer,
with their sizes in sheets/models/index.json:
- millimetres, Y up (KiCad models are in metres once converted, Z up);
- centred on their bounding box in the horizontal plane;
- the board surface (KiCad z = 0) stays at Y = 0.

Usage (needs the dev dependencies: pip install -r requirements-dev.txt):
    python tools/build_models.py            # convert missing models
    python tools/build_models.py --force    # convert everything again
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import urllib.request
from pathlib import Path

import cascadio
import numpy as np
import trimesh
import yaml

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "tools" / "models.yaml"
OUTPUT_DIR = ROOT / "sheets" / "models"

# KiCad (x right, y up in the footprint view, z out of the board), in metres
# -> viewer (x right, y up out of the board, z down in the top view), in mm.
KICAD_TO_VIEWER = np.array([
    [1000, 0, 0, 0],
    [0, 0, 1000, 0],
    [0, -1000, 0, 0],
    [0, 0, 0, 1],
], dtype=float)


def convert(step_path: Path, glb_path: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.glb"
        cascadio.step_to_glb(str(step_path), str(raw), 0.01, 0.3)
        scene = trimesh.load(raw, force="scene")
    scene.apply_transform(KICAD_TO_VIEWER)
    (min_x, _, min_z), (max_x, _, max_z) = scene.bounds
    scene.apply_translation([-(min_x + max_x) / 2, 0, -(min_z + max_z) / 2])
    glb_path.write_bytes(scene.export(file_type="glb"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--force", action="store_true", help="convert models that already exist")
    args = parser.parse_args()

    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    base_url = f"{manifest['source']}/{manifest['revision']}"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for name, source_path in manifest["models"].items():
            target = OUTPUT_DIR / f"{name}.glb"
            if target.exists() and not args.force:
                continue
            step = Path(tmp) / f"{name}.step"
            print(f"{name}: {source_path}", flush=True)
            urllib.request.urlretrieve(f"{base_url}/{source_path}", step)
            convert(step, target)
            print(f"  -> {target.relative_to(ROOT)} ({target.stat().st_size // 1024} KiB)")
    write_index()
    return 0


def write_index() -> None:
    """Record each model's size so that the 2D pinout can draw parts without loading them."""
    sizes = {}
    for glb in sorted(OUTPUT_DIR.glob("*.glb")):
        (min_x, min_y, min_z), (max_x, max_y, max_z) = trimesh.load(glb, force="scene").bounds
        sizes[glb.stem] = [round(max_x - min_x, 2), round(max_y - min_y, 2), round(max_z - min_z, 2)]
    (OUTPUT_DIR / "index.json").write_text(json.dumps(sizes, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
