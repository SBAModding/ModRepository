#!/usr/bin/env python3
"""Validates mods/*.json, categories.json and the generated index.json. Standard library only."""
import json
import sys

from common import (CONTAINS, MAX_AUDIT_NOTES, MAX_AUDIT_NOTE_LENGTH, ALLOWED_KEYS, DATE_RE, HEX64, ID_RE, IMAGE_EXTENSIONS, INDEX, KINDS, MAX_IMAGE_BYTES,
                    MAX_SCREENSHOTS, MODS_DIR, RELEASE_OPTIONAL, RELEASE_REQUIRED, REQUIRED_KEYS, ROOT, VERSION_RE,
                    annotate, download_url, load_categories, load_mods, version_key, write_summary)

errors = []


def err(where, msg):
    errors.append(("error", where, msg))
    annotate("error", where, msg)


def check_source(w, s, open_source):
    """Where the file may come from. Open source mods are only ever loaded from a GitHub release."""
    if not isinstance(s, dict) or s.get("kind") not in ("github", "external"):
        err(w, "source.kind must be 'github' or 'external'")
        return
    if s["kind"] == "github":
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
    if open_source is True and s["kind"] != "github":
        err(w, "open source mods must be loaded from a GitHub release")
    elif open_source is False and s["kind"] != "external":
        err(w, "closed source mods must use an external source")


def check_dependencies(w, deps, own_id, ids):
    """`dependencies` are {id, min?, max?}: the mods a release needs and the versions of them it works with."""
    if not isinstance(deps, list):
        return err(w, "dependencies must be a list")
    seen = set()
    for d in deps:
        if not isinstance(d, dict) or not isinstance(d.get("id"), str) or set(d) - {"id", "min", "max"}:
            err(w, "each dependency must be an object with 'id' and optional 'min' and 'max'")
            continue
        if d["id"] == own_id:
            err(w, "a mod cannot require itself")
        elif d["id"] not in ids:
            err(w, f"requires '{d['id']}', which is not in this repository")
        if d["id"] in seen:
            err(w, f"dependency '{d['id']}' is listed twice")
        seen.add(d["id"])
        bounds = {}
        for key in ("min", "max"):
            if key in d:
                if not isinstance(d[key], str) or not VERSION_RE.match(d[key]):
                    err(w, f"dependency '{d['id']}' {key} must look like 1.2 or 1.2.3")
                else:
                    bounds[key] = d[key]
        if len(bounds) == 2 and version_key(bounds["min"]) > version_key(bounds["max"]):
            err(w, f"dependency '{d['id']}' has min above max")


