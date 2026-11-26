"""Mock-ups of the 3D look-around's background (Skyhammer_Viewer.lua), with real turntable frames on
top, at the viewer's default size (the sensor map's place in a 960 x 600 terminal: 666 x 428).
Writes turntable/viewer_bg_mockups.png. Codex python: python -I viewer_bg_mockups.py"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
UI = HERE.parents[1] / '42/media/ui'
W, H = 666, 428
PAD, TOP, BOTTOM = 12, 12 + 29 + 8, 12 + 19 + 8
TEXT, DIM, ACCENT, LINE = (226, 229, 226), (162, 170, 171), (220, 182, 94), (75, 83, 85)
FONT_T = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 20)
FONT_S = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 13)
rng = np.random.default_rng(7)

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
u, v = xx / W, yy / H


def to_img(a):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB')


def grad(top, bottom, ys=v):
    t = ys[..., None]
    return np.array(top, np.float32) * (1 - t) + np.array(bottom, np.float32) * t


def radial(cx, cy, rx, ry):
    d = np.sqrt(((u - cx) / rx) ** 2 + ((v - cy) / ry) ** 2)
    return np.clip(1 - d, 0, 1) ** 1.6


def noise(scale, octaves=5, seed=0):
    r = np.random.default_rng(seed)
    out = np.zeros((H, W), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        s = max(2, int(scale * 2 ** o))
        small = r.random((s, max(2, int(s * W / H)))).astype(np.float32)
        big = np.array(Image.fromarray((small * 255).astype(np.uint8)).resize((W, H), Image.Resampling.BICUBIC), np.float32) / 255
        out += big * amp
        total += amp
        amp *= 0.5
    return out / total


def perspective_grid(d, horizon, color, alpha, n_rays=19, n_rows=9, vx=0.5):
    """floor lines below the horizon, meeting at (vx, horizon)"""
    hy = horizon * H
    for k in range(n_rays):
        x0 = (k / (n_rays - 1) - 0.5) * W * 3.2 + W * vx
        d.line([(W * vx, hy), (x0, H)], fill=color + (alpha,), width=1)
    for k in range(1, n_rows + 1):
        t = (k / n_rows) ** 2.2
        y = hy + (H - hy) * t
        d.line([(0, y), (W, y)], fill=color + (int(alpha * (0.35 + 0.65 * t)),), width=1)


def brackets(d, col, inset=8, arm=18, width=2):
    for (x, y, sx, sy) in ((inset, inset, 1, 1), (W - inset - 1, inset, -1, 1), (inset, H - inset - 1, 1, -1), (W - inset - 1, H - inset - 1, -1, -1)):
        d.line([(x, y), (x + sx * arm, y)], fill=col, width=width)
        d.line([(x, y), (x, y + sy * arm)], fill=col, width=width)


# ------------------------------------------------------------------ the four backgrounds
def bg_display():
    """A: the inspection display, lighter: slate blue-grey, a soft light in the middle, a floor grid"""
    a = grad((70, 84, 94), (40, 48, 54))
    a += radial(0.5, 0.52, 0.62, 0.72)[..., None] * np.array((62, 70, 74), np.float32)
    img = to_img(a).convert('RGBA')
    over = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(over)
    perspective_grid(d, 0.60, (170, 200, 210), 70)
    # the turntable ring under the aircraft, a tick every 30 deg
    cx, cy, rx, ry = W * 0.5, H * 0.78, W * 0.36, H * 0.075
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=ACCENT + (150,), width=2)
    for k in range(12):
        ang = np.radians(k * 30)
        x, y = cx + rx * np.cos(ang), cy + ry * np.sin(ang)
        d.line([(x, y - 4), (x, y + 4)], fill=ACCENT + (170,), width=2)
    # scan lines
    for y in range(0, H, 3):
        d.line([(0, y), (W, y)], fill=(0, 0, 0, 14))
    img.alpha_composite(over)
    d = ImageDraw.Draw(img)
    brackets(d, ACCENT + (230,))
    return img, None


def bg_sky():
    """B: in flight: a muted daytime sky, clouds below (the renders are without landing gear)"""
    a = grad((96, 128, 160), (182, 196, 206), np.clip(v * 1.15, 0, 1))
    n = noise(3, 6, seed=3)
    band = np.clip((v - 0.35) / 0.65, 0, 1)
    cloud = np.clip((n - 0.52 + band * 0.18) * 3.2, 0, 1) * (0.25 + 0.75 * band)
    a = a * (1 - cloud[..., None] * 0.85) + np.array((236, 238, 240), np.float32) * cloud[..., None] * 0.85
    a *= (1 - 0.25 * (np.sqrt((u - 0.5) ** 2 + (v - 0.5) ** 2) / 0.71) ** 2)[..., None]
    return to_img(a).convert('RGBA'), None


def bg_hangar():
    """C: a hangar's mood: a dark ribbed wall, lights at the top, a concrete floor with a yellow line
    and the aircraft's soft shadow on it (it is shown hanging above the floor)"""
    horizon = 0.56
    wall = grad((40, 43, 46), (64, 67, 69), np.clip(v / horizon, 0, 1))
    ribs = (np.sin(u * np.pi * 22) > 0.86).astype(np.float32)[..., None] * 10
    wall = wall - ribs
    floor_t = np.clip((v - horizon) / (1 - horizon), 0, 1)
    concrete = grad((96, 98, 97), (128, 130, 128), floor_t) + (noise(18, 4, seed=5)[..., None] - 0.5) * 26
    a = np.where((v < horizon)[..., None], wall, concrete)
    # the overhead lights: a pool of light on the floor and the glow up top
    a += radial(0.5, 0.80, 0.55, 0.35)[..., None] * 48
    a += radial(0.5, 0.0, 0.5, 0.30)[..., None] * 40
    img = to_img(a).convert('RGBA')
    d = ImageDraw.Draw(img)
    glow = Image.new('RGBA', (W, H))
    g = ImageDraw.Draw(glow)
    for lx in (0.2, 0.5, 0.8):
        g.rectangle([W * lx - 40, 2, W * lx + 40, 9], fill=(255, 248, 220, 255))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(6)))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(1.5)))
    hy = horizon * H
    for off in (-1, 1):
        d.line([(W * 0.5 + off * 3, hy), (W * 0.5 + off * 40, H)], fill=(205, 168, 60, 255), width=3)
    d.line([(0, hy), (W, hy)], fill=(30, 32, 34, 255), width=2)
    return img, 'shadow'


