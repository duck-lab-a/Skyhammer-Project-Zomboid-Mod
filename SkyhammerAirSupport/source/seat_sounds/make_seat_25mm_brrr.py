# (2026-10-31, the user: "brrrr") The seat's 25mm as the recording's own unbroken stream, 35 shots a second,
# instead of one slice a round. A loop from the video's steady firing (15.5 s on) and its real wind-down
# (29.7 s on), at the video's speed; the spin was dropped (2026-10-31, the user). Skyhammer_25mmAudio starts
# the loop at full level and plays the wind-down on release.
# Run: blender --background --factory-startup --python make_seat_25mm_brrr.py
import os, wave
import aud
import numpy as np

SRC = r"C:\Users\user\Downloads\M134 Minigun - Sound Effects.mp4"
HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(os.path.dirname(HERE))
SEAT = os.path.join(MOD, "42", "media", "sound", "skyhammer_seat")
OUT = os.path.join(HERE, "m134_25mm")
SR = 44100
LOOP_FROM, LOOP_S, XFADE_S = 15.5, 3.0, 0.120
TAIL_FROM, TAIL_TO = 29.7, 31.6
TARGET_RMS = -12.0                    # a held stream, a little over the -14.7 of the rounds it replaces
FADE_MS = 80  # Skyhammer_SeatShotAudio
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


d = aud.Sound(SRC).data()
mono = d.mean(axis=1)
mono -= np.convolve(mono, np.ones(1470) / 1470, "same")        # below ~30 Hz, as the spin

# the loop's length lands where the firing's waveform best matches its start, so the seam keeps the rhythm
xf = int(XFADE_S * SR)
start = int(LOOP_FROM * SR)
head = mono[start:start + xf]
best, length = -2.0, 0
for n in range(int(LOOP_S * SR) - 2000, int(LOOP_S * SR) + 2000):
    c = np.corrcoef(head, mono[start + n:start + n + xf])[0, 1]
    if c > best:
        best, length = c, n
raw = mono[start:start + length + xf]
loop = raw[:length].copy()
t = np.linspace(0, np.pi / 2, xf)
loop[:xf] = raw[:xf] * np.sin(t) + raw[length:length + xf] * np.cos(t)

gain = 10 ** ((TARGET_RMS - db(loop)) / 20)
loop *= gain
tail = mono[int(TAIL_FROM * SR):int(TAIL_TO * SR)] * gain
tail[:int(0.04 * SR)] *= np.linspace(0, 1, int(0.04 * SR))     # under the loop's 80 ms fade
tail[-int(0.2 * SR):] *= np.linspace(1, 0, int(0.2 * SR))

assert np.abs(loop).max() < 0.98 and np.abs(tail).max() < 0.98
write(os.path.join(SEAT, "sh_seat_25mm_fire_loop.wav"), loop)
write(os.path.join(SEAT, "sh_seat_25mm_tail.wav"), tail)

# what the seat does with them: a held trigger, then a release
hold = int(PREVIEW_S * SR)
out = np.zeros(hold + len(tail))
looped = np.tile(loop, hold // len(loop) + 1)[:hold]
level = np.ones(hold)
fade = int(FADE_MS / 1000 * SR)
level[-fade:] *= np.linspace(1, 0, fade)
out[:hold] = looped * level
out[hold - fade:hold - fade + len(tail)] += tail
assert np.abs(out).max() < 0.98, "the mix would clip: %.3f" % np.abs(out).max()
write(os.path.join(OUT, "preview_25mm_brrr_5s.wav"), out)

twice = np.concatenate([loop, loop])
w = int(0.1 * SR)
rms = 20 * np.log10(np.sqrt(np.convolve(twice ** 2, np.ones(w) / w, "valid")) + 1e-12)
env = np.abs(twice - np.convolve(twice, np.ones(44) / 44, "same"))
env = np.convolve(env, np.ones(44) / 44, "same")[::10]
spec = np.abs(np.fft.rfft((env - env.mean()) * np.hanning(len(env))))
fr = np.fft.rfftfreq(len(env), 10 / SR)
band = (fr > 15) & (fr < 130)
print("loop %.3f s, seam match %.3f, gain %.3f, peak %.3f, rms %.1f dB" % (length / SR, best, gain, np.abs(loop).max(), db(loop)))
print("100 ms level across the seam: min %.1f max %.1f dB" % (rms.min(), rms.max()))
print("shots a second %.1f" % fr[band][np.argmax(spec[band])])
print("tail %.2f s, peak %.3f; preview peak %.3f" % (len(tail) / SR, np.abs(tail).max(), np.abs(out).max()))
