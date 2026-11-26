"""Packs make_turntables.py's frames into the terminal viewer's sheets (Skyhammer_Viewer.lua):
media/ui/SH_Spin_<NAME>.png, the 36 frames in 4 columns x 9 rows, frame i at column i % 4, row
i // 4. Every frame is cut to the same box (all 36 frames' outline together, so the aircraft
stays still in the middle as it turns); a cell is 512 px wide unless 9 rows would pass 2048 px.
Also writes turntable/contact_<key>.png (every third frame) for looking them over.
Run with the Codex python (PIL, numpy): python -I package_turntables.py [keys...]"""
from pathlib import Path
import sys, json
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
UI = HERE.parents[1] / '42/media/ui'
NAMES = {'ac130': 'AC130', 'apache': 'Apache', 'a10': 'A10', 'b2': 'B2', 'f22': 'F22'}
COLS, ROWS, FRAMES, MAX = 4, 9, 36, 2048
PAD = 10                       # px around the outline, at the render's size


def pack(key):
    src = HERE / 'turntable' / key
    frames = [Image.open(src / ('f%02d.png' % i)).convert('RGBA') for i in range(FRAMES)]
    boxes = [f.getchannel('A').point(lambda a: 255 if a > 2 else 0).getbbox() for f in frames]
    W, H = frames[0].size
    l = max(0, min(b[0] for b in boxes) - PAD)
    t = max(0, min(b[1] for b in boxes) - PAD)
    r = min(W, max(b[2] for b in boxes) + PAD)
    b = min(H, max(b[3] for b in boxes) + PAD)
    if l == 0 or t == 0 or r == W or b == H:
        print('WARNING', key, 'touches the render edge', (l, t, r, b))
    bw, bh = r - l, b - t
    cw = min(MAX // COLS, int(MAX // ROWS * bw / bh))
    ch = round(cw * bh / bw)
    sheet = Image.new('RGBA', (cw * COLS, ch * ROWS))
    for i, f in enumerate(frames):
        cell = f.crop((l, t, r, b)).resize((cw, ch), Image.Resampling.LANCZOS)
        sheet.alpha_composite(cell, ((i % COLS) * cw, (i // COLS) * ch))
    a = np.array(sheet)
    a[a[:, :, 3] == 0, :3] = 0
    sheet = Image.fromarray(a)
    out = UI / ('SH_Spin_%s.png' % NAMES[key])
    sheet.save(out, optimize=True)
    # every third frame, for looking them over
    contact = Image.new('RGB', (cw * 4, ch * 3), (23, 28, 30))
    for n, i in enumerate(range(0, FRAMES, 3)):
        cell = sheet.crop(((i % COLS) * cw, (i // COLS) * ch, (i % COLS + 1) * cw, (i // COLS + 1) * ch))
        contact.paste(cell, ((n % 4) * cw, (n // 4) * ch), cell)
    contact.save(HERE / 'turntable' / ('contact_%s.png' % key))
    m = a[:, :, 3] > 200
    return {'sheet': out.name, 'size': sheet.size, 'cell': (cw, ch), 'bytes': out.stat().st_size,
            'mean_rgb': [round(float(c), 1) for c in a[m][:, :3].mean(0)]}


keys = sys.argv[1:] or list(NAMES)
print(json.dumps({k: pack(k) for k in keys}, indent=1))
