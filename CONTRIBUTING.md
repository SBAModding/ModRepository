# Submitting a mod

Mods are added by pull request, one file per mod: `mods/<id>.json`. Start from
[`examples/example-mod.json`](examples/example-mod.json).

## Before you open a pull request

1. Publish the file.
   - **Open source:** create a GitHub release and attach the file as a release asset. Use a tag and do not edit the
     release afterwards.
   - **Closed source or all rights reserved:** host the file at a stable `https` URL. If you cannot host it and
     you allow it, a maintainer can publish the audited file as a release of the
     [release repository](https://github.com/SBAModding/ReleaseRepository) instead, and your entry points there.
2. Get the hash and size of exactly that file:
   ```
   sha256sum ExampleMod.dll
   stat -c %s ExampleMod.dll
   ```
3. Fill in `mods/<id>.json`. `id` is lowercase letters, digits and `-`, and equals the file name.
4. Check your file before you open the pull request:
   ```
   python3 scripts/validate.py --allow-stale-index
   python3 scripts/verify_downloads.py mods/<id>.json
   ```
   Change **only** `mods/<id>.json`. Do not edit `index.json` or `stats.json`: they are generated, and a pull request
   that changes them fails the *Index* check. `index.json` is rebuilt automatically after the merge.

### Packs (`.sbapack`)

A pack is a **zip** file with the extension `.sbapack` (not 7z, RAR or tar). `sbapack.json` and the `overlay/` folder
(or a native `.so`) sit at the **top** of the zip, not inside another folder. Zip the folder's *contents*. In 7-Zip set
Archive format to `zip`; "Store" is fine for large art files. The *Downloads* check reads the file and says which of
these is wrong.

## What the checks tell you

A pull request shows three checks, and problems are marked on the changed file:

| Check | What it looks at |
|---|---|
| **Mod files** | the structure of `mods/*.json`, the audit rules, dependencies, images |
| **Index** | that `index.json` and `stats.json` were not edited by hand |
| **Downloads** | that the real file has the stated size and SHA-256, is laid out as a pack, and contains what `contains` says |

## The audit

A reviewer fills in `audited` after reading the release, not before. The audit names one version, and `audited.version`
must equal `version`. When you publish a new version, move the current release into `previousVersions` (keeping its
own audit), then update `version`, `gameVersions`, `size`, `sha256` and the source at the top level. The reviewer audits
the new release before the entry is merged. Old releases keep their own audit and stay installable.

A review covers, at least:

- the source (open source) or the decompiled and disassembled code (closed source);
- what the mod does on the network, on disk, and to the rest of the device;
- native code: its imports, what it hooks, and anything it loads or downloads;
- the license, and that the stated source matches the file that was hashed.

## Notes and contents shown on the mod's page

The loader's page for a mod explains why it is rated safe. Two optional fields feed it:

- `audited.notes`: up to 6 short sentences (120 characters each) written by the reviewer, for example "Reads only art
  assets". Add them only for things the reviewer actually checked.
- `contains`: what the release is made of (`assets`, `native`, `java`, `fusion`). A pack with only `assets` is shown as
  having no code. Do not type it by hand: run `python3 scripts/verify_downloads.py --write-contains mods/<id>.json`, which
  reads the file's table of contents, and CI checks it again.

## Rules the checks enforce

- Open source mods are loaded from a GitHub release; closed source mods from an external `https` URL.
- Open source mods name an open license (an SPDX identifier); closed source mods state their terms, for example
  `All rights reserved`.
- The audited version equals the listed version, and any `audited.notes` are short sentences.
- `contains` matches what is really in the file.
- The file's SHA-256 and size match what is downloaded, for the primary URL and for every mirror.
- A `.sbapack` is a zip with `sbapack.json` and `overlay/` (or a native `.so`) at its top.
- Pull requests do not change `index.json` or `stats.json`.
- Mirrors are `https` URLs and do not repeat the primary one.
- `previousVersions` are unique, newest first, and each one is audited for its own version.
- Every dependency (and every `requires` entry) is a mod in this repository, with no cycles and `min` not above `max`.
- Icons and screenshots are files under `images/<id>/`: png, jpg or webp, at most 1 MB each, at most 8 screenshots.
- `index.json` is regenerated.
