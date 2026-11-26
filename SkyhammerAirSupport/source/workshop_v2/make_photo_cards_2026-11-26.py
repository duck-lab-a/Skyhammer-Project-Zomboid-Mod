r"""Description cards from the 2026-11-26 recordings (UI-free stills): same frame and lettering as
make_photo_cards.py, with the F-22 (04) added, the B-2 now 05, and the terminal with its F-22 tab.

Usage: <python with Pillow + numpy> make_photo_cards_2026-11-26.py
Reads and writes Downloads\Skyhammer_스크린샷\2026-11-26 (cards go to \설명문용).
"""
import importlib.util, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SHOTS = Path.home() / 'Downloads' / 'Skyhammer_스크린샷' / '2026-11-26'
OUT = SHOTS / '설명문용'
# the lettering of make_photo_cards.py, without running its loop
src = (HERE / 'make_photo_cards.py').read_text(encoding='utf-8').split("OUT.mkdir(exist_ok=True)")[0]
ns = {'__name__': 'cards', '__file__': str(HERE / 'make_photo_cards.py')}
exec(compile(src, 'make_photo_cards.py', 'exec'), ns)
W, H = ns['W'], ns['H']
smooth = ns['smooth']
yy, xx = ns['yy'], ns['xx']
# a light shade right behind the lettering only (2026-10-17, the user: the dark hid the B-2's shadow)
SHADE = 0.62 * smooth((0.46 - xx) / 0.22) * smooth((yy - 0.62) / 0.18)

def card(photo, spec, fade):
    ns['FADE'] = fade
    return ns['card'](photo, *spec)

def seam(left, right, top_x=700, bottom_x=600):
    """two stills side by side, split by a slanted amber line"""
    a = Image.open(left).convert('RGB').resize((W, H), Image.Resampling.LANCZOS) if not isinstance(left, Image.Image) else left
    b = right
    m = Image.new('L', (W * 2, H * 2), 0)
    ImageDraw.Draw(m).polygon([(top_x * 2, 0), (W * 2, 0), (W * 2, H * 2), (bottom_x * 2, H * 2)], fill=255)
    out = a.copy(); out.paste(b, (0, 0), m.resize((W, H), Image.Resampling.LANCZOS))
    l = Image.new('RGBA', (W * 3, H * 3)); ImageDraw.Draw(l).line([(top_x * 3, 0), (bottom_x * 3, H * 3)], fill='#DCB65E', width=7)
    l = l.resize((W, H), Image.Resampling.LANCZOS); out.paste(l, (0, 0), l)
    return out

def shift(path, zoom, ox, oy):
    im = Image.open(path).convert('RGB'); z = W / im.width * zoom
    im = im.resize((round(im.width * z), round(im.height * z)), Image.Resampling.LANCZOS)
    c = Image.new('RGB', (W, H)); c.paste(im, (-round(ox), -round(oy))); return c

SPEC = {
    'apache':   ('01', 'AH-64', 'APACHE', 'HELLHOUND 1-1', ['30MM', 'ROCKETS', 'FLARES']),
    'a10':      ('02', 'A-10', 'THUNDERBOLT', 'VALKYRIE 2-6', ['GAU-8 30MM', 'NAPALM']),
    'ac130':    ('03', 'AC-130', 'GUNSHIP', 'BANSHEE 2-1', ['40MM', '105MM']),
    'f22':      ('04', 'F-22', 'RAPTOR', 'RAVEN 1-1', ['GBU-32 x20', '10 JETS']),
    'b2':       ('05', 'B-2', 'SPIRIT', 'TITAN 0-1', ['BOMBS x20', 'TACTICAL NUKE']),
    'terminal': ('//', 'TERMINAL', '', 'AEGIS CONTROL', ['SENSOR MAP', 'MARK', 'CALL'], 56),
}
tmp = SHOTS / '_tmp.png'
jobs = [
    ('main_01_apache', 'apache', 'VP_1_apache.jpg'), ('main_02_a10', 'a10', 'VP_2_a10.jpg'),
    ('main_03_ac130', 'ac130', 'VP_3_ac130.jpg'), ('main_04_f22', 'f22', 'VP_6_f22_formation.jpg'),
    ('main_05_b2_nuke', 'b2', None),
    ('vanilla_01_apache', 'apache', 'VA_1_apache.jpg'), ('vanilla_02_a10', 'a10', 'VA_2_a10.jpg'),
    ('vanilla_03_ac130', 'ac130', 'VA_3_ac130.jpg'), ('vanilla_04_f22', 'f22', 'VA_6_f22_formation.jpg'),
    ('vanilla_05_b2', 'b2', 'VA_4_b2.jpg'),
    ('main_06_terminal_ko', 'terminal', 'T_main.png'), ('vanilla_06_terminal_ko', 'terminal', 'T_vanilla.png'),
]
OUT.mkdir(exist_ok=True)
for name, key, f in jobs:
    if f is None:
        im = seam(shift(SHOTS / "VP_4_b2.jpg", 1.006, 219, 0), shift(SHOTS / "VP_5_nuke.jpg", 1.04, -115, 0), 735, 620)
        im.save(tmp); p = tmp
    else: p = SHOTS / f
    if not p.exists(): print('skip', f); continue
    dst = OUT / f'{name}.jpg'
    c = card(p, SPEC[key], SHADE)
    c.save(dst, quality=90, optimize=True, progressive=True)
    print(dst.name, c.size, dst.stat().st_size // 1024, 'KB')
tmp.unlink(missing_ok=True)
