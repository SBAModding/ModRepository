#!/usr/bin/env python3
"""Downloads every mod's file (and every mirror) and checks it against the hash and size in the repository.

    python3 scripts/verify_downloads.py                  # the newest release of every mod
    python3 scripts/verify_downloads.py mods/a.json ...  # just these
    python3 scripts/verify_downloads.py --all ...        # also every older release in previousVersions
    python3 scripts/verify_downloads.py --write-contains # fill in `contains` from the real files (maintainers)

Older releases can be hundreds of megabytes each, so the weekly run checks only the newest ones; a pull request
that changes a mod file checks all of that mod's releases with --all.

This is the independent check that a release asset or an external file has not been replaced after the audit.
Set MODREPO_ALLOW_LOCAL=1 to also accept http://127.0.0.1 URLs (for testing the script itself).
"""
import hashlib
import json
import os
import struct
import sys
import urllib.request
from pathlib import Path

from common import annotate, download_urls, load_mods, write_summary

MAX_BYTES = 1024 * 1024 * 1024


def fetch(url):
    local = os.environ.get("MODREPO_ALLOW_LOCAL") == "1" and url.startswith("http://127.0.0.1")
    if not (url.startswith("https://") or local):
        raise ValueError("refusing to download over a non-https URL")
    req = urllib.request.Request(url, headers={"User-Agent": "SBAModLoader-ModRepository-verify"})
    digest = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(req, timeout=60) as resp:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BYTES:
                raise ValueError("download is larger than 1 GiB")
            digest.update(chunk)
    return digest.hexdigest(), size


