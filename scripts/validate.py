#!/usr/bin/env python3
"""Validates mods/*.json, categories.json and the generated index.json. Standard library only."""
import json
import sys

from common import (ALLOWED_KEYS, DATE_RE, HEX64, ID_RE, INDEX, KINDS, MODS_DIR, REQUIRED_KEYS, ROOT, VERSION_RE,
                    load_categories, load_mods)

errors = []


def err(where, msg):
    errors.append(f"{where}: {msg}")
    print(f"error: {where}: {msg}")


def check_mod(path, m, valid_categories, ids):
    w = path.name
    if not isinstance(m, dict):
        return err(w, "must be a JSON object")
    for key in REQUIRED_KEYS:
        if key not in m:
            err(w, f"missing '{key}'")
    for key in m:
        if key not in ALLOWED_KEYS:
            err(w, f"unknown field '{key}'")
    if any(e.startswith(w + ":") for e in errors):
        return

    if not ID_RE.match(m["id"]):
        err(w, "id must be 2-64 characters of a-z, 0-9 and '-'")
    if path.stem != m["id"]:
        err(w, f"file name must be {m['id']}.json")
    if m["kind"] not in KINDS:
        err(w, f"kind must be one of {KINDS}")
    for key in ("name", "author", "summary", "description", "license"):
        if not isinstance(m[key], str) or not m[key].strip():
            err(w, f"'{key}' must be a non-empty string")
    if len(m["summary"]) > 120:
        err(w, "summary is longer than 120 characters")
    if not VERSION_RE.match(m["version"]):
        err(w, "version must look like 1.2 or 1.2.3")
    if not isinstance(m["gameVersions"], list) or not m["gameVersions"]:
        err(w, "gameVersions must list at least one game version")
    if not isinstance(m["categories"], list) or not m["categories"]:
        err(w, "a mod needs at least one category")
    else:
        for c in m["categories"]:
            if c not in valid_categories:
                err(w, f"unknown category '{c}' (see categories.json)")
        if len(set(m["categories"])) != len(m["categories"]):
            err(w, "duplicate category")
    if not isinstance(m["size"], int) or isinstance(m["size"], bool) or m["size"] < 1:
        err(w, "size must be a positive integer (bytes)")
    if not HEX64.match(m["sha256"]):
        err(w, "sha256 must be 64 lowercase hex characters")
    if not DATE_RE.match(m["updated"]):
        err(w, "updated must be YYYY-MM-DD")

    # Where the file may come from. Open source mods are only ever loaded from a GitHub release.
    s = m["source"]
    if not isinstance(s, dict) or s.get("kind") not in ("github", "external"):
        err(w, "source.kind must be 'github' or 'external'")
    elif s["kind"] == "github":
        extra = set(s) - {"kind", "repo", "tag", "asset"}
        if extra:
            err(w, f"unknown source fields {sorted(extra)}")
        for key in ("repo", "tag", "asset"):
            if not isinstance(s.get(key), str) or not s[key]:
                err(w, f"github source needs '{key}'")
        if isinstance(s.get("repo"), str) and s["repo"].count("/") != 1:
            err(w, "source.repo must be owner/repo")
        if isinstance(s.get("asset"), str) and "/" in s["asset"]:
            err(w, "source.asset must be a file name")
    else:
        extra = set(s) - {"kind", "url"}
        if extra:
            err(w, f"unknown source fields {sorted(extra)}")
        if not isinstance(s.get("url"), str) or not s["url"].startswith("https://"):
            err(w, "external source needs an https url")

    if not isinstance(m["openSource"], bool):
        err(w, "openSource must be true or false")
    elif m["openSource"] and isinstance(s, dict) and s.get("kind") != "github":
        err(w, "open source mods must be loaded from a GitHub release")
    elif not m["openSource"] and isinstance(s, dict) and s.get("kind") != "external":
        err(w, "closed source mods must use an external source")
    if m.get("openSource") is True and m["license"].strip().lower().startswith("all rights"):
        err(w, "an open source mod cannot be 'All rights reserved'")
    if m.get("openSource") is False and not m["license"].strip():
        err(w, "closed source mods must state their terms in 'license'")

    # Every release is audited before it is listed; an audit covers exactly one version.
    a = m["audited"]
    if not isinstance(a, dict) or set(a) != {"version", "date", "by"}:
        err(w, "audited must have exactly version, date and by")
    else:
        if a["version"] != m["version"]:
            err(w, f"audited version {a['version']} is not the listed version {m['version']}: the new version needs a review")
        if not DATE_RE.match(a["date"]):
            err(w, "audited.date must be YYYY-MM-DD")
        if not isinstance(a["by"], str) or not a["by"].strip():
            err(w, "audited.by must name the reviewer")

    for key in ("tags", "requires"):
        if key in m and (not isinstance(m[key], list) or any(not isinstance(x, str) for x in m[key])):
            err(w, f"'{key}' must be a list of strings")
    for r in m.get("requires", []):
        if r == m["id"]:
            err(w, "a mod cannot require itself")
        elif r not in ids:
            err(w, f"requires '{r}', which is not in this repository")


def main():
    # categories.json must stay in step with the schema's pattern and the loader.
    cats = load_categories()
    mods = load_mods()
    ids = {m["id"] for _, m in mods if isinstance(m, dict) and "id" in m}
    seen = set()
    for path, m in mods:
        if isinstance(m, dict) and m.get("id") in seen:
            err(path.name, "duplicate id")
        if isinstance(m, dict):
            seen.add(m.get("id"))
        check_mod(path, m, cats, ids)

    # index.json is generated; it must match mods/ exactly.
    from build_index import build
    expected = build()
    actual = json.loads(INDEX.read_text()) if INDEX.exists() else None
    if actual != expected:
        err("index.json", "is out of date; run `python3 scripts/build_index.py` and commit the result")

    if errors:
        print(f"{len(errors)} error(s)")
        sys.exit(1)
    print(f"ok ({len(mods)} mods)")


if __name__ == "__main__":
    main()
