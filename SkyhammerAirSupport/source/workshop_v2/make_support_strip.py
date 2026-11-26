"""Skyhammer support strip: the five aircraft of the main mod on one wide card row, for the
Workshop description. Replaces TEXT-MAIN_aegis.png (assets sheet) and TEXT-KILLSTREAK_aegis.png:
almost no words (names, callsigns, calibres, prices), so it reads in any language; what each one
does is told in the description text, which Steam can translate.

Same look as make_killstreak_image.py: Windows Bahnschrift / Consolas (rasterized only, see the
licence note there), the same palette, the Apache / B-2 blueprints cropped from the user's
TEXT-MAIN_aegis.png. The A-10, AC-130 and F-22 blueprints are drawn here from the game's own
meshes (the outline and the creases of the airframe): the A-10 from the side, the AC-130 from the
front (2026-11-23: the old crop still had its landing gear down), the F-22 from above.
2026-11-23: the F-22 (Raven 1-1, 200 points) added as the fourth card; five columns.

Usage: <python with Pillow + numpy> make_support_strip.py
Writes SUPPORT-STRIP.png (1272 wide) and SUPPORT-STRIP_636.png (half size, as the description
column shows it) next to this script.
"""
from pathlib import Path
from functools import lru_cache
import math, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent
AIR = ROOT.parent / 'java' / 'skyhammer' / 'aircraft'
REF = Image.open(ROOT / 'TEXT-MAIN_aegis.png').convert('RGB')
assert REF.width == 887, 'blueprint crops are authored for the 887 px reference'

W, H, S = 1272, 584, 3
BG = '#101416'; PANEL = '#171C1E'; LINE = '#4B5355'; TEXT = '#E2E5E2'; MUTED = '#A2AAAB'; AMBER = '#DCB65E'
CYAN = (82, 196, 214); CRAFT = (173, 218, 228); GREEN = (96, 214, 120); HOT = (236, 146, 72)
FONTS = Path('C:/Windows/Fonts')
im = Image.new('RGB', (W * S, H * S), BG)
d = ImageDraw.Draw(im)


@lru_cache(None)
def font(size, weight=400, width=100, mono=False):
    f = ImageFont.truetype(str(FONTS / ('consola.ttf' if mono else 'bahnschrift.ttf')), round(size * S))
    if not mono: f.set_variation_by_axes([weight, width])
    return f
def measure(s, f): return d.textlength(s, font=f) / S
def P(v): return round(v * S)
def rect(box, fill=None, outline=None, width=1):
    d.rectangle(tuple(P(v) for v in box), fill=fill, outline=outline, width=max(1, P(width)))
def line(points, fill=LINE, width=1.0):
    d.line([(P(x), P(y)) for x, y in points], fill=fill, width=max(1, P(width)), joint='curve')
def ellipse(box, fill=None, outline=None, width=1.0):
    d.ellipse(tuple(P(v) for v in box), fill=fill, outline=outline, width=max(1, P(width)))
def text(s, x, y, f, fill=TEXT, align='left', limit=None):
    tw = measure(s, f)
    if limit is not None: assert tw <= limit + .2, (s, tw, limit)
    if align == 'right': x -= tw
    elif align == 'center': x -= tw / 2
    assert 0 <= x and x + tw <= W + .2, (s, x, tw)
    d.text((P(x), P(y)), s, font=f, fill=fill, anchor='lt')
def dashed_circle(cx, cy, r, fill, n=40, on=0.55, width=1.2):
    for k in range(n):
        a0 = k / n * 2 * math.pi; a1 = (k + on) / n * 2 * math.pi
        line([(cx + math.cos(a0) * r, cy + math.sin(a0) * r), (cx + math.cos(a1) * r, cy + math.sin(a1) * r)], fill, width)
def dashed_line(a, b, fill, dash=7, gap=5, width=1.6):
    L = math.dist(a, b); ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    t = 0
    while t < L:
        e = min(L, t + dash)
        line([(a[0] + ux * t, a[1] + uy * t), (a[0] + ux * e, a[1] + uy * e)], fill, width)
        t = e + gap
def arrow_head(tip, ux, uy, fill, size=8, width=1.8):
    px, py = -uy, ux
    line([(tip[0] - ux * size + px * size * .6, tip[1] - uy * size + py * size * .6), tip,
          (tip[0] - ux * size - px * size * .6, tip[1] - uy * size - py * size * .6)], fill, width)


# ---------------------------------------------------------------- blueprints
CROPS = {'apache': (65, 291, 531, 427), 'b2': (76, 1330, 524, 1429)}
def paste_mask(mask, box):
    x, y, w, h = box
    scale = min(w / mask.width, h / mask.height)
    size = (max(1, round(mask.width * scale * S)), max(1, round(mask.height * scale * S)))
    mask = mask.resize(size, Image.Resampling.LANCZOS)
    im.paste(Image.new('RGB', size, CRAFT), (P(x + (w - size[0] / S) / 2), P(y + (h - size[1] / S) / 2)), mask)
