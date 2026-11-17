import re
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "app" / "static"


def test_import_map_targets_exist():
    # A missing vendored file only shows up in the browser (404), so check it here.
    index = (STATIC / "index.html").read_text(encoding="utf-8")
    targets = re.findall(r'"three(?:/addons/)?": "\./static/([^"]+)"', index)
    assert len(targets) == 2
    for target in targets:
        assert (STATIC / target).exists(), target


def test_three_addon_imports_exist():
    for script in (STATIC / "js").glob("*.js"):
        for addon in re.findall(r'"three/addons/([^"]+)"', script.read_text(encoding="utf-8")):
            assert (STATIC / "vendor/three/examples/jsm" / addon).is_file(), (script.name, addon)
