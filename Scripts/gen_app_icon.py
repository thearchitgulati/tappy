#!/usr/bin/env python3
"""Generate Tappy's app icon: a white keycap with a bold "t" on a diagonal
pink -> orange -> purple -> blue gradient rounded square, with three motion
dashes at the upper right signaling a tap/click. Matches the brand reference
(gradient squircle + glossy keycap + tap dashes) supplied by the user.
Produces a 1024x1024 master PNG plus a full .iconset and .icns.
"""
import os
import subprocess

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SIZE = 1024
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "AppIcon")
FONT_PATH = "/System/Library/Fonts/SFNSRounded.ttf"

# Corner colors for the diagonal brand gradient (top-left, top-right,
# bottom-left, bottom-right), matching the supplied branding reference.
CORNER_TL = (255, 91, 145)   # pink/magenta
CORNER_TR = (255, 149, 45)   # orange
CORNER_BL = (66, 110, 255)   # blue
CORNER_BR = (139, 61, 216)   # purple

KEYCAP_BASE = (26, 24, 40)   # near-black navy, keycap bezel/base + glyph color


def bilerp(c00, c10, c01, c11, tx, ty):
    top = tuple(c00[i] + (c10[i] - c00[i]) * tx for i in range(3))
    bot = tuple(c01[i] + (c11[i] - c01[i]) * tx for i in range(3))
    return tuple(int(top[i] + (bot[i] - top[i]) * ty) for i in range(3))


def rounded_mask(size, radius):
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


def make_background():
    grad = Image.new("RGB", (SIZE, SIZE))
    pixels = grad.load()
    for y in range(SIZE):
        ty = y / (SIZE - 1)
        for x in range(SIZE):
            tx = x / (SIZE - 1)
            pixels[x, y] = bilerp(CORNER_TL, CORNER_TR, CORNER_BL, CORNER_BR, tx, ty)

    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    corner_radius = int(SIZE * 0.225)
    img.paste(grad, (0, 0), rounded_mask(SIZE, corner_radius))
    return img


def add_top_sheen(img):
    sheen = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(sheen).ellipse(
        [-SIZE * 0.3, -SIZE * 0.6, SIZE * 1.3, SIZE * 0.5], fill=(255, 255, 255, 30)
    )
    sheen = sheen.filter(ImageFilter.GaussianBlur(70))
    corner_radius = int(SIZE * 0.225)
    return Image.composite(Image.alpha_composite(img, sheen), img, rounded_mask(SIZE, corner_radius))


def draw_tap_dashes(img):
    """Three short parallel motion dashes at the upper right, echoing a tap."""
    overlay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    ox, oy = int(SIZE * 0.665), int(SIZE * 0.225)
    length = int(SIZE * 0.10)
    width = int(SIZE * 0.028)
    gap = int(SIZE * 0.075)
    # Dash direction: pointing up-and-right, at roughly -35deg.
    import math
    angle = math.radians(-38)
    dx, dy = math.cos(angle), math.sin(angle)
    perp_x, perp_y = math.cos(angle + math.pi / 2), math.sin(angle + math.pi / 2)
    for i, alpha in enumerate((255, 235, 200)):
        cx = ox + perp_x * gap * i
        cy = oy + perp_y * gap * i
        x0, y0 = cx - dx * length / 2, cy - dy * length / 2
        x1, y1 = cx + dx * length / 2, cy + dy * length / 2
        odraw.line([x0, y0, x1, y1], fill=(255, 255, 255, alpha), width=width)
    overlay = overlay.filter(ImageFilter.GaussianBlur(1))
    # Round the dash ends by drawing circles at the endpoints too (line caps
    # in Pillow are flat, not round).
    for i, alpha in enumerate((255, 235, 200)):
        cx = ox + perp_x * gap * i
        cy = oy + perp_y * gap * i
        x0, y0 = cx - dx * length / 2, cy - dy * length / 2
        x1, y1 = cx + dx * length / 2, cy + dy * length / 2
        r = width / 2
        odraw.ellipse([x0 - r, y0 - r, x0 + r, y0 + r], fill=(255, 255, 255, alpha))
        odraw.ellipse([x1 - r, y1 - r, x1 + r, y1 + r], fill=(255, 255, 255, alpha))
    img.alpha_composite(overlay)
    return img


def draw_keycap(img):
    """A single centered glossy keycap with a dark bezel/base and a bold
    lowercase 't' glyph, styled after the supplied branding reference."""
    cap_size = int(SIZE * 0.44)
    cap_radius = int(cap_size * 0.24)
    cx, cy = SIZE // 2, int(SIZE * 0.56)
    left = cx - cap_size // 2
    top = cy - cap_size // 2

    # Drop shadow onto the background.
    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [left - 6, top + 26, left + cap_size - 6, top + cap_size + 26],
        radius=cap_radius, fill=(0, 0, 0, 120)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(30))
    img = Image.alpha_composite(img, shadow)

    # Dark bezel/base peeking out from beneath the cap.
    base = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(base).rounded_rectangle(
        [left, top + 16, left + cap_size, top + cap_size + 16],
        radius=cap_radius, fill=(*KEYCAP_BASE, 255)
    )
    img = Image.alpha_composite(img, base)

    # Glossy white face with a soft top-to-bottom gradient.
    face = Image.new("RGBA", (cap_size, cap_size), (0, 0, 0, 0))
    fpixels = face.load()
    top_color = (255, 255, 255)
    bottom_color = (226, 226, 236)
    for y in range(cap_size):
        t = y / cap_size
        color = tuple(int(top_color[i] + (bottom_color[i] - top_color[i]) * t) for i in range(3))
        for x in range(cap_size):
            fpixels[x, y] = (*color, 255)
    face_mask = rounded_mask(cap_size, cap_radius)
    img.paste(face, (left, top), face_mask)

    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        [left, top, left + cap_size, top + cap_size],
        radius=cap_radius, outline=(210, 210, 222, 160), width=3
    )

    # Bold rounded "t" glyph, centered on the face.
    font = ImageFont.truetype(FONT_PATH, int(cap_size * 0.62))
    try:
        font.set_variation_by_name("Bold")
    except Exception:
        pass
    glyph = "t"
    bbox = draw.textbbox((0, 0), glyph, font=font)
    gw, gh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    gx = cx - gw / 2 - bbox[0]
    gy = cy - gh / 2 - bbox[1] - int(cap_size * 0.02)
    draw.text((gx, gy), glyph, font=font, fill=(*KEYCAP_BASE, 255))

    return img


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    img = make_background()
    img = add_top_sheen(img)
    img = draw_tap_dashes(img)
    img = draw_keycap(img)

    master_path = os.path.join(OUT_DIR, "icon_1024.png")
    img.save(master_path)
    print(f"Wrote {master_path}")

    iconset_dir = os.path.join(OUT_DIR, "AppIcon.iconset")
    os.makedirs(iconset_dir, exist_ok=True)
    sizes = [16, 32, 128, 256, 512]
    for s in sizes:
        img.resize((s, s), Image.LANCZOS).save(os.path.join(iconset_dir, f"icon_{s}x{s}.png"))
        img.resize((s * 2, s * 2), Image.LANCZOS).save(os.path.join(iconset_dir, f"icon_{s}x{s}@2x.png"))

    icns_path = os.path.join(OUT_DIR, "AppIcon.icns")
    subprocess.run(["iconutil", "-c", "icns", iconset_dir, "-o", icns_path], check=True)
    print(f"Wrote {icns_path}")


if __name__ == "__main__":
    main()
