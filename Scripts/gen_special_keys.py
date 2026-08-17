#!/usr/bin/env python3
"""Generate space/enter down+up variants for each pack -- physically larger
keys hit a stabilizer bar, producing a deeper, louder hit than a regular
alpha key: lower tick frequency, more body/impulse energy, longer decay.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from gen_click import make_click, _default_up_variant  # noqa: E402

SOUNDS_DIR = os.path.join(os.path.dirname(__file__), "..", "Sources", "Tappy", "Resources", "sounds")

# Derived from each pack's first click spec: lower tick freq, more body/impulse, longer decay.
# Synthesized packs (Cherry Black, iPhone Click, and 6 before them) were
# dropped in favor of real CC0 recordings -- see assemble_freesound_packs.py.
# Kept empty rather than deleted in case synthesis is ever worth revisiting.
SPECIAL_KEY_SPECS = {}
DELETE_KEY_SPECS = {}


def main():
    for pack_name, down_spec in SPECIAL_KEY_SPECS.items():
        pack_dir = os.path.join(SOUNDS_DIR, pack_name)
        os.makedirs(pack_dir, exist_ok=True)

        make_click(os.path.join(pack_dir, "space_down_0.wav"), seed=501, target_peak=0.55, **down_spec)
        make_click(os.path.join(pack_dir, "enter_down_0.wav"), seed=907, target_peak=0.55, **down_spec)

        up_spec = _default_up_variant(down_spec)
        make_click(os.path.join(pack_dir, "space_up_0.wav"), seed=502, **up_spec)
        make_click(os.path.join(pack_dir, "enter_up_0.wav"), seed=908, **up_spec)

        print(f"Wrote space/enter down+up variants for '{pack_name}'")

    for pack_name, down_spec in DELETE_KEY_SPECS.items():
        pack_dir = os.path.join(SOUNDS_DIR, pack_name)
        os.makedirs(pack_dir, exist_ok=True)

        make_click(os.path.join(pack_dir, "delete_down_0.wav"), seed=1301, target_peak=0.55, **down_spec)
        up_spec = _default_up_variant(down_spec)
        make_click(os.path.join(pack_dir, "delete_up_0.wav"), seed=1302, **up_spec)

        print(f"Wrote delete down+up variant for '{pack_name}'")


if __name__ == "__main__":
    main()