def bg_blueprint():
    """D: a blueprint: blue paper, fine and major grid"""
    a = grad((30, 70, 108), (22, 54, 86)) + radial(0.5, 0.5, 0.7, 0.8)[..., None] * 22
    img = to_img(a).convert('RGBA')
    over = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(over)
    for x in range(0, W, 16):
        d.line([(x, 0), (x, H)], fill=(255, 255, 255, 40 if x % 80 == 0 else 16))
    for y in range(0, H, 16):
        d.line([(0, y), (W, y)], fill=(255, 255, 255, 40 if y % 80 == 0 else 16))
    img.alpha_composite(over)
    return img, None


# ------------------------------------------------------------------ the viewer on top
def cell(name, frame):
    sheet = Image.open(UI / f'SH_Spin_{name}.png').convert('RGBA')
    cw, ch = sheet.width // 4, sheet.height // 9
    c, r = frame % 4, frame // 4
    return sheet.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch))


def panel(bg, extra, name, frame, title, edge_line=True):
    img = bg.copy()
    bw, bh = W - PAD * 2, H - TOP - BOTTOM
    art = cell(name, frame)
    s = min(bw / art.width, bh / art.height, 2)
    art = art.resize((int(art.width * s), int(art.height * s)), Image.Resampling.LANCZOS)
    x, y = PAD + (bw - art.width) // 2, TOP + (bh - art.height) // 2
    if extra == 'shadow':
        sh = Image.new('RGBA', (W, H))
        alpha = art.getchannel('A').resize((int(art.width * 0.85), max(1, art.height // 5)))
        blob = Image.new('RGBA', alpha.size, (0, 0, 0, 0))
        blob.putalpha(alpha.point(lambda a: int(a * 0.40)))
        sh.alpha_composite(blob, (x + int(art.width * 0.075), int(H * 0.82) - alpha.height // 2))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(9)))
    img.alpha_composite(art, (x, y))
    d = ImageDraw.Draw(img)
    # the title (with a dark backing so it reads on a light background), the hint, the X
    for ox, oy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        d.text((PAD + ox, PAD - 2 + oy), title, font=FONT_T, fill=(10, 12, 14, 200))
    d.text((PAD, PAD - 2), title, font=FONT_T, fill=TEXT + (255,))
    hint = '드래그해서 기체를 돌려 보세요.'
    for ox, oy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        d.text((PAD + ox, H - PAD - 19 + oy), hint, font=FONT_S, fill=(10, 12, 14, 200))
    d.text((PAD, H - PAD - 19), hint, font=FONT_S, fill=DIM + (255,))
    s = 27
    d.rectangle([W - s - 8, 8, W - 8, 8 + s], fill=(23, 28, 30, 255), outline=LINE + (255,))
    d.text((W - 8 - s / 2, 8 + s / 2), 'X', font=FONT_S, fill=TEXT + (255,), anchor='mm')
    if edge_line:
        d.rectangle([0, 0, W - 1, H - 1], outline=LINE + (255,))
    return img


rows = [('A  점검 화면 (밝게)', bg_display()), ('B  하늘 (비행 중)', bg_sky()),
        ('C  격납고 분위기', bg_hangar()), ('D  청사진', bg_blueprint())]
GAP, LABEL = 14, 34
sheet = Image.new('RGBA', (W * 2 + GAP * 3, (H + LABEL + GAP) * len(rows) + GAP), (16, 20, 22, 255))
lab = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 22)
y = GAP
for name, (bg, extra) in rows:
    d = ImageDraw.Draw(sheet)
    d.text((GAP, y), name, font=lab, fill=ACCENT + (255,))
    y += LABEL
    sheet.alpha_composite(panel(bg, extra, 'F22', 0, 'F-22 / 10기 편대'), (GAP, y))
    sheet.alpha_composite(panel(bg, extra, 'B2', 3, 'B-2 / 융단폭격'), (GAP * 2 + W, y))
    y += H + GAP
out = HERE / 'turntable' / 'viewer_bg_mockups.png'
sheet.convert('RGB').save(out)
print(out, sheet.size)
