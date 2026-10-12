"""Generate PWA icons (no network, Pillow only).

Usage:  python scripts/gen_icons.py
Writes: frontend/public/icons/icon-{512,192,180}.png + favicon.svg
"""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1] / "frontend" / "public"
BG = (7, 11, 18, 255)
GREEN = (34, 197, 94, 255)
WHITE = (248, 250, 252, 255)


def draw(size: int, rounded: bool) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if rounded:
        d.rounded_rectangle([0, 0, size - 1, size - 1], radius=size // 5, fill=BG)
    else:
        d.rectangle([0, 0, size - 1, size - 1], fill=BG)
    c, r = size / 2, size * 0.30
    d.ellipse([c - r, c - r, c + r, c + r], fill=GREEN)
    d.ellipse([c - r * 0.62, c - r * 0.62, c + r * 0.62, c + r * 0.62], fill=WHITE)
    for k in range(5):
        import math
        angle = -math.pi / 2 + k * 2 * math.pi / 5
        x1, y1 = c + r * 0.62 * math.cos(angle), c + r * 0.62 * math.sin(angle)
        x2, y2 = c + r * 0.30 * math.cos(angle), c + r * 0.30 * math.sin(angle)
        d.line([x1, y1, x2, y2], fill=BG, width=max(2, size // 64))
    return img


def main() -> None:
    out = ROOT / "icons"
    out.mkdir(parents=True, exist_ok=True)
    draw(512, rounded=False).save(out / "icon-512-maskable.png")
    draw(512, rounded=True).save(out / "icon-512.png")
    draw(192, rounded=True).save(out / "icon-192.png")
    draw(180, rounded=True).save(out / "apple-touch-icon.png")
    (ROOT / "favicon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="13" fill="#070B12"/>'
        '<circle cx="32" cy="32" r="19" fill="#22C55E"/>'
        '<circle cx="32" cy="32" r="12" fill="#F8FAFC"/></svg>\n'
    )
    print(f"icons written to {out}")


if __name__ == "__main__":
    raise SystemExit(main())