def check_release(w, rel, mod, ids):
    """One release: the top level of a mod file, or one entry of `previousVersions`."""
    if not isinstance(rel["version"], str) or not VERSION_RE.match(rel["version"]):
        err(w, "version must look like 1.2 or 1.2.3")
    gv = rel["gameVersions"]
    if not isinstance(gv, list) or not gv or any(not isinstance(x, str) or not x.strip() for x in gv):
        err(w, "gameVersions must list at least one game version")
    elif len(set(gv)) != len(gv):
        err(w, "duplicate game version")
    if not isinstance(rel["size"], int) or isinstance(rel["size"], bool) or rel["size"] < 1:
        err(w, "size must be a positive integer (bytes)")
    if not isinstance(rel["sha256"], str) or not HEX64.match(rel["sha256"]):
        err(w, "sha256 must be 64 lowercase hex characters")
    if not isinstance(rel["updated"], str) or not DATE_RE.match(rel["updated"]):
        err(w, "updated must be YYYY-MM-DD")
    if "changelog" in rel and not isinstance(rel["changelog"], str):
        err(w, "changelog must be a string")

    s = rel["source"]
    check_source(w, s, mod["openSource"] if isinstance(mod.get("openSource"), bool) else None)

    # Every release is audited before it is listed; an audit covers exactly one version.
    a = rel["audited"]
    if not isinstance(a, dict) or not {"version", "date", "by"} <= set(a) or not set(a) <= {"version", "date", "by", "notes"}:
        err(w, "audited must have version, date and by, and may have notes")
    else:
        # Notes are the reviewer's short reasons it is safe, shown to people on the mod's page.
        if "notes" in a:
            n = a["notes"]
            if not isinstance(n, list) or not 1 <= len(n) <= MAX_AUDIT_NOTES:
                err(w, f"audited.notes must be a list of 1 to {MAX_AUDIT_NOTES} short sentences")
            elif any(not isinstance(x, str) or not x.strip() or len(x) > MAX_AUDIT_NOTE_LENGTH for x in n):
                err(w, f"each audited note must be text of at most {MAX_AUDIT_NOTE_LENGTH} characters")
        if a["version"] != rel["version"]:
            err(w, f"audited version {a['version']} is not the listed version {rel['version']}: the new version needs a review")
        if not isinstance(a["date"], str) or not DATE_RE.match(a["date"]):
            err(w, "audited.date must be YYYY-MM-DD")
        if not isinstance(a["by"], str) or not a["by"].strip():
            err(w, "audited.by must name the reviewer")

    # Optional extra copies of the same file. Each one is hash-checked like the primary, so a mirror is trusted
    # no more than the host it is on.
    if "mirrors" in rel:
        mirrors = rel["mirrors"]
        if not isinstance(mirrors, list) or any(not isinstance(u, str) for u in mirrors):
            err(w, "mirrors must be a list of URLs")
        else:
            usable = isinstance(s, dict) and (
                (s.get("kind") == "github" and all(isinstance(s.get(k), str) for k in ("repo", "tag", "asset")))
                or (s.get("kind") == "external" and isinstance(s.get("url"), str)))
            primary = download_url(rel) if usable else None
            for u in mirrors:
                if not u.startswith("https://"):
                    err(w, f"mirror {u!r} must be an https url")
                if u == primary:
                    err(w, "a mirror cannot repeat the primary url")
            if len(set(mirrors)) != len(mirrors):
                err(w, "duplicate mirror")

    if "contains" in rel:
        c = rel["contains"]
        if not isinstance(c, list) or not c or any(x not in CONTAINS for x in c) or len(set(c)) != len(c):
            err(w, f"contains must list what the release is made of, from {', '.join(CONTAINS)}")
        elif mod.get("kind") == "fusion" and c != ["fusion"]:
            err(w, "a fusion mod contains exactly fusion")
        elif mod.get("kind") == "native" and c != ["native"]:
            err(w, "a native mod contains exactly native")
        elif mod.get("kind") == "sbapack" and ("fusion" in c):
            err(w, "a pack cannot contain fusion")

    if "dependencies" in rel:
        check_dependencies(w, rel["dependencies"], mod["id"], ids)


def check_images(w, m):
    if "icon" in m:
        check_image(w, "icon", m["icon"], m["id"])
    if "screenshots" in m:
        shots = m["screenshots"]
        if not isinstance(shots, list) or any(not isinstance(x, str) for x in shots):
            err(w, "screenshots must be a list of paths")
        else:
            if len(shots) > MAX_SCREENSHOTS:
                err(w, f"at most {MAX_SCREENSHOTS} screenshots")
            if len(set(shots)) != len(shots):
                err(w, "duplicate screenshot")
            for x in shots:
                check_image(w, "screenshot", x, m["id"])


