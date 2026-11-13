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
   external file that changes after the audit fails verification.

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
categories.json            the category list
schema/mod.schema.json     JSON Schema for a mod file
schema/index.schema.json   JSON Schema for index.json
examples/example-mod.json  a template (not listed)
scripts/validate.py        checks every mod file and that index.json is current
scripts/build_index.py     regenerates index.json
scripts/verify_downloads.py  downloads each file and checks its hash and size
```

Everything is plain Python 3 with no dependencies.

## Adding or updating a mod

See [CONTRIBUTING.md](CONTRIBUTING.md).
