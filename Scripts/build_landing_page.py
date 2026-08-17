#!/usr/bin/env python3
"""Build Landing/index.html from Landing/index.template.html, embedding a
representative click sample from each pack as a base64 data URI so the page
itself can play real Tappy sounds (no server, no external files).

Run: python3 Scripts/build_landing_page.py
"""
import base64
import io
import json
import os
from html import escape

from PIL import Image

ROOT = os.path.join(os.path.dirname(__file__), "..")
SOUNDS_DIR = os.path.join(ROOT, "Sources", "Tappy", "Resources", "sounds")
ICON_PATH = os.path.join(ROOT, "AppIcon", "icon_1024.png")
UPI_QR_PATH = os.path.join(ROOT, "AppIcon", "upi_qr.png")
QRCODE_LIB_PATH = os.path.join(ROOT, "Scripts", "vendor", "qrcode-generator.js")
CHANGELOG_PATH = os.path.join(ROOT, "CHANGELOG.json")
TEMPLATE_PATH = os.path.join(ROOT, "Landing", "index.template.html")
OUT_PATH = os.path.join(ROOT, "Landing", "index.html")


def format_date(iso_date):
    from datetime import datetime
    return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%B %-d, %Y")


def build_changelog_html(entries):
    blocks = []
    for entry in entries:
        items = "\n".join(f"        <li>{escape(h)}</li>" for h in entry["highlights"])
        blocks.append(
            f'      <div class="changelog-entry">\n'
            f'        <div class="changelog-entry-head">\n'
            f'          <span class="changelog-version">v{escape(entry["version"])}</span>\n'
            f'          <span class="changelog-date">{format_date(entry["date"])}</span>\n'
            f'        </div>\n'
            f'        <ul>\n{items}\n        </ul>\n'
            f'      </div>'
        )
    return "\n".join(blocks)

# placeholder -> pack directory name
PACKS = {
    "__CHERRY_MX_BLUE__": "Cherry MX Blue",
    "__GAMING_CLICK__": "Gaming Click",
    "__LOGITECH_TYPING__": "Logitech Typing",
    "__COMPUTER_KEYBOARD__": "Computer Keyboard",
    "__TYPEWRITER__": "Typewriter",
    "__APPLE_MACBOOK__": "Apple MacBook",
}


def main():
    with open(TEMPLATE_PATH) as f:
        html = f.read()

    for placeholder, pack_name in PACKS.items():
        sample_path = os.path.join(SOUNDS_DIR, pack_name, "click_down_0.wav")
        with open(sample_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        if placeholder not in html:
            print(f"WARNING: placeholder {placeholder} not found in template")
        html = html.replace(placeholder, b64)

    favicon = Image.open(ICON_PATH).convert("RGBA").resize((64, 64), Image.LANCZOS)
    buf = io.BytesIO()
    favicon.save(buf, format="PNG")
    favicon_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    html = html.replace("__FAVICON__", f"data:image/png;base64,{favicon_b64}")

    with open(UPI_QR_PATH, "rb") as f:
        upi_qr_b64 = base64.b64encode(f.read()).decode("ascii")
    html = html.replace("__UPI_QR__", f"data:image/png;base64,{upi_qr_b64}")

    with open(QRCODE_LIB_PATH) as f:
        qrcode_lib_js = f.read()
    html = html.replace("__QRCODE_LIB__", qrcode_lib_js)

    with open(CHANGELOG_PATH) as f:
        changelog = json.load(f)
    latest = changelog[0]
    html = html.replace("__CURRENT_VERSION__", latest["version"])
    html = html.replace("__CURRENT_VERSION_DATE__", format_date(latest["date"]))
    html = html.replace("__CHANGELOG_HTML__", build_changelog_html(changelog))

    with open(OUT_PATH, "w") as f:
        f.write(html)

    print(f"Wrote {OUT_PATH} ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
