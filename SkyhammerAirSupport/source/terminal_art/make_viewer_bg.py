"""The 3D look-around's background (2026-11-23, the user's pick from viewer_bg_mockups.py: "A",
the inspection display): a slate blue-grey screen lighter in the middle, a floor grid in
perspective and the turntable's amber ring with a tick every 30 deg. Skyhammer_Viewer.lua stretches
it over the whole panel and draws the corner brackets itself (crisp at any size). Made at 1024 x 658
(the default panel's 666 x 428 shape, room to grow). Writes 42/media/ui/SH_Viewer_Bg.png.
Codex python: python -I make_viewer_bg.py"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / '42/media/ui/SH_Viewer_Bg.png'
W, H = 1024, 658
K = W / 666                          # line widths as in the mock-up at 666 px
ACCENT = (220, 182, 94)

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
u, v = xx / W, yy / H
t = v[..., None]
a = np.array((70, 84, 94), np.float32) * (1 - t) + np.array((40, 48, 54), np.float32) * t
d = np.sqrt(((u - 0.5) / 0.62) ** 2 + ((v - 0.52) / 0.72) ** 2)
a += (np.clip(1 - d, 0, 1) ** 1.6)[..., None] * np.array((62, 70, 74), np.float32)
img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')

over = Image.new('RGBA', (W, H))
g = ImageDraw.Draw(over)
lw = max(1, round(K))
# the floor grid: rays to the middle of the horizon, rows closer together towards it
hy = 0.60 * H
for k in range(19):
    x0 = (k / 18 - 0.5) * W * 3.2 + W * 0.5
    g.line([(W * 0.5, hy), (x0, H)], fill=(170, 200, 210, 70), width=lw)
for k in range(1, 10):
    f = (k / 9) ** 2.2
    y = hy + (H - hy) * f
    g.line([(0, y), (W, y)], fill=(170, 200, 210, int(70 * (0.35 + 0.65 * f))), width=lw)
# the turntable ring under the aircraft
cx, cy, rx, ry = W * 0.5, H * 0.78, W * 0.36, H * 0.075
g.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=ACCENT + (150,), width=round(2 * K))
for k in range(12):
    ang = np.radians(k * 30)
    x, y = cx + rx * np.cos(ang), cy + ry * np.sin(ang)
    g.line([(x, y - 4 * K), (x, y + 4 * K)], fill=ACCENT + (170,), width=round(2 * K))
img.alpha_composite(over)
img.convert('RGB').save(OUT, optimize=True)
print(OUT, img.size, OUT.stat().st_size, 'bytes')
