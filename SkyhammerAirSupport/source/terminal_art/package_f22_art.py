"""Crops make_f22_art.py's render into the terminal picture (media/ui/SH_Art_F22.png, 512 px wide, as
the A-10's: package_a10_art.py) and makes the tab icon (SH_Icon_F22.png): the B-2 icon's bracket frame
with the F-22's top-down silhouette from the game mesh. Also writes F22_terminal_compare.png."""
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np, struct, json

HERE = Path(__file__).resolve().parent
MOD = HERE.parents[1]
UI = MOD / '42/media/ui'

im = Image.open(HERE / 'SH_Art_F22_native.png').convert('RGBA')
im = im.crop(im.getchannel('A').getbbox())
high = Image.new('RGBA', (im.width + 32, im.height + 16))
high.alpha_composite(im, (16, 8))
high.resize((2048, round(high.height * 2048 / high.width)), Image.Resampling.LANCZOS).save(HERE / 'SH_Art_F22_2048.png')
h = round(high.height * 512 / high.width)
out = high.resize((512, h), Image.Resampling.LANCZOS)
a = np.array(out)
a[a[:, :, 3] == 0, :3] = 0
out = Image.fromarray(a)
out.save(UI / 'SH_Art_F22.png')

# the icon: the existing pack's frame and corner pixels kept, its symbol replaced (as the A-10's)
base = np.array(Image.open(UI / 'SH_Icon_B2.png').convert('RGBA'))
bg = base[32, 3].copy()
base[8:56, 6:58] = bg
icon = Image.fromarray(base).resize((256, 256), Image.Resampling.NEAREST)
sil = Image.new('L', (256, 256))
d = ImageDraw.Draw(sil)
b = (MOD / 'source/java/skyhammer/aircraft/f22.mesh').read_bytes()
n = struct.unpack_from('>I', b, 4)[0]
v = np.frombuffer(b, '>f4', n * 10, 8).reshape(-1, 10)
# game space: +X right wing, +Z nose; nose up in the icon, the 19.2 m length in about 180 of 256 px
k = 180 / (v[:, 2].max() - v[:, 2].min())
cz = (v[:, 2].max() + v[:, 2].min()) / 2
for i in range(0, n, 3):
    d.polygon([(128 + float(x) * k, 128 - (float(z) - cz) * k) for x, y, z in v[i:i + 3, :3]], fill=255)
symbol = Image.new('RGBA', (256, 256), (237, 234, 218, 255))
icon.paste(symbol, (0, 0), sil)
icon = icon.resize((64, 64), Image.Resampling.LANCZOS)
icon.save(UI / 'SH_Icon_F22.png')

canvas = Image.new('RGB', (680, 960), (23, 29, 32))
y = 20
for name in ['AC130', 'B2', 'A10', 'F22']:
    art = Image.open(UI / f'SH_Art_{name}.png').convert('RGBA')
    canvas.paste(art, (12, y), art)
    ic = Image.open(UI / f'SH_Icon_{name}.png').convert('RGBA')
    canvas.paste(ic, (574, y + 30), ic)
    y += max(art.height + 24, 195)
canvas.crop((0, 0, 680, y + 8)).save(HERE / 'F22_terminal_compare.png')


def mean(path):
    x = np.array(Image.open(path).convert('RGBA')).astype(float)
    m = x[:, :, 3] > 200
    return [round(c, 1) for c in x[m][:, :3].mean(0)]


print(json.dumps({'art_size': out.size, 'icon_size': icon.size,
                  'mean_rgb': {k: mean(UI / f'SH_Art_{k}.png') for k in ['AC130', 'B2', 'A10', 'Apache', 'F22']}}))
