"""Check that the links of the hardware catalog and of the sheets still answer.

Run by the "Links" workflow. Some manufacturers refuse automated requests, so
a failure is reported (GitHub annotation and job summary) without failing the
job, unless --strict is given.

Usage: python tools/check_links.py [--strict]
"""

from __future__ import annotations

import argparse
import concurrent.futures
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.catalog import normalize  # noqa: E402
from app.sheets import SheetLibrary  # noqa: E402

SHEETS_DIR = ROOT / "sheets"
# A generic client name: some sites answer 403 to requests without a browser-like agent.
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) Promethee-link-check/1.0"
TIMEOUT = 30


def collect() -> list[tuple[str, str]]:
    """(where the link comes from, url) for every link of the catalog and of the sheets."""
    links = []
    devices, problems = normalize(yaml.safe_load((SHEETS_DIR / "catalog.yaml").read_text(encoding="utf-8")))
    if problems:
        raise SystemExit("Invalid catalog: " + "; ".join(problems))
    for device in devices:
        links += [(f"catalog: {device['id']}", url) for url in device["links"]]
    sheets, _ = SheetLibrary(SHEETS_DIR).list()
    for sheet in sheets:
        links += [(f"sheet: {sheet.id}", link["url"]) for link in sheet.meta["links"]]
    return links


def check(url: str) -> tuple[bool, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            response.read(1024)  # enough to know the document is served
            kind = response.headers.get_content_type()
            moved = f" -> {response.geturl()}" if response.geturl() != url else ""
            return True, f"{response.status} {kind}{moved}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:  # DNS, TLS, timeout…
        return False, f"{type(exc).__name__}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the links of the catalog and of the sheets.")
    parser.add_argument("--strict", action="store_true", help="exit with an error if a link fails")
    args = parser.parse_args()

    links = collect()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda item: (*item, *check(item[1])), links))

    failures = [r for r in results if not r[2]]
    rows = []
    for origin, url, ok, detail in results:
        print(f"{'OK  ' if ok else 'FAIL'} {origin:32} {url} ({detail})")
        rows.append(f"| {'✅' if ok else '❌'} | {origin} | {url} | {detail} |")
        if not ok and os.environ.get("GITHUB_ACTIONS"):
            print(f"::warning title=Lien injoignable::{origin}: {url} ({detail})")
    print(f"\n{len(results) - len(failures)}/{len(results)} links answer.")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write(f"### Liens : {len(results) - len(failures)}/{len(results)} répondent\n\n")
            out.write("| | Origine | Lien | Résultat |\n|---|---|---|---|\n" + "\n".join(rows) + "\n")
    return 1 if failures and args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
