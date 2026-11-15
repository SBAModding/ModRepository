#!/usr/bin/env python3
"""Builds index.json from mods/*.json. The index is what the loader fetches; never edit it by hand."""
import json

from common import INDEX, load_mods


def build():
    mods = [m for _, m in load_mods()]
    mods.sort(key=lambda m: m["id"])
    for m in mods:
        # Loaders before 0.0.3 only know `requires`, a plain list of ids. Keep it in step with `dependencies`.
        if "dependencies" in m:
            m["requires"] = [d["id"] for d in m["dependencies"]]
    return {"schemaVersion": 1, "mods": mods}


if __name__ == "__main__":
    INDEX.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n")
    print(f"wrote index.json ({len(build()['mods'])} mods)")
