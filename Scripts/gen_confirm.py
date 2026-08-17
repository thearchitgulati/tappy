#!/usr/bin/env python3
"""Generate copy/paste confirmation chimes for each real sample-based pack.

Modeled on the reference clip the user provided (a single soft attack
followed by a longer bell-like ring, ~250ms), rather than the short quick
sweep used in the first synthesized-click pass.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from gen_click import make_pop  # noqa: E402

SOUNDS_DIR = os.path.join(os.path.dirname(__file__), "..", "Sources", "Tappy", "Resources", "sounds")

PACKS = ["Mechanical A", "Mechanical B", "Mechanical Studio", "iPhone Keys"]


def main():
    for pack_name in PACKS:
        pack_dir = os.path.join(SOUNDS_DIR, pack_name)
        os.makedirs(pack_dir, exist_ok=True)

        # Pickup (copy): soft tap + rising bell tail.
        make_pop(
            os.path.join(pack_dir, "confirm_copy.wav"),
            freq_start=600,
            freq_end=950,
            duration=0.26,
            decay=9,
            transient_amount=0.28,
        )
        # Drop (paste): soft tap + falling bell tail with a light thud settling in.
        make_pop(
            os.path.join(pack_dir, "confirm_paste.wav"),
            freq_start=950,
            freq_end=560,
            duration=0.3,
            decay=8,
            transient_amount=0.25,
            thud=True,
        )
        print(f"Wrote confirm sounds for '{pack_name}'")


if __name__ == "__main__":
    main()
