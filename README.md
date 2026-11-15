# SBAModding mod repository

The list of mods that SBAModLoader's mod browser shows. The loader fetches [`index.json`](index.json) every time it
opens the browser.

## Trust model

Nothing in this repository is trusted because of where it is hosted. Every mod is pinned by hash.

1. **Audited first.** A mod is reviewed by the SBAModLoader team before it is listed. The review covers one exact
   version; a new version is reviewed again before its entry changes.
2. **The hash is the source of truth.** Each entry holds the SHA-256 and size of the file. The loader downloads the
   file and installs it only if both match, whatever the host says.
3. **Open source mods** are loaded from a **GitHub release** (`openSource: true`, `source.kind: "github"`).
   Being on GitHub does not make a file trusted: the hash is still checked.
4. **Closed source / all rights reserved mods** are loaded from an **external URL** (`openSource: false`,
   `source.kind: "external"`): the creator's own host, or a release of the project's
   [release repository](https://github.com/SBAModding/ReleaseRepository) for creators who allow it to host the file.
5. A mod can list extra `mirrors` of the same file (none do yet). The loader tries the primary source first and then
   each mirror, and accepts any copy that matches the hash, so a mirror is trusted no more than any other host.
6. CI downloads every file, mirrors included, on every pull request and every week, so a release asset or an
   external file that changes after the audit fails verification. The weekly run checks the newest release of each
   mod; a pull request that touches a mod file checks all of that mod's releases.
7. Older releases stay listed (see below), and each one is audited and hash-pinned on its own.

## Versions, game versions and dependencies

The top level of `mods/<id>.json` is the **newest** release. Older releases go in `previousVersions`, newest first, so
players can still install them (for example when they have not updated the game):

```json
"previousVersions": [
  { "version": "1.0.0", "gameVersions": ["13.0.8"], "size": 1234, "sha256": "...", "updated": "2026-11-14",
    "source": { "kind": "external", "url": "https://..." },
    "audited": { "version": "1.0.0", "date": "2026-11-14", "by": "SBAModLoader team" },
    "changelog": "First release." }
]
```

When you publish a new version, copy the current top-level release into `previousVersions` (first position), then
update the top level. Every release has its own `gameVersions`, `size`, `sha256`, `source`, `audited` and optional
`mirrors`, `changelog` and `dependencies`. Versions must be unique and ordered newest first.

`dependencies` lists the mods a release needs, with the versions of them it works with (both bounds inclusive and
optional):

```json
"dependencies": [ { "id": "some-library", "min": "1.2.0", "max": "1.9" } ]
```

The loader installs a release's dependencies together with it and warns when the versions do not fit. `requires` is the
older ids-only form that loaders before 0.0.3 read; `build_index.py` generates it from `dependencies`, so use only
`dependencies` in new work.

## Images

A mod can have an `icon` and up to 8 `screenshots`: png, jpg or webp files of at most 1 MB each, stored in this
repository under `images/<mod id>/` and listed by path:

```json
"icon": "images/hive-reborn/icon.png",
"screenshots": ["images/hive-reborn/1.png", "images/hive-reborn/2.png"]
```

## What a mod is

| `kind` | What it is | File |
|---|---|---|
| `fusion` | A BepInEx plugin | `.dll`, or a `.zip` of a plugin |
| `native` | A native mod | `.so` |
| `sbapack` | A pack: assets, Java and native code | `.sbapack` |

## Categories

A mod lists one or more `category/subcategory` pairs (see [`categories.json`](categories.json)):

- **Texture packs**: `fun`, `extra_content`, `replacement`
- **Mods**: `quality_of_life`, `expansion`, `changes`, `cheats`, `port`

## Layout

```
mods/<id>.json             one file per mod: the source of truth
index.json                 generated from mods/, never edited by hand
images/<id>/               icons and screenshots of each mod
categories.json            the category list
schema/mod.schema.json     JSON Schema for a mod file
schema/index.schema.json   JSON Schema for index.json
examples/example-mod.json  a template (not listed)
scripts/validate.py        checks every mod file and that index.json is current
scripts/build_index.py     regenerates index.json
scripts/verify_downloads.py  downloads each file and checks its hash and size (--all: older releases too)
```

Everything is plain Python 3 with no dependencies.

## Adding or updating a mod

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Download counts

`stats.json` holds how many times each mod has been downloaded, added up over all of its releases. A scheduled workflow
(`.github/workflows/stats.yml`, every 6 hours) runs `scripts/fetch_stats.py`, which reads GitHub's own download counts of
the release assets the mods are served from, and commits the file when it changes. The loader shows the numbers; a mod
hosted somewhere other than a GitHub release has none.
