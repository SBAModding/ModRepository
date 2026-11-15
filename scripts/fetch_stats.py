#!/usr/bin/env python3
"""Writes stats.json: how many times each mod has been downloaded, added up over all of its releases.

    python3 scripts/fetch_stats.py            # uses GITHUB_TOKEN when set (5000 requests an hour, otherwise 60)

The counts are GitHub's own download counts of the release assets a mod's files are served from: the `github` sources,
and `external` URLs that are release assets (such as the ones in the release repository). A mod hosted anywhere else has
no count. The loader reads stats.json next to index.json; it is a separate file so the index, which is checked against
the mod files, does not change every few hours.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

from common import ROOT, load_mods

ASSET_URL = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/releases/download/([^/]+)/([^/?#]+)$")


def api(path):
    req = urllib.request.Request("https://api.github.com" + path, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "SBAModLoader-ModRepository-stats"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def asset_of(release):
    """(repo, tag, asset name) of the GitHub release asset a release is served from, or None."""
    s = release["source"]
    if s["kind"] == "github":
        return s["repo"], s["tag"], s["asset"]
    m = ASSET_URL.match(s["url"])
    if m:
        return m.group(1), urllib.parse.unquote(m.group(2)), urllib.parse.unquote(m.group(3))
    return None


def downloads(repo, tag, name, cache):
    key = (repo, tag)
    if key not in cache:
        try:
            cache[key] = api(f"/repos/{repo}/releases/tags/{urllib.parse.quote(tag)}")["assets"]
        except urllib.error.HTTPError as e:
            # Never write counts that are wrong because a request failed (zeros would look like a real drop).
            sys.exit(f"could not read the release {repo}@{tag}: {e}")
    for asset in cache[key]:
        if asset["name"] == name:
            return int(asset["download_count"])
    return 0


def main():
    cache, totals = {}, {}
    for _, m in load_mods():
        total, counted = 0, False
        for rel in [m] + m.get("previousVersions", []):
            ref = asset_of(rel)
            if ref:
                counted = True
                total += downloads(*ref, cache)
        if counted:
            totals[m["id"]] = total
    out = json.dumps(dict(sorted(totals.items())), indent=2) + "\n"
    path = ROOT / "stats.json"
    if not path.exists() or path.read_text() != out:
        path.write_text(out)
        print("stats.json updated")
    else:
        print("stats.json unchanged")


if __name__ == "__main__":
    main()
