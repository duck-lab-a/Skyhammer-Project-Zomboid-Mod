# The gunner seat's warning (2026-10-24): two short cockpit tones, played to the player alone
# when the body left on the ground is hit (Skyhammer_Gunner). 44.1 kHz, 16-bit, mono, as
# build.js's fixedEffect wants. Run: python make_gunner_alert.py  (writes sh_gunner_alert.wav here)
import math, os, struct, wave

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sh_gunner_alert.wav")


def tone(freq, ms, amp):
    n = int(SR * ms / 1000)
    fade = int(SR * 0.006)
    out = []
    for i in range(n):
        env = min(1.0, i / fade, (n - 1 - i) / fade)
        # a square-ish tone (fundamental + odd harmonics), like a panel buzzer, softened
        t = i / SR
        s = (math.sin(2 * math.pi * freq * t) + math.sin(2 * math.pi * freq * 3 * t) / 5
             + math.sin(2 * math.pi * freq * 5 * t) / 12)
        out.append(s * env * amp)
    return out


def silence(ms):
    return [0.0] * int(SR * ms / 1000)


samples = tone(1250, 90, 0.5) + silence(60) + tone(1250, 90, 0.5) + silence(40)
peak = max(abs(s) for s in samples)
with wave.open(OUT, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(b"".join(struct.pack("<h", int(s / peak * 0.7 * 32767)) for s in samples))
print(OUT, len(samples) / SR, "s")
