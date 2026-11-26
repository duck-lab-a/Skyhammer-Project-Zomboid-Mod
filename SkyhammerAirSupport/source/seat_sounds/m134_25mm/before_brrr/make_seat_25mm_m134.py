# (2026-10-31, the user: the seat's 25mm from Downloads\M134 Minigun - Sound Effects.mp4)
# Eight takes of the video's full-bodied firing (14.5-20 s, 26-29.5 s), slowed to 0.85 so 36 shots a
# second become 30, the GAU-12's rate. Each take is a 240 ms slice starting on a shot: flat for 80 ms,
# then a decay, because the seat plays one take per round (70 ms apart) and the overlap is the stream.
# Run: blender --background --factory-startup --python make_seat_25mm_m134.py
import os, shutil, wave
import aud
import numpy as np

SRC = r"C:\Users\user\Downloads\M134 Minigun - Sound Effects.mp4"
HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(os.path.dirname(HERE))
SEAT = os.path.join(MOD, "42", "media", "sound", "skyhammer_seat")
OUT = os.path.join(HERE, "m134_25mm")
SR = 44100
SPEED = 0.85
TAKES = 8
BODY, LEN = 0.080, 0.240
ROUND_MS, CUE_GAIN = 70, 0.7          # Skyhammer_Ops SEATGUN25, Skyhammer_SeatShotAudio gun25
TARGET_RMS = -14.7                    # the 14/s stream level of the take this replaces
PREVIEW_S, FPS = 5.0, 25              # the seat fires on frames, so the preview does too


def write(path, x):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def db(x):
    return 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-12)


def stream(takes, seconds, fps, seed):
    rng = np.random.default_rng(seed)
    out = np.zeros(int(seconds * SR) + len(takes[0]))
    frame, ready, last = 1000.0 / fps, 0.0, -1
    t = 0.0
    while t < seconds * 1000:
        if t >= ready:
            # as Skyhammer_Ops: a round late within one reload keeps the rhythm
            ready = ready + ROUND_MS if t - ready < ROUND_MS else t + ROUND_MS
            k = rng.integers(len(takes))
            at = int(t / 1000 * SR)
            out[at:at + len(takes[k])] += takes[k] * CUE_GAIN
        t += frame
    return out[:int(seconds * SR) + int(LEN * SR)]


d = aud.Sound(SRC).data()
mono = d.mean(axis=1)
n = int(len(mono) / SPEED)
slow = np.interp(np.arange(n) * SPEED, np.arange(len(mono)), mono)
slow -= np.convolve(slow, np.ones(1470) / 1470, "same")        # below ~30 Hz: nothing to hear, only headroom

ranges = [(14.5, 20.0), (26.0, 29.5)]
starts = []
for a, z in ranges:
    for t in np.linspace(a + 0.1, z - 0.5, TAKES // 2):
        i = int(t / SPEED * SR)
        win = int(0.045 * SR)
        e = np.convolve(np.abs(np.diff(slow[i:i + win])), np.ones(44) / 44, "same")
        starts.append(i + int(np.argmax(e)))

count = int(LEN * SR)
body = int(BODY * SR)
env = np.ones(count)
env[body:] = np.exp(-np.arange(count - body) / (count - body) * 6.9)      # -60 dB at the end
env[:44] = np.linspace(0, 1, 44)                                          # 1 ms, no click
env[-220:] *= np.linspace(1, 0, 220)
takes = [slow[s:s + count] * env for s in starts]

probe = stream(takes, PREVIEW_S, FPS, 1)
gain = 10 ** ((TARGET_RMS - db(probe[:int(PREVIEW_S * SR)])) / 20)
takes = [t * gain for t in takes]
assert max(np.abs(t).max() for t in takes) < 0.98, "a take would clip"

os.makedirs(OUT, exist_ok=True)
old = os.path.join(OUT, "sh_seat_25mm_fire_before_m134.wav")
if not os.path.exists(old):
    shutil.copy2(os.path.join(SEAT, "sh_seat_25mm_fire.wav"), old)
for i, t in enumerate(takes):
    write(os.path.join(SEAT, "sh_seat_25mm_fire%s.wav" % ("" if i == 0 else "_%d" % (i + 1))), t)

prev = stream(takes, PREVIEW_S, FPS, 7)
write(os.path.join(OUT, "preview_25mm_5s.wav"), prev / max(1.0, np.abs(prev).max() / 0.98))
for fps in (18, 25, 45):
    s = stream(takes, PREVIEW_S, fps, 3)[:int(PREVIEW_S * SR)]
    k = int(0.02 * SR)
    env20 = np.sqrt(np.convolve(s ** 2, np.ones(k) / k, "valid"))[int(0.1 * SR):]
    print("%2d fps: rms %.1f dB, peak %.3f, quietest 20 ms %.1f dB" % (fps, db(s), np.abs(s).max(), 20 * np.log10(env20.min() + 1e-9)))
print("takes", len(takes), "start s", [round(s / SR * SPEED, 2) for s in starts], "gain %.3f" % gain,
      "take peak %.3f" % max(np.abs(t).max() for t in takes))
print("tail after release: last round + %.0f ms" % (LEN * 1000))