def blueprint(key, box):
    a = np.asarray(REF.crop(CROPS[key]), dtype=float)
    alpha = np.clip((a.max(axis=2) - 65) / 125, 0, 1) * 255
    if key == 'b2': alpha[:22, :90] = 0     # (a stray label of the old inset)
    paste_mask(Image.fromarray(alpha.astype('uint8')).filter(ImageFilter.MaxFilter(3)), box)

# game space of the meshes: X across the wings, Y up, nose toward +Z. Each view: the image x and y
# of a point, and the axis a silhouette is seen along.
VIEWS = {'side': (lambda p: -p[2], lambda p: -p[1], 0),     # left side, nose left (as the Apache)
         'front': (lambda p: p[0], lambda p: -p[1], 2),     # nose on
         'top': (lambda p: -p[2], lambda p: p[0], 1)}       # from above, nose left
def mesh_blueprint(name, view, box, skip_parts=()):
    """An aircraft from its mesh: edges where the surface creases (> 28 degrees), the silhouette,
    and open edges."""
    b = (AIR / name).read_bytes()
    assert struct.unpack('>i', b[:4])[0] == 0x53484131
    n = struct.unpack('>i', b[4:8])[0]
    v = np.frombuffer(b, '>f4', n * 10, 8).reshape(-1, 10).astype(float)
    v = v[~np.isin(np.repeat(v[0::3, 9], 3), skip_parts)]   # (part 5 of the AC-130: its muzzle flash)
    pos = v[:, 0:3].reshape(-1, 3, 3)
    ix, iy, axis = VIEWS[view]
    fn = np.cross(pos[:, 1] - pos[:, 0], pos[:, 2] - pos[:, 0])
    ln = np.linalg.norm(fn, axis=1); keep = ln > 1e-9
    pos, fn = pos[keep], fn[keep] / ln[keep, None]
    key = lambda p: tuple(np.round(p, 4))
    edges = {}
    for t in range(len(pos)):
        for i in range(3):
            a, c = key(pos[t, i]), key(pos[t, (i + 1) % 3])
            k = (a, c) if a < c else (c, a)
            edges.setdefault(k, []).append(t)
    segs = []
    for (a, c), faces in edges.items():
        draw = len(faces) != 2
        if not draw:
            n1, n2 = fn[faces[0]], fn[faces[1]]
            crease = np.dot(n1, n2) < math.cos(math.radians(28))
            silhouette = (n1[axis] > 0) != (n2[axis] > 0)    # seen along the view's axis
            draw = crease or silhouette
        if draw: segs.append((a, c))
    xs = [ix(p) for s in segs for p in s]; ys = [iy(p) for s in segs for p in s]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    w, h = box[2], box[3]
    sc = min(w / (x1 - x0), h / (y1 - y0))
    W2, H2 = max(1, round((x1 - x0) * sc * S)), max(1, round((y1 - y0) * sc * S))
    mask = Image.new('L', (W2 + 6, H2 + 6), 0); md = ImageDraw.Draw(mask)
    for a, c in segs:
        pa = ((ix(a) - x0) * sc * S + 3, (iy(a) - y0) * sc * S + 3)
        pc = ((ix(c) - x0) * sc * S + 3, (iy(c) - y0) * sc * S + 3)
        md.line([pa, pc], fill=255, width=max(1, round(S * 1.1)))
    paste_mask(mask, box)
    return len(segs)


# ---------------------------------------------------------------- tactical pictograms
def dots(points, fill=TEXT, r=2.4):
    for x, y in points: ellipse((x - r, y - r, x + r, y + r), fill=fill)
def you(x, y):
    ellipse((x - 7, y - 7, x + 7, y + 7), outline=GREEN, width=1.6); ellipse((x - 3.5, y - 3.5, x + 3.5, y + 3.5), fill=GREEN)