def _get(url, start, end):
    """Bytes start..end of the file at url (end inclusive), and the file's total size, without downloading the rest."""
    req = urllib.request.Request(url, headers={"User-Agent": "SBAModLoader-ModRepository-verify",
                                               "Range": f"bytes={start}-{end}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        content_range = resp.headers.get("Content-Range")
        if content_range:
            return resp.read(), int(content_range.rsplit("/", 1)[1])
        # The host ignored the Range header and sends the whole file: read it, bounded, and cut out the part.
        data = resp.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("download is larger than 1 GiB")
        return data[start:end + 1], len(data)


def zip_names(url):
    """The file names inside a zip at url, read from its central directory with a few small range requests."""
    _, total = _get(url, 0, 0)
    tail, _ = _get(url, max(0, total - 65536), total - 1)
    i = tail.rfind(b"PK\x05\x06")
    if i < 0:
        raise ValueError("not a zip file")
    _, cd_size, cd_offset = struct.unpack("<HII", tail[i + 10:i + 20])
    cd, _ = _get(url, cd_offset, cd_offset + cd_size - 1)
    names, pos = [], 0
    while pos + 46 <= len(cd) and cd[pos:pos + 4] == b"PK\x01\x02":
        n, m, k = struct.unpack("<HHH", cd[pos + 28:pos + 34])
        names.append(cd[pos + 46:pos + 46 + n].decode("utf-8", "replace"))
        pos += 46 + n + m + k
    return names


FORMATS = {b"7z\xbc\xaf\x27\x1c": "a 7z archive", b"Rar!": "a RAR archive", b"\x1f\x8b": "a gzip file",
           b"BZh": "a bzip2 file", b"\xfd7zXZ": "an xz file"}


def check_pack_layout(url):
    """A pack must be a zip with sbapack.json and overlay/ (or a .so) at its top. Returns a problem text, or None."""
    head, _ = _get(url, 0, 7)
    if not head.startswith(b"PK"):
        for magic, what in FORMATS.items():
            if head.startswith(magic):
                return (f"the file is {what}, not a zip. Make it with a zip tool (7-Zip: Archive format = zip) "
                        "and keep the .sbapack extension")
        return "the file is not a zip"
    names = [n for n in zip_names(url) if not n.endswith("/")]
    if "sbapack.json" not in names:
        nested = sorted({n.split("/")[0] for n in names if n.endswith("/sbapack.json") and n.count("/") == 1})
        if nested:
            return (f"sbapack.json is inside the folder '{nested[0]}/'. Zip the folder's contents, so that "
                    "sbapack.json and overlay/ are at the top of the zip")
        return "sbapack.json is missing at the top of the zip"
    if not any(n.startswith("overlay/") or ("/" not in n and n.endswith(".so")) or n.startswith("lib/") for n in names):
        return "the pack has no overlay/ folder, native .so or lib/ at the top of the zip"
    return None


def describe(kind, names):
    """What a release is made of, the way the loader reads it: native code, Java code, replaced assets."""
    if kind == "fusion":
        return ["fusion"]
    if kind == "native":
        return ["native"]
    found = set()
    for name in names:
        if name.endswith("/"):
            continue
        if ("/" not in name and name.endswith(".so")) or (name.startswith("lib/") and name.endswith(".so")):
            found.add("native")
        elif name.startswith("overlay/classes") and name.endswith(".dex"):
            found.add("java")
        elif name.startswith("overlay/"):
            found.add("assets")
    return [c for c in ("assets", "native", "java") if c in found]


def check_contains(m, rel, url):
    """Compares the declared contents with the file. Returns an error text, or None."""
    if "contains" not in rel:
        return None
    names = zip_names(url) if m["kind"] == "sbapack" else []
    actual = describe(m["kind"], names)
    if sorted(actual) != sorted(rel["contains"]):
        return f"contains says {rel['contains']} but the file is made of {actual}"
    return None


def write_contains(paths):
    """Maintainers: sets `contains` on every release of the given mods from the real files."""
    for path in paths:
        m = json.loads(path.read_text())
        for rel in [m] + m.get("previousVersions", []):
            url = download_urls(rel)[0]
            names = zip_names(url) if m["kind"] == "sbapack" else []
            rel["contains"] = describe(m["kind"], names)
            print(f"{m['id']} {rel['version']}: {rel['contains']}")
        path.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n")


def main(argv):
    if "--write-contains" in argv:
        rest = [Path(a) for a in argv if not a.startswith("--")] or [p for p, _ in load_mods()]
        write_contains(rest)
        return
    every_release = "--all" in argv
    paths = [Path(a) for a in argv if a != "--all"] or [p for p, _ in load_mods()]
    failed = 0
    rows = []

    def fail(m, rel, msg):
        nonlocal failed
        failed += 1
        where = f"{m['id']}.json"
        annotate("error", where, f"{m['id']} {rel['version']}: {msg}")
        rows.append(("error", where, f"{m['id']} {rel['version']}: {msg}"))

    for path in paths:
        m = json.loads(path.read_text())
        releases = [m] + (m.get("previousVersions", []) if every_release else [])
        for rel in releases:
            for url in download_urls(rel):
                try:
                    sha, size = fetch(url)
                except Exception as e:  # noqa: BLE001 - report every failure and keep going
                    fail(m, rel, f"could not download {url}: {e}")
                    continue
                if sha != rel["sha256"] or size != rel["size"]:
                    fail(m, rel, f"{url} has sha256 {sha} and {size} bytes, "
                                 f"the repository says {rel['sha256']} and {rel['size']}")
                else:
                    print(f"ok   {m['id']} {rel['version']} {url}")
                # The layout and contents are about the real file, so they are reported even when the hash is wrong.
                if url == download_urls(rel)[0]:
                    try:
                        problem = (check_pack_layout(url) if m["kind"] == "sbapack" else None) or check_contains(m, rel, url)
                    except Exception as e:  # noqa: BLE001
                        problem = f"could not read the contents: {e}"
                    if problem:
                        fail(m, rel, problem)
    write_summary("Downloads", rows)
    if failed:
        print(f"{failed} mod(s) failed verification")
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
