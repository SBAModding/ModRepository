#!/usr/bin/env python3
"""Downloads every mod's file and checks it against the hash and size in the repository.

    python3 scripts/verify_downloads.py                  # every mod
    python3 scripts/verify_downloads.py mods/a.json ...  # just these

This is the independent check that a release asset or an external file has not been replaced after the audit.
Set MODREPO_ALLOW_LOCAL=1 to also accept http://127.0.0.1 URLs (for testing the script itself).
"""
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

from common import download_url, load_mods

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


def main(argv):
    paths = [Path(a) for a in argv] or [p for p, _ in load_mods()]
    failed = 0
    for path in paths:
        m = json.loads(path.read_text())
        url = download_url(m)
        try:
            sha, size = fetch(url)
        except Exception as e:  # noqa: BLE001 - report every failure and keep going
            print(f"FAIL {m['id']}: could not download {url}: {e}")
            failed += 1
            continue
        if sha != m["sha256"] or size != m["size"]:
            print(f"FAIL {m['id']}: {url} has sha256 {sha} and {size} bytes, the repository says {m['sha256']} and {m['size']}")
            failed += 1
        else:
            print(f"ok   {m['id']} {m['version']}")
    if failed:
        print(f"{failed} mod(s) failed verification")
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