def picto(kind, x, y, w, h):
    cx, cy = x + w / 2, y + h / 2
    if kind == 'apache':                      # circles you, fires on its own
        dashed_circle(cx, cy, h * .36, CYAN)
        for a in (-.6, 2.3): arrow_head((cx + math.cos(a) * h * .36, cy + math.sin(a) * h * .36), -math.sin(a), math.cos(a), CYAN, 6, 1.4)
        dots([(cx - 52, cy - 22), (cx - 40, cy + 26), (cx + 30, cy - 34), (cx + 58, cy + 8), (cx - 70, cy + 4), (cx + 8, cy + 38)])
        for px, py in ((cx + 74, cy - 18), (cx + 86, cy + 2), (cx + 80, cy + 22)):
            ellipse((px - 7, py - 7, px + 7, py + 7), outline=HOT, width=1.4); dots([(px, py)], HOT, 2.2)
        you(cx, cy)
    elif kind == 'a10':                       # one mark, a straight run through the crowd, never near you
        ux, uy = math.cos(math.radians(-24)), math.sin(math.radians(-24))
        mx, my = cx + 28, cy + 2
        a = (mx - ux * 82, my - uy * 82); b = (mx + ux * 82, my + uy * 82)
        crowd = [(mx + ux * t + (-uy) * o, my + uy * t + ux * o) for t, o in ((-60, 5), (-38, -6), (-16, 4), (6, -4), (24, 7), (44, -5), (64, 3))]
        dots(crowd)
        dashed_line(a, b, HOT, width=2)
        arrow_head(b, ux, uy, HOT, 9, 2)
        for t in (-52, -30, -8, 14, 36, 58):
            px, py = mx + ux * t, my + uy * t
            ellipse((px - 5, py - 5, px + 5, py + 5), outline=HOT, width=1.1)
        gx, gy = x + 38, y + h - 30
        dashed_circle(gx, gy, 22, (70, 140, 92), n=24, width=1.0)    # the safe ring around you
        you(gx, gy)
    elif kind == 'ac130':                     # circles high, and 105mm where you mark
        dashed_circle(cx - 20, cy, h * .38, CYAN)
        you(cx - 20, cy)
        dots([(cx - 52, cy - 24), (cx - 4, cy + 30), (cx - 46, cy + 22)])
        ex, ey = cx + 62, cy - 6
        for ox, oy in ((0, 0), (-12, 9), (11, 10), (2, -13)):
            ellipse((ex + ox - 9, ey + oy - 9, ex + ox + 9, ey + oy + 9), outline=HOT, width=1.3)
        line([(ex - 20, ey), (ex + 20, ey)], HOT, 1.4); line([(ex, ey - 20), (ex, ey + 20)], HOT, 1.4)
        dots([(ex - 26, ey + 22), (ex + 24, ey - 22), (ex + 28, ey + 18)])
    elif kind == 'f22':                       # one mark, a wide strip laid through it, jets in trail along it
        ux, uy = math.cos(math.radians(-18)), math.sin(math.radians(-18))
        mx, my = cx + 18, cy
        at = lambda t, o: (mx + ux * t - uy * o, my + uy * t + ux * o)
        corners = [at(-96, -20), at(96, -20), at(96, 20), at(-96, 20)]
        for k in range(4): dashed_line(corners[k], corners[(k + 1) % 4], HOT, 6, 4, 1.2)
        dots([at(t, o) for t, o in ((-70, 14), (-44, -12), (-20, 6), (4, -15), (30, 12), (56, -6), (78, 10))])
        for t in range(-80, 81, 32):
            for o in (-9, 9):
                px, py = at(t, o)
                ellipse((px - 5, py - 5, px + 5, py + 5), fill=(92, 66, 40), outline=HOT, width=1)
        dashed_line(at(-112, 0), at(112, 0), CYAN, 7, 5, 1.4)        # the flight's track
        for t in (-40, 10, 60, 112): arrow_head(at(t, 0), ux, uy, CYAN, 6, 1.6)
        gx, gy = x + 34, y + 30
        dashed_circle(gx, gy, 22, (70, 140, 92), n=24, width=1.0)    # never passes near you
        you(gx, gy)
    else:                                     # b2: a wide marked area, carpet of bombs
        ax, ay, r = cx + 26, cy, h * .4
        dashed_circle(ax, ay, r, HOT, n=44)
        for k in range(11):
            a = k * 2.39996; rr = r * .82 * math.sqrt((k + .5) / 11)
            px, py = ax + math.cos(a) * rr, ay + math.sin(a) * rr
            ellipse((px - 7, py - 7, px + 7, py + 7), fill=(92, 66, 40), outline=HOT, width=1)
        you(x + 34, y + h - 26)
PICTO_W = 266          # the width the pictograms are drawn at (a card of the four-column strip)
def picto_fit(kind, x, y, w, h):
    """A pictogram drawn at PICTO_W x h on its own canvas, then scaled down to the card's width."""
    global im, d
    keep = im, d
    tmp = Image.new('RGB', (P(PICTO_W), P(h)), (13, 19, 22))
    im, d = tmp, ImageDraw.Draw(tmp)
    try: picto(kind, 0, 0, PICTO_W, h)
    finally: im, d = keep
    k = (w - 2) / PICTO_W
    size = (P(w - 2), round(P(h) * k))
    im.paste(tmp.resize(size, Image.Resampling.LANCZOS), (P(x + 1), P(y + (h - h * k) / 2)))


