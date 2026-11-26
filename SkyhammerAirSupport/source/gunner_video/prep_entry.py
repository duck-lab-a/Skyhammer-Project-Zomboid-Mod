# The gunner seat's entry video, 2026-10-24 evening (the user's own clip, generated with Google
# Gemini, 1920x1080 24 fps, 108 frames, 4.5 s, with sound). prep_entry.py <frames_dir> <out_dir>:
# every frame cropped to 1690x951 from the top left, which leaves out the generator's sparkle mark
# in the bottom right corner (x 1700-1780, y 855-940), and scaled to 1280x720, the size the seat
# opens the video at (Skyhammer_Gunner VIDEO.w x VIDEO.h); f001..f108.png. Also the five fallback
# stills (media/textures/SH_Gunner/entry_1..5.png, 960x540).
import os, sys
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
CROP = (0, 0, 1690, 951)
names = sorted(f for f in os.listdir(src) if f.endswith(".png"))
for i, f in enumerate(names, 1):
    im = Image.open(os.path.join(src, f)).convert("RGB").crop(CROP).resize((1280, 720), Image.LANCZOS)
    im.save(os.path.join(out, "f%03d.png" % i))
stills = os.path.join(out, "stills")
os.makedirs(stills, exist_ok=True)
for k, i in enumerate((12, 30, 50, 70, 88), 1):
    Image.open(os.path.join(out, "f%03d.png" % i)).resize((960, 540), Image.LANCZOS).save(os.path.join(stills, "entry_%d.png" % k))
print("frames", len(names))
