# The gunner seat's entry sounds (2026-10-24, the user: the entry video played silent):
#   sh_gunner_flare.wav   one flare going off the gunship: a dull pop, a crack, then its burning hiss
#   sh_gunner_static.wav  the cut to the sensor picture: a falling switch chirp into a burst of static
# 44.1 kHz, 16-bit, mono, as build.js's fixedEffect wants. Run: python make_gunner_fx.py
import math, os, random, struct, wave

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
rng = random.Random(4242)


def write(name, samples, level=0.8):
    peak = max(abs(s) for s in samples) or 1.0
    with wave.open(os.path.join(HERE, name), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(s / peak * level * 32767)) for s in samples))
    print(name, round(len(samples) / SR, 2), "s")


def lowpass(x, cut):
    a = 1 - math.exp(-2 * math.pi * cut / SR)
    y, out = 0.0, []
    for v in x:
        y += a * (v - y)
        out.append(y)
    return out


def flare():
    n = int(SR * 1.1)
    noise = [rng.uniform(-1, 1) for _ in range(n)]
    lo = lowpass(noise, 1800)
    hiss_band = [noise[i] - lowpass_v for i, lowpass_v in enumerate(lowpass(noise, 2500))]
    hiss_band = lowpass(hiss_band, 7000)
    out = []
    for i in range(n):
        t = i / SR
        thump = math.sin(2 * math.pi * (85 - 30 * min(1, t / 0.1)) * t) * math.exp(-t / 0.05) * 0.9
        crack = lo[i] * math.exp(-t / 0.012) * 0.8
        att = min(1.0, t / 0.03)
        hiss = hiss_band[i] * att * math.exp(-t / 0.33) * 0.55
        fade = min(1.0, (n - 1 - i) / (SR * 0.05))
        out.append((thump + crack + hiss) * fade)
    return out


def static():
    n = int(SR * 0.5)
    noise = [rng.uniform(-1, 1) for _ in range(n)]
    hiss = lowpass(noise, 6000)
    out, phase = [], 0.0
    for i in range(n):
        t = i / SR
        # the switch: a short falling chirp
        f = 2200 * math.exp(-t / 0.03) + 300
        phase += 2 * math.pi * f / SR
        chirp = math.sin(phase) * math.exp(-t / 0.05) * 0.5
        # the static: a burst that settles, with a mains buzz in it
        env = min(1.0, t / 0.01) * (0.35 + 0.65 * math.exp(-t / 0.12))
        buzz = (1 if math.sin(2 * math.pi * 120 * t) > 0 else -1) * 0.06
        fade = min(1.0, (n - 1 - i) / (SR * 0.08))
        out.append((chirp + (hiss[i] * 0.7 + buzz) * env) * fade)
    return out


write("sh_gunner_flare.wav", flare(), 0.85)
write("sh_gunner_static.wav", static(), 0.6)
