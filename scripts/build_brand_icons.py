#!/usr/bin/env python3
"""Rebuild the code-authored Orion favicon in square browser/search sizes."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / 'assets/brand'
BLUE = '#124ca1'
SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><title>СК Орион</title><rect width="512" height="512" rx="96" fill="#124ca1"/><ellipse cx="224" cy="250" rx="132" ry="162" fill="white"/><ellipse cx="224" cy="250" rx="76" ry="104" fill="#124ca1"/><circle cx="400" cy="380" r="29" fill="white"/></svg>\n'''

def main():
    BRAND.mkdir(parents=True, exist_ok=True)
    (ROOT / 'favicon.svg').write_text(SVG)
    scale = 4
    image = Image.new('RGBA', (512 * scale, 512 * scale))
    draw = ImageDraw.Draw(image)
    def box(values):
        return tuple(round(value * scale) for value in values)
    draw.rounded_rectangle(box((0, 0, 512, 512)), radius=96 * scale, fill=BLUE)
    draw.ellipse(box((92, 88, 356, 412)), fill='white')
    draw.ellipse(box((148, 146, 300, 354)), fill=BLUE)
    draw.ellipse(box((371, 351, 429, 409)), fill='white')
    for size in (120, 180, 192, 512):
        image.resize((size, size), Image.Resampling.LANCZOS).save(BRAND / f'orion-{size}.png')
    image.resize((256, 256), Image.Resampling.LANCZOS).save(ROOT / 'favicon.ico', format='ICO', sizes=[(16, 16), (32, 32), (48, 48)])
    print('Orion SVG, ICO and square PNG icons rebuilt.')

if __name__ == '__main__':
    main()
