"""Shared helpers for the repository tooling. Standard library only."""
import json
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
                "mirrors"}
REQUIRED_KEYS = ["id", "name", "author", "kind", "summary", "description", "categories", "version", "gameVersions",
                 "size", "sha256", "updated", "source", "openSource", "license", "audited"]


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
