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
4. Rebuild the index and validate:
   ```
   python3 scripts/build_index.py
   python3 scripts/validate.py
   python3 scripts/verify_downloads.py mods/<id>.json
   ```

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
- Mirrors are `https` URLs and do not repeat the primary one.
- `previousVersions` are unique, newest first, and each one is audited for its own version.
- Every dependency (and every `requires` entry) is a mod in this repository, with no cycles and `min` not above `max`.
- Icons and screenshots are files under `images/<id>/`: png, jpg or webp, at most 1 MB each, at most 8 screenshots.
- `index.json` is regenerated.
