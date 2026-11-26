# The AC-130 gunner seat's and gunship's sound slots (2026-10-24, the user): one WAV a slot in
# 42/media/sound/skyhammer_seat, named as Skyhammer_SeatSounds.txt plays them. Until the finished
# sounds come, each slot is filled from Skyhammer's own sounds here. A file already there is
# never overwritten (the finished ones replace these by name), unless --force.
# The folder is not build.js's: its sound/skyhammer folder moves aside any file it did not make.
# Run: <codex python> -I source/make_seat_placeholders.py [--force]
import os, sys, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SND = os.path.join(HERE, "..", "42", "media", "sound")
OWN, OUT = os.path.join(SND, "skyhammer"), os.path.join(SND, "skyhammer_seat")
SR = 44100
FORCE = "--force" in sys.argv


def read(name):
    with wave.open(os.path.join(OWN, name), "rb") as w:
        assert w.getframerate() == SR and w.getsampwidth() == 2 and w.getnchannels() == 1, name
        return np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(float) / 32768


def fades(x, a_ms=5, b_ms=5):
    x = x.copy()
    a, b = min(len(x), int(a_ms * SR / 1000)), min(len(x), int(b_ms * SR / 1000))
    if a: x[:a] *= np.linspace(0, 1, a)
    if b: x[-b:] *= np.linspace(1, 0, b)
    return x


def respeed(x, k): return np.interp(np.arange(0, len(x) - 1, k), np.arange(len(x)), x)


def peak(x, p=0.85):
    m = np.max(np.abs(x))
    return x * (p / m) if m > 0 else x


def write(name, x):
    path = os.path.join(OUT, name)
    if os.path.exists(path) and not FORCE:
        print("kept", name); return
    x = np.clip(x, -0.999, 0.999)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())
    print("wrote", name, "%.2f s" % (len(x) / SR))


os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(130)
# 1 the 25mm, a round: a slice of the rotary take (its sustained part)
with wave.open(os.path.join(OUT, "sh_25mm_rotary_local.wav"), "rb") as w:
    rot = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(float) / 32768
write("sh_seat_25mm_fire.wav", fades(peak(rot[int(0.30 * SR):int(0.42 * SR)], 0.8), 3, 30))
# 2, 3 the 40mm and the 105 reports
write("sh_seat_40mm_fire.wav", fades(read("sh_40mm_report_1.wav")[:int(1.2 * SR)], 2, 300))
write("sh_seat_105mm_fire.wav", fades(read("sh_105_report_1.wav"), 2, 200))
# 4-6 impacts: the 30mm's for the 25mm, the 40mm's, the 105's (two more by a little pitch)
for i in range(3):
    write(f"sh_seat_25mm_impact_{i + 1}.wav", read(f"sh_30mm_impact_{i + 1}.wav"))
    write(f"sh_seat_40mm_impact_{i + 1}.wav", read(f"sh_40mm_impact_{i + 1}.wav"))
    write(f"sh_seat_105mm_impact_{i + 1}.wav", read(f"sh_105_impact_{i + 1}.wav"))
write("sh_seat_105mm_impact_4.wav", fades(respeed(read("sh_105_impact_1.wav"), 0.92), 2, 50))
write("sh_seat_105mm_impact_5.wav", fades(respeed(read("sh_105_impact_2.wav"), 1.08), 2, 50))
# 7, 8 reloads: the synthesized 105 reload, a little quicker for the 40mm
rel = read("sh_reload_105.wav")
write("sh_seat_40mm_reload.wav", fades(respeed(rel, 1.15), 2, 40))
write("sh_seat_105mm_reload.wav", rel)
# 9 a kill confirmed: a short soft tick
t = np.arange(int(0.06 * SR)) / SR
write("sh_seat_hitmarker.wav", fades(0.45 * np.sin(2 * np.pi * 1850 * t) * np.exp(-t * 70), 1, 10))
# 10 the entry: the entry video's own sound (2026-10-24 evening, the user's clip; mono, 4.5 s:
# source/gunner_video/sh_seat_entry_master.wav), as it is
with wave.open(os.path.join(HERE, "gunner_video", "sh_seat_entry_master.wav"), "rb") as w:
    write("sh_seat_entry.wav", np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(float) / 32768)
eng = read("sh_engine_loop.wav")
# 11, 12 the gunship's engines: the orbit loop as it is, and the same going away
write("sh_ac130_engine_loop.wav", eng)
k = int(6.0 * SR)
dep = np.resize(eng, k) * np.linspace(1, 0, k) ** 2
write("sh_ac130_engine_depart.wav", fades(dep, 5, 20))
# (the 25mm rotary takes, sh_25mm_rotary_local / _loop_local, made 2026-10-24 from Skyhammer's own
# sounds, live in this folder too: moved here as they were)
