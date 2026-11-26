# (2026-10-31, the user: "the spin sound mixed in at the start") The barrels' spin before the video's
# firing (25.00-25.65 s, no shot rhythm yet), at the takes' 0.85 speed, so 760 ms. Skyhammer_25mmAudio
# plays it once a burst under the first rounds, which rise from 0.4 of their level to full over its length.
# Reads the takes make_seat_25mm_m134.py wrote; the preview is that opening and 5 s of stream.
# Run: blender --background --factory-startup --python make_seat_25mm_spin.py
import os, wave
import aud
import numpy as np

SRC = r"C:\Users\user\Downloads\M134 Minigun - Sound Effects.mp4"
HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(os.path.dirname(HERE))
SEAT = os.path.join(MOD, "42", "media", "sound", "skyhammer_seat")
OUT = os.path.join(HERE, "m134_25mm")
SR = 44100
SPEED = 0.85
SPIN_FROM, SPIN_TO = 25.002, 25.65
SPIN_RMS = -15.0                      # its loudest 50 ms; louder clips where it meets the rising rounds
ROUND_MS, CUE_GAIN = 70, 0.7          # Skyhammer_Ops SEATGUN25, Skyhammer_SeatShotAudio gun25
SPIN_MS, FIRST_ROUND = 760, 0.4       # Skyhammer_25mmAudio
PREVIEW_S = 5.0


def read(path):
    with wave.open(path) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768


def write(path, x):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def db(x):
    return 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-12)


def burst(takes, spin, seconds, fps, seed, rounds=True, with_spin=True):
    rng = np.random.default_rng(seed)
    out = np.zeros(int(seconds * SR) + len(takes[0]) + len(spin))
    if with_spin:
        out[:len(spin)] += spin
    frame, ready, t = 1000.0 / fps, 0.0, 0.0
    while rounds and t < seconds * 1000:
        if t >= ready:
            ready = ready + ROUND_MS if t - ready < ROUND_MS else t + ROUND_MS
            k = rng.integers(len(takes))
            at = int(t / 1000 * SR)
            rise = FIRST_ROUND + (1 - FIRST_ROUND) * min(1.0, t / SPIN_MS)
            out[at:at + len(takes[k])] += takes[k] * CUE_GAIN * rise
        t += frame
    return out[:int(seconds * SR) + len(takes[0])]


d = aud.Sound(SRC).data()
mono = d.mean(axis=1)
n = int(len(mono) / SPEED)
slow = np.interp(np.arange(n) * SPEED, np.arange(len(mono)), mono)
slow -= np.convolve(slow, np.ones(1470) / 1470, "same")        # below ~30 Hz, as the takes

spin = slow[int(SPIN_FROM / SPEED * SR):int(SPIN_TO / SPEED * SR)].copy()
spin[:44] *= np.linspace(0, 1, 44)                              # 1 ms, no click
fade = int(0.150 * SR)
spin[-fade:] *= np.linspace(1, 0, fade) ** 2                    # gone as the rounds reach full level
k = int(0.05 * SR)
loudest = np.sqrt(np.convolve(spin ** 2, np.ones(k) / k, "valid")).max()
gain = 10 ** (SPIN_RMS / 20) / loudest
spin *= gain
assert np.abs(spin).max() < 0.98, "the spin would clip"
write(os.path.join(SEAT, "sh_seat_25mm_spin.wav"), spin)

takes = [read(os.path.join(SEAT, "sh_seat_25mm_fire%s.wav" % ("" if i == 1 else "_%d" % i))) for i in range(1, 9)]
print("spin %.0f ms, gain %.3f, peak %.3f" % (len(spin) / SR * 1000, gain, np.abs(spin).max()))
for fps in (18, 25, 45):
    # the takes are picked at random, so the worst of many openings, not one
    peak = max(np.abs(burst(takes, spin, 1.2, fps, seed)).max() for seed in range(200))
    s = burst(takes, spin, PREVIEW_S, fps, 3)
    print("%2d fps: worst opening peak %.3f, rms after the spin %.1f dB" % (fps, peak, db(s[int(1.0 * SR):int(PREVIEW_S * SR)])))
    assert peak < 0.98, "the opening would clip"
a = burst(takes, spin, 1.2, 25, 3, with_spin=False)
b = burst(takes, spin, 1.2, 25, 3, rounds=False)
print("t ms: rounds alone / spin alone, dB")
for t in range(0, 1000, 100):
    i, j = int(t / 1000 * SR), int((t + 100) / 1000 * SR)
    print("%4d: %6.1f / %6.1f" % (t, db(a[i:j]), db(b[i:j])))

prev = burst(takes, spin, PREVIEW_S, 25, 7)
write(os.path.join(OUT, "preview_25mm_spin_5s.wav"), prev)
print("preview peak %.3f" % np.abs(prev).max())
