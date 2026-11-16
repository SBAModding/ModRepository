"""Shared helpers for the repository tooling. Standard library only."""
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODS_DIR = ROOT / "mods"
INDEX = ROOT / "index.json"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VERSION_RE = re.compile(r"^[0-9]+(\.[0-9]+){1,3}([-+][0-9A-Za-z.-]+)?$")
KINDS = ("fusion", "native", "sbapack")
ALLOWED_KEYS = {"id", "name", "author", "kind", "summary", "description", "categories", "version", "gameVersions",
                "size", "sha256", "updated", "source", "openSource", "license", "audited", "changelog", "tags", "requires",
                "mirrors", "dependencies", "previousVersions", "icon", "screenshots", "contains"}
REQUIRED_KEYS = ["id", "name", "author", "kind", "summary", "description", "categories", "version", "gameVersions",
                 "size", "sha256", "updated", "source", "openSource", "license", "audited"]

# One release of a mod. The top level of a mod file is its newest release; `previousVersions` holds the older ones.
RELEASE_REQUIRED = ["version", "gameVersions", "size", "sha256", "updated", "source", "audited"]
RELEASE_OPTIONAL = ["mirrors", "changelog", "dependencies", "contains"]
# What a release is made of: replaced files, native code, Java code, or a BepInEx plugin. Checked against the real file.
CONTAINS = ("assets", "native", "java", "fusion")
MAX_AUDIT_NOTES = 6
MAX_AUDIT_NOTE_LENGTH = 120
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
MAX_IMAGE_BYTES = 1024 * 1024
MAX_SCREENSHOTS = 8
_VERSION_PARTS = re.compile(r"^([0-9]+(?:\.[0-9]+)*)(?:([-+])(.*))?$")


def version_key(version):
    """Sort key for a VERSION_RE version: numbers first, and 1.2.0-beta sorts before 1.2.0."""
    m = _VERSION_PARTS.match(version)
    nums = [int(n) for n in m.group(1).split(".")]
    nums += [0] * (4 - len(nums))
    prerelease = m.group(2) == "-"
    return (tuple(nums), 0 if prerelease else 1, m.group(3) or "")


def load_categories():
    data = json.loads((ROOT / "categories.json").read_text())
    return {f"{c}/{s}" for c, v in data.items() for s in v["subs"]}


def load_mods():
    mods = []
    for path in sorted(MODS_DIR.glob("*.json")):
        mods.append((path, json.loads(path.read_text())))
    return mods


def download_urls(mod):
    """The primary URL followed by any mirrors. Every one must serve exactly the pinned file."""
    return [download_url(mod)] + list(mod.get("mirrors", []))


def download_url(mod):
    s = mod["source"]
    if s["kind"] == "github":
        return f"https://github.com/{s['repo']}/releases/download/{s['tag']}/{s['asset']}"
    return s["url"]


def annotate(level, where, msg):
    """Prints a problem. On GitHub Actions it also becomes an annotation shown on the pull request's changed file."""
    print(f"{level}: {where}: {msg}")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        target = MODS_DIR / where
        file = f"mods/{where}" if where.endswith(".json") and target.exists() else where
        text = msg.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print(f"::{level} file={file}::{text}")


def write_summary(title, rows):
    """Adds a table to the job's summary page (GitHub Actions only). rows: list of (status, where, message)."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a") as f:
        f.write(f"### {title}\n\n")
        if not rows:
            f.write("All checks passed.\n\n")
            return
        f.write("| | Where | Problem |\n|---|---|---|\n")
        for status, where, msg in rows:
            f.write(f"| {status} | `{where}` | {msg.replace('|', chr(92) + '|')} |\n")
        f.write("\n")
