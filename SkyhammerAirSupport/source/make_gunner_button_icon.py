# The terminal's GUNNER SEAT button icon (2026-10-24, the user's pick: an AC-130 seen from above,
# nose up, four engines, inside a broken diamond sight). White on clear, drawn in the button's
# colour (black on its amber panel): 42/media/ui/SH_Btn_GunnerSeat.png, 64x64, drawn ~20-30 px.
# Run: <codex python> -I source/make_gunner_button_icon.py
import os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "42", "media", "ui", "SH_Btn_GunnerSeat.png")
N = 1024                      # drawn large, scaled down for clean edges
im = Image.new("L", (N, N), 0)
d = ImageDraw.Draw(im)
W = 255
c = N / 2

# the broken diamond: its four sides, the corners left open, and a sight tick across each corner
# along its axis
r, t = 410, 30
pts = [(c, c - r), (c + r, c), (c, c + r), (c - r, c)]
for i in range(4):
    (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % 4]
    a, b = 0.16, 0.84
    d.line([(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)], fill=W, width=t)
for (x, y), (dx, dy) in zip(pts, ((0, -1), (1, 0), (0, 1), (-1, 0))):
    d.line([(x - dx * 40, y - dy * 40), (x + dx * 95, y + dy * 95)], fill=W, width=t)

# the aircraft, nose up
fw = 64                                   # fuselage half width
d.rounded_rectangle([c - fw, c - 300, c + fw, c + 250], radius=fw, fill=W)
d.polygon([(c - fw, c - 250), (c, c - 330), (c + fw, c - 250)], fill=W)            # nose
d.polygon([(c - fw, c + 180), (c - 22, c + 310), (c + 22, c + 310), (c + fw, c + 180)], fill=W)  # tail cone
# the high straight wing, a little tapered
d.polygon([(c - 340, c - 40), (c + 340, c - 40), (c + 330, c + 22), (c - 330, c + 22)], fill=W)
# four engines ahead of the wing
for ex in (-245, -130, 130, 245):
    d.rounded_rectangle([c + ex - 24, c - 120, c + ex + 24, c + 10], radius=20, fill=W)
# the tailplane
d.polygon([(c - 165, c + 205), (c + 165, c + 205), (c + 155, c + 255), (c - 155, c + 255)], fill=W)

alpha = im.resize((64, 64), Image.LANCZOS)
icon = Image.merge("RGBA", (Image.new("L", (64, 64), 255),) * 3 + (alpha,))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
icon.save(OUT)
print("wrote", os.path.normpath(OUT))
