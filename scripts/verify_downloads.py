#!/usr/bin/env python3
"""Downloads every mod's file (and every mirror) and checks it against the hash and size in the repository.

    python3 scripts/verify_downloads.py                  # the newest release of every mod
    python3 scripts/verify_downloads.py mods/a.json ...  # just these
    python3 scripts/verify_downloads.py --all ...        # also every older release in previousVersions

Older releases can be hundreds of megabytes each, so the weekly run checks only the newest ones; a pull request
that changes a mod file checks all of that mod's releases with --all.

This is the independent check that a release asset or an external file has not been replaced after the audit.
Set MODREPO_ALLOW_LOCAL=1 to also accept http://127.0.0.1 URLs (for testing the script itself).
"""
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

from common import download_urls, load_mods

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
    every_release = "--all" in argv
    paths = [Path(a) for a in argv if a != "--all"] or [p for p, _ in load_mods()]
    failed = 0
    for path in paths:
        m = json.loads(path.read_text())
        releases = [m] + (m.get("previousVersions", []) if every_release else [])
        for rel in releases:
            for url in download_urls(rel):
                try:
                    sha, size = fetch(url)
                except Exception as e:  # noqa: BLE001 - report every failure and keep going
                    print(f"FAIL {m['id']} {rel['version']}: could not download {url}: {e}")
                    failed += 1
                    continue
                if sha != rel["sha256"] or size != rel["size"]:
                    print(f"FAIL {m['id']} {rel['version']}: {url} has sha256 {sha} and {size} bytes, "
                          f"the repository says {rel['sha256']} and {rel['size']}")
                    failed += 1
                else:
                    print(f"ok   {m['id']} {rel['version']} {url}")
    if failed:
        print(f"{failed} mod(s) failed verification")
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