def check_image(w, what, path, mod_id):
    """Images live in the repository under images/<mod id>/ and are served from there."""
    if not isinstance(path, str) or not path.startswith(f"images/{mod_id}/") or ".." in path.split("/"):
        return err(w, f"{what} must be a file under images/{mod_id}/")
    if not path.lower().endswith(IMAGE_EXTENSIONS):
        return err(w, f"{what} {path} must be a png, jpg or webp image")
    f = ROOT / path
    if not f.is_file():
        return err(w, f"{what} {path} does not exist")
    if f.stat().st_size > MAX_IMAGE_BYTES:
        err(w, f"{what} {path} is larger than {MAX_IMAGE_BYTES // 1024} KB")


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
    if not isinstance(m["categories"], list) or not m["categories"]:
        err(w, "a mod needs at least one category")
    else:
        for c in m["categories"]:
            if c not in valid_categories:
                err(w, f"unknown category '{c}' (see categories.json)")
        if len(set(m["categories"])) != len(m["categories"]):
            err(w, "duplicate category")
    if not isinstance(m["openSource"], bool):
        err(w, "openSource must be true or false")
    if m.get("openSource") is True and m["license"].strip().lower().startswith("all rights"):
        err(w, "an open source mod cannot be 'All rights reserved'")
    if m.get("openSource") is False and not m["license"].strip():
        err(w, "closed source mods must state their terms in 'license'")

    # The newest release is the top level of the file.
    check_release(w, m, m, ids)

    # Older releases stay installable. Newest first, each one audited on its own.
    previous = m.get("previousVersions", [])
    if not isinstance(previous, list):
        err(w, "previousVersions must be a list")
        previous = []
    versions = [m["version"]]
    for i, old in enumerate(previous):
        ow = f"{w} previousVersions[{i}]"
        if not isinstance(old, dict):
            err(ow, "must be a JSON object")
            continue
        missing = [k for k in RELEASE_REQUIRED if k not in old]
        extra = set(old) - set(RELEASE_REQUIRED) - set(RELEASE_OPTIONAL)
        for k in missing:
            err(ow, f"missing '{k}'")
        for k in sorted(extra):
            err(ow, f"unknown field '{k}'")
        if missing or extra:
            continue
        check_release(ow, old, m, ids)
        if isinstance(old["version"], str) and VERSION_RE.match(old["version"]) and VERSION_RE.match(versions[-1]):
            if old["version"] in versions:
                err(ow, f"version {old['version']} is listed twice")
            elif version_key(old["version"]) > version_key(versions[-1]):
                err(ow, "previousVersions must be newest first and older than the current version")
            versions.append(old["version"])

    for key in ("tags", "requires"):
        if key in m and (not isinstance(m[key], list) or any(not isinstance(x, str) for x in m[key])):
            err(w, f"'{key}' must be a list of strings")
    # `requires` is the older, ids-only form that loaders before 0.0.3 read. It is generated from `dependencies`.
    if "dependencies" in m and "requires" in m and isinstance(m["dependencies"], list):
        dep_ids = [d.get("id") for d in m["dependencies"] if isinstance(d, dict)]
        if sorted(map(str, dep_ids)) != sorted(map(str, m["requires"])):
            err(w, "requires must list the same ids as dependencies (or be left out)")
    for r in m.get("requires", []):
        if r == m["id"]:
            err(w, "a mod cannot require itself")
        elif r not in ids:
            err(w, f"requires '{r}', which is not in this repository")

    check_images(w, m)


def dependency_ids(m):
    if isinstance(m.get("dependencies"), list):
        return [d["id"] for d in m["dependencies"] if isinstance(d, dict) and isinstance(d.get("id"), str)]
    return [r for r in m.get("requires", []) if isinstance(r, str)]


def check_cycles(mods):
    graph = {m["id"]: dependency_ids(m) for _, m in mods if isinstance(m, dict) and "id" in m}
    state = {}

    def visit(node, trail):
        if state.get(node) == 2:
            return
        if state.get(node) == 1:
            err("mods", "dependency cycle: " + " -> ".join(trail + [node]))
            return
        state[node] = 1
        for nxt in graph.get(node, []):
            if nxt in graph:
                visit(nxt, trail + [node])
        state[node] = 2

    for node in graph:
        visit(node, [])


def main(argv):
    # CI passes --allow-stale-index: a workflow rebuilds index.json after a merge, so a pull request is not
    # failed for it. Locally the check stays strict.
    allow_stale_index = "--allow-stale-index" in argv
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
    check_cycles(mods)

    # index.json is generated; it must match mods/ exactly.
    from build_index import build
    expected = build()
    actual = json.loads(INDEX.read_text()) if INDEX.exists() else None
    if actual != expected:
        if allow_stale_index:
            annotate("notice", "index.json", "will be rebuilt automatically after this is merged")
        else:
            err("index.json", "is out of date; run `python3 scripts/build_index.py` and commit the result")

    write_summary("Mod files", errors)
    if errors:
        print(f"{len(errors)} error(s)")
        sys.exit(1)
    print(f"ok ({len(mods)} mods)")


if __name__ == "__main__":
    main(sys.argv[1:])