# ---------------------------------------------------------------- page
for yy in range(0, H, 4): line([(0, yy), (W, yy)], (18, 24, 27), .35)
text('SKYHAMMER', 24, 16, font(46, 700, 90), AMBER)
text('AIR SUPPORT', 26 + measure('SKYHAMMER', font(46, 700, 90)) + 14, 36, font(20, 600, 84), TEXT)
text('AEGIS CONTROL // SUPPORT LADDER', W - 24, 30, font(15, mono=True), CYAN, 'right')
line([(24, 76), (W - 24, 76)], AMBER, 1.6)

CARDS = [
    ('01', 'HELLHOUND 1-1', 'AH-64', 'apache', ['30MM', 'ROCKETS', 'FLARES'], 80),
    ('02', 'VALKYRIE 2-6', 'A-10', 'a10', ['GAU-8 30MM', 'NAPALM'], 120),
    ('03', 'BANSHEE 2-1', 'AC-130', 'ac130', ['40MM', '105MM'], 150),
    ('04', 'RAVEN 1-1', 'F-22', 'f22', ['GBU-32 x20', '10 JETS'], 200),
    ('05', 'TITAN 0-1', 'B-2', 'b2', ['BOMBS x20', 'NUKE'], 300),
]
M, GAP = 24, 16
CW = (W - 2 * M - (len(CARDS) - 1) * GAP) / len(CARDS)
TOP, BOT = 94, 564
BORDERS = [(64, 76, 79), (80, 90, 86), (104, 106, 90), (150, 136, 94), (220, 182, 94)]
for i, (num, call, name, key, tags, price) in enumerate(CARDS):
    x = M + i * (CW + GAP); inner = x + 14; avail = CW - 28
    rect((x, TOP, x + CW, BOT), PANEL, BORDERS[i], 1)
    rect((x, TOP, x + 36 + i * 24, TOP + 3), AMBER)
    text(num, inner, TOP + 14, font(15, mono=True), CYAN)
    text(call, x + CW - 14, TOP + 14, font(15, 600, 75), MUTED, 'right')
    text(name, inner, TOP + 36, font(40, 700, 82), AMBER, limit=avail)
    # blueprint
    by = TOP + 92
    rect((inner, by, x + CW - 14, by + 104), fill=(15, 22, 25))
    for gx in range(round(inner), round(x + CW - 13), 16): line([(gx, by), (gx, by + 104)], (29, 44, 49), .5)
    for gy in range(by, by + 105, 16): line([(inner, gy), (x + CW - 14, gy)], (29, 44, 49), .5)
    if key == 'a10': mesh_blueprint('a10.mesh', 'side', (inner + 8, by + 8, avail - 16, 88))
    elif key == 'ac130': mesh_blueprint('ac130.mesh', 'front', (inner + 6, by + 8, avail - 12, 88), skip_parts=(5,))
    elif key == 'f22': mesh_blueprint('f22.mesh', 'top', (inner + 8, by + 6, avail - 16, 92))
    else: blueprint(key, (inner + 6, by + 6, avail - 12, 92))
    # how it works, drawn
    py = by + 114
    rect((inner, py, x + CW - 14, py + 128), fill=(13, 19, 22), outline=(33, 46, 50))
    picto_fit(key, inner, py, avail, 128)
    # weapons
    ty = py + 140; tx = inner
    for t in tags:
        f = font(14, 600, 78); tw = measure(t, f) + 12
        rect((tx, ty, tx + tw, ty + 26), outline=LINE)
        text(t, tx + 6, ty + 6, f, TEXT)
        tx += tw + 5
    assert tx <= x + CW - 14 + 5, (name, tx)
    # price
    pf, sf = font(56, 700, 80), font(20, 600, 80)
    pw = measure(str(price), pf) + 6 + measure('PTS', sf)
    sx = x + (CW - pw) / 2
    text(str(price), sx, BOT - 74, pf, TEXT)
    text('PTS', sx + measure(str(price), pf) + 6, BOT - 44, sf, AMBER)
    # (2026-10-17: the B-2's tactical nuke has its own price)
    if key == 'b2': text('NUKE 600 PTS', x + CW / 2, BOT - 22, font(13, 600, 80), MUTED, 'center')
    rect((x + CW - 30, BOT - 2, x + CW, BOT), CYAN)
    if i < len(CARDS) - 1:
        a, b2, cy = x + CW + 3, x + CW + GAP - 3, BOT - 44
        line([(a, cy), (b2, cy)], AMBER, 1.6); line([(b2 - 5, cy - 5), (b2, cy), (b2 - 5, cy + 5)], AMBER, 1.6)

out = im.resize((W, H), Image.Resampling.LANCZOS)
out.save(ROOT / 'SUPPORT-STRIP.png', optimize=True)
half = out.resize((W // 2, H // 2), Image.Resampling.LANCZOS)
half.save(ROOT / 'SUPPORT-STRIP_636.png', optimize=True)
print('ok', out.size, half.size)
