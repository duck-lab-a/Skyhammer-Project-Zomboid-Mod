# The AC-130 gunner seat's and the gunship's 12 sounds (24 WAVs, 2026-10-24, the user's spec).
# Made only from Skyhammer's own sounds (42/media/sound/skyhammer + the two 25mm rotary takes in
# skyhammer_seat) and from synthesis here; the reloads reuse the synth of synth_reload/make_reload_105.py
# (its functions, run from its own text; that file is not changed). No other game's or mod's audio.
# Writes into 42/media/sound/skyhammer_seat (the slots Skyhammer_SeatSounds.txt plays; replaces
# make_seat_placeholders.py's stand-ins by name), a report and previews into OUT_PREVIEW.
# Run: <blender python> -I source/seat_sounds/make_seat_sounds.py
import hashlib, json, os, sys, wave
import numpy as np

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.normpath(os.path.join(HERE, "..", ".."))
OWN = os.path.join(MOD, "42", "media", "sound", "skyhammer")
SEAT = os.path.join(MOD, "42", "media", "sound", "skyhammer_seat")
RELOAD_SYNTH = os.path.join(MOD, "source", "synth_reload", "make_reload_105.py")
OUT_PREVIEW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.expanduser("~"), "Documents", "Codex", "2026-10-08", "project-zomboid-b42-1-3-x20", "outputs",
    "AC130_seat_sounds_20261024")
CEIL_DB = -1.2          # a little under the -1 dBFS limit, so the 16-bit rounding stays under it
rng = np.random.default_rng(130)
os.makedirs(SEAT, exist_ok=True); os.makedirs(OUT_PREVIEW, exist_ok=True)


# ---- helpers ---------------------------------------------------------------------------------------
def db(v): return 10 ** (v / 20)


def todb(v): return 20 * np.log10(max(float(v), 1e-12))


def tt(n): return np.arange(n) / SR


def load(path):
    with wave.open(path, "rb") as w:
        assert w.getframerate() == SR and w.getsampwidth() == 2 and w.getnchannels() == 1, path
        return np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(float) / 32768


def own(name): return load(os.path.join(OWN, name))


def norm(x): return x / (np.abs(x).max() + 1e-12)


def filt(x, lo=None, hi=None, order=2, circular=False):
    """Zero-phase band shaping in the frequency domain; padded unless the signal is a loop."""
    pad = 0 if circular else int(0.5 * SR)
    y = np.concatenate([x, np.zeros(pad)])
    X = np.fft.rfft(y); f = np.fft.rfftfreq(len(y), 1 / SR); g = np.ones_like(f)
    if lo: g /= np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** (2 * order))
    if hi: g /= np.sqrt(1 + (f / hi) ** (2 * order))
    return np.fft.irfft(X * g, len(y))[:len(x)]


def respeed(x, k):
    """Play k times as fast (pitch and length together, like a tape)."""
    return np.interp(np.arange(0, len(x) - 1, k), np.arange(len(x)), x)


def varispeed(x, rate):
    """rate[n] = playback speed at output sample n."""
    pos = np.concatenate([[0], np.cumsum(rate[:-1])])
    pos = pos[pos < len(x) - 1]
    return np.interp(pos, np.arange(len(x)), x)


def tv_lowpass(x, fc_at, order=2, nfft=2048, hop=512):
    """Lowpass whose cutoff moves with time (fc_at(t) in Hz), by STFT overlap-add."""
    win = np.hanning(nfft); pad = np.concatenate([np.zeros(nfft), x, np.zeros(nfft)])
    out = np.zeros(len(pad)); wsum = np.zeros(len(pad)); f = np.fft.rfftfreq(nfft, 1 / SR)
    for s in range(0, len(pad) - nfft, hop):
        t = (s + nfft / 2 - nfft) / SR
        g = 1 / np.sqrt(1 + (f / max(fc_at(t), 20)) ** (2 * order))
        out[s:s + nfft] += np.fft.irfft(np.fft.rfft(pad[s:s + nfft] * win) * g, nfft) * win
        wsum[s:s + nfft] += win ** 2
    return (out / np.maximum(wsum, 1e-6))[nfft:nfft + len(x)]


def onset(x, rel_db=-30):
    """First sample above rel_db of the peak."""
    return int(np.argmax(np.abs(x) > np.abs(x).max() * db(rel_db)))


def fades(x, a_ms=5, b_ms=5):
    x = x.copy(); a, b = int(a_ms * SR / 1000), int(b_ms * SR / 1000)
    if a: x[:a] *= np.linspace(0, 1, a)
    if b: x[-b:] *= np.linspace(1, 0, b)
    return x


def fade_out_tail(x, sec):
    """A long cos^2 fade over the last sec seconds: the tail ends in silence, not in a cut."""
    x = x.copy(); n = int(sec * SR)
    x[-n:] *= np.cos(np.linspace(0, np.pi / 2, n)) ** 2
    return x


def fit(x, sec):
    n = int(sec * SR)
    return x[:n] if len(x) >= n else np.concatenate([x, np.zeros(n - len(x))])


def active_rms_db(x, block=1024, floor=-45):
    """Skyhammer's loudness measure (synth_reload): RMS of the 1024-sample blocks above -45 dBFS."""
    r = np.array([np.sqrt(np.mean(x[i:i + block] ** 2)) for i in range(0, len(x) - block + 1, block)])
    r = r[r > db(floor)]
    return todb(np.sqrt(np.mean(r ** 2))) if len(r) else -120.0


def limit(x, ceil_db=CEIL_DB, look_ms=1.5, release_ms=80):
    """Look-ahead peak limiter: the gain is down before a peak comes, and comes back slowly."""
    ceil = db(ceil_db); k = max(1, int(look_ms / 1000 * SR))
    need = np.minimum(1.0, ceil / np.maximum(np.abs(x), 1e-12))
    padded = np.concatenate([np.ones(k), need, np.ones(k)])
    g = np.min(np.lib.stride_tricks.sliding_window_view(padded, 2 * k + 1), axis=1)
    g = np.convolve(np.concatenate([np.ones(k // 2), g, np.ones(k // 2)]), np.ones(k + 1) / (k + 1), "valid")[:len(x)]
    a = np.exp(-1 / (release_ms / 1000 * SR)); h = np.empty_like(g); cur = 1.0
    for i, v in enumerate(g):
        cur = v if v < cur else a * cur + (1 - a) * v
        h[i] = cur
    return x * h


def level(x, target_db, limiter=True):
    """Gain to the target active RMS; peaks over the ceiling go through the limiter; a few rounds."""
    y = x.copy()
    for _ in range(6):
        y = y * db(target_db - active_rms_db(y))
        if np.abs(y).max() > db(CEIL_DB):
            if not limiter: y = y * db(CEIL_DB) / np.abs(y).max(); break
            y = limit(y)
        if abs(active_rms_db(y) - target_db) < 0.2: break
    return y


def clean(x, lo=20):
    """No DC, no sub-sonic: a 20 Hz high-pass, the mean taken out."""
    y = filt(x, lo, None, 2)
    return y - y.mean()


# ---- synth parts -----------------------------------------------------------------------------------
def thump(f0, f1, tau, dur, pitch_tau=0.01, attack=0.0008):
    n = int(dur * SR); t = tt(n)
    f = f1 + (f0 - f1) * np.exp(-t / pitch_tau)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * (1 - np.exp(-t / attack)) * np.exp(-t / tau)


def burst(dur, lo, hi, tau, attack=0.0002, hold=0.0):
    n = int(dur * SR); t = tt(n)
    return filt(rng.standard_normal(n), lo, hi, 2) * (1 - np.exp(-t / attack)) * np.exp(-np.maximum(0, t - hold) / tau)


def rumble(dur, tau, lo=25, hi=170, attack=0.04):
    """The ground's low roll after a hit: low noise swelling in, then dying away."""
    n = int(dur * SR); t = tt(n)
    nz = filt(np.cumsum(rng.standard_normal(n)) * 0.02, lo, hi, 3)
    return norm(nz * (1 - np.exp(-t / attack)) * np.exp(-t / tau))


def debris(dur, t0, rate, tau, lo=900, hi=6500):
    """Dirt and bits falling back: short noise grains, thinning out."""
    n = int(dur * SR); out = np.zeros(n); t = t0
    while t < dur - 0.02:
        t += rng.exponential(1 / (rate * np.exp(-(t - t0) / tau) + 1e-3))
        if t >= dur - 0.02: break
        gl = rng.uniform(0.003, 0.012); m = int(gl * SR); c = rng.uniform(lo, hi)
        g = filt(rng.standard_normal(m), c * 0.6, c * 1.6, 2) * np.exp(-tt(m) / (gl * 0.35))
        k = int(t * SR); out[k:k + m] += g[:n - k] * rng.uniform(0.3, 1.0) * np.exp(-(t - t0) / (tau * 1.5))
    return norm(out)


def place(dst, src, t0, gain=1.0):
    k = int(t0 * SR); m = min(len(src), len(dst) - k)
    if m > 0: dst[k:k + m] += src[:m] * gain


# ---- the reload synth (make_reload_105.py's own functions, run from its text) ------------------------
def reload_namespace(seed):
    text = open(RELOAD_SYNTH, encoding="utf-8").read()
    head = text.split("N = int((DUR + 1.0) * SR)")[0]
    tools = text[text.index("def active_rms"):text.index("# Loudness:")]
    ns = {"__file__": RELOAD_SYNTH, "__name__": "reload_synth"}
    argv = sys.argv; sys.argv = ["make_reload_105.py", str(seed)]
    try: exec(head + "\n" + tools, ns)
    finally: sys.argv = argv
    return ns


def reload_master(ns, mix, dur):
    """make_reload_105.py's own master: cargo-bay room, dark top, compressor, clipper drive."""
    y = ns["room"](mix)[:int(dur * SR)]
    y = ns["shape"](y, 30, ns["TOP_HZ"], 2)
    y = ns["norm"](ns["compress"](ns["norm"](y), -14))
    for drive in np.arange(0, 20.5, 0.5):
        z = ns["shape"](ns["clip"](y * db(drive)), None, 11000, 2); z = z / np.abs(z).max() * db(-0.3)
        if ns["active_rms"](z) >= -10.5: break
    return z


def reload_105_seat():
    """The approved full 105 take's own hits, re-timed to 1.85 s: breech opens + case out (0-0.70 s as in
    sh_reload_105), the round rammed home (from 1.846 s), the breech slammed shut (from 3.418 s)."""
    text = open(RELOAD_SYNTH, encoding="utf-8").read()
    text = text.replace('"shortest": (1.70,',
                        '"seat": (1.85, [(0.0, 0.70, 0.0), (1.846, 2.20, 0.75 - 1.846), (3.418, 9.9, 1.15 - 3.418)]),\n'
                        '    "shortest": (1.70,')
    tmp = os.path.join(OUT_PREVIEW, "_reload_105_seat_raw.wav")
    ns = {"__file__": RELOAD_SYNTH, "__name__": "reload_synth"}
    argv = sys.argv; sys.argv = ["make_reload_105.py", "105", tmp, "seat"]
    try: exec(text, ns)
    finally: sys.argv = argv
    y = load(tmp); os.remove(tmp)
    return y


def reload_40():
    """40 mm: a 4-round clip dropped into the feed guides, the rounds pushed down, the clip pulled,
    the cocking ratchet, the breech slamming shut. Lighter and higher than the 105."""
    ns = reload_namespace(40); r = ns["rng"]
    dur = 2.35; N = int((dur + 1.0) * SR); mix = np.zeros(N)
    th, cl, sc, rg = ns["thump"], ns["clank"], ns["scrape"], ns["ring"]

    def put(t0, s, g): place(mix, s, t0, db(g))
    for tc in (0.00, 0.025, 0.06):                                    # the clip picked up, rounds rattle
        put(tc, cl(1500, 7000, 0.015, modes=24, contact_ms=0.15, noise=0.7), -22)
    put(0.30, cl(500, 6000, 0.040, modes=48, contact_ms=0.25, noise=1.0, noise_tau=0.04,
                 bounces=((0, 1), (0.012, 0.5), (0.027, 0.3)), ringers=3), -4)
    put(0.30, th(120, 60, 0.12, noise=0.6), -8)
    put(0.30, rg([88, 140, 230], 0.35, dur=1.2, amps=[1, 0.6, 0.2]), -16)
    for tc, g in ((0.36, -14), (0.40, -16), (0.45, -18)):            # the rounds settle in the guides
        put(tc, cl(1200, 8000, 0.020, modes=28, contact_ms=0.15, noise=0.8), g)
    put(0.62, sc(0.22, 300, 3500), -10)                                # pushed down
    put(0.86, cl(400, 4500, 0.040, modes=36, contact_ms=0.4, noise=0.9), -10)
    put(0.86, th(100, 60, 0.08, noise=0.5), -14)
    put(1.20, sc(0.12, 800, 6000, rise=False, grain=260), -14)         # the empty clip pulled out
    put(1.20, cl(2000, 9000, 0.015, modes=20, contact_ms=0.12, noise=0.6, click=0.4), -18)
    for tc, g in ((1.55, -12), (1.59, -11), (1.63, -10), (1.67, -9)):  # cocking ratchet
        put(tc, cl(1400, 9000, 0.020, modes=32, contact_ms=0.12, noise=0.9, noise_tau=0.016, click=0.5,
                   bounces=((0, 1), (r.uniform(0.004, 0.009), 0.4))), g)
        put(tc, th(r.uniform(110, 140), 75, 0.04, noise=0.7), g - 5)
    put(1.72, th(140, 70, 0.20, noise=0.6, pitch_tau=0.03), -4)       # breech slams shut
    put(1.72, cl(300, 7000, 0.060, modes=56, contact_ms=0.4, noise=1.0, noise_tau=0.05,
                 bounces=((0, 1), (0.010, 0.4)), ringers=4), -6)
    put(1.72, rg([120, 180, 260], 0.30, dur=1.0, amps=[1, 0.5, 0.15]), -14)
    put(2.00, cl(500, 5000, 0.030, modes=24, contact_ms=0.4, noise=0.8), -20)
    y = reload_master(ns, mix, dur)
    y *= np.minimum(1, (dur - tt(len(y))) / 0.05)
    return y


# ---- the sounds ------------------------------------------------------------------------------------
REF = {}


def ref_db(names):
    """Mean active RMS (dB) of the reference sounds of the same role."""
    vals = [active_rms_db(load(os.path.join(OWN if os.path.exists(os.path.join(OWN, n)) else SEAT, n))) for n in names]
    return float(np.mean(vals)), vals


made = []   # (file, signal, ref names, ref dB or None, target dB, sources, method)


def pre_roll(x):
    """A sound that hits at once: a 1 ms ramp on its first sample, then 4 ms of silence ahead of it,
    so the 5 ms edge fade lies on the silence and does not dull the attack."""
    x = x.copy(); r = int(0.001 * SR); x[:r] *= np.linspace(0, 1, r)
    return np.concatenate([np.zeros(int(0.004 * SR)), x])


def dc_zero(x):
    """The mean taken out with a smooth bump, so the faded edges stay at zero."""
    w = np.hanning(len(x))
    return x - x.mean() * len(x) / w.sum() * w


def make(file, y, refs, sources, method, target=None, offset=0.0, limiter=True, finish=True, pre=False):
    r, _ = ref_db(refs) if refs else (None, None)
    tgt = target if target is not None else r + offset
    gr = 0.0
    if finish:
        y = clean(y)
        if pre: y = pre_roll(y)
        gr = max(0.0, todb(np.abs(y).max() * db(tgt - active_rms_db(y))) - CEIL_DB)
        y = level(y, tgt, limiter); y = dc_zero(fades(y, 5, 5))
    made.append(dict(file=file, y=y, refs=refs, ref_db=r, target_db=tgt, sources=sources, method=method, gr=gr))
    return y


# 1 the 25mm, one round (played every 70 ms): since 2026-10-25 the user's own file (Codex, cut from
# a sound-effect video the user supplied; the 40mm likewise); taken here as it is
shot = load(os.path.join(SEAT, "sh_seat_25mm_fire.wav"))


def stream(x, period=0.070, secs=1.0):
    n = int(round(secs / period)) + 1
    out = np.zeros(int((period * (n - 1)) * SR) + len(x))
    for i in range(n): place(out, x, i * period)
    return out


rot_db, _ = ref_db(["sh_25mm_rotary_local.wav"])
make("sh_seat_25mm_fire.wav", shot, ["sh_25mm_rotary_local.wav"],
     [],
     "2026-10-25 사용자 제공 파일(Codex 가공, 효과음 영상에서 한 발 분리). 이 스크립트는 그대로 불러오기만 함",
     target=rot_db, finish=False)

# 2 the 40mm, one round: since 2026-10-25 the user's own file too (Codex), taken here as it is
y = load(os.path.join(SEAT, "sh_seat_40mm_fire.wav"))
make("sh_seat_40mm_fire.wav", y, [f"sh_40mm_report_{i}.wav" for i in range(1, 5)], [],
     "2026-10-25 사용자 제공 파일(Codex 가공). 이 스크립트는 그대로 불러오기만 함", finish=False)

# 3 the 105, one round
r105 = own("sh_105_report_1.wav"); r105 = r105[max(0, onset(r105) - int(0.005 * SR)):]
y = fit(r105, 3.6)
place(y, thump(90, 35, 0.25, 1.2, pitch_tau=0.02) * np.abs(y).max() * db(-8), 0.0)
y = fade_out_tail(y + filt(y, None, 100, 2) * db(-6), 0.8)
make("sh_seat_105mm_fire.wav", y, [f"sh_105_report_{i}.wav" for i in range(1, 4)], ["sh_105_report_1.wav"],
     "sh_105_report_1 앞 무음 잘라내기 + 3.6초로 자르기, 100Hz 아래 저역 보강(-6dB 레이어), "
     "합성 저역 킥(90→35Hz) -8dB, 마지막 0.8초 cos² 페이드")

# 5 the 40mm impacts
for i, (src, sp, L, lo, hi) in enumerate((("sh_40mm_impact_1.wav", 1.00, 2.2, None, None),
                                         ("sh_40mm_impact_2.wav", 0.92, 2.6, None, 5000),
                                         ("sh_40mm_impact_4.wav", 1.05, 2.0, 90, None)), 1):
    b = respeed(own(src), sp); b = filt(b, lo, hi, 2) if (lo or hi) else b
    y = fit(b, L)
    pk = np.abs(y).max()
    place(y, debris(L, 0.10, 70, 0.45) * pk * db(-22), 0.0)
    place(y, rumble(L, 0.55) * pk * db(-14), 0.0)
    y = fade_out_tail(y, 0.45)
    eq = {1: "", 2: ", 5kHz LPF", 3: ", 90Hz HPF"}[i]
    make(f"sh_seat_40mm_impact_{i}.wav", y, [f"sh_40mm_impact_{j}.wav" for j in range(1, 5)], [src],
         f"{src} 속도 {sp}배{eq}, 합성 파편 그레인 -22dB + 합성 저역 럼블 -14dB(감쇠 0.55초), {L}초, 꼬리 0.45초 cos² 페이드", pre=True)

# 6 the 105 impacts
for i, (src, sp, L, lo, hi, rum) in enumerate((("sh_105_impact_1.wav", 1.00, 2.2, None, None, -12),
                                              ("sh_105_impact_2.wav", 0.90, 2.6, None, None, -11),
                                              ("sh_105_impact_3.wav", 1.00, 2.0, None, 6000, -13),
                                              ("sh_105_impact_1.wav", 0.94, 2.8, None, 3000, -10),
                                              ("sh_105_impact_2.wav", 1.06, 1.8, 60, None, -14)), 1):
    b = respeed(own(src), sp); b = filt(b, lo, hi, 2) if (lo or hi) else b
    y = fit(b, L)
    pk = np.abs(y).max()
    place(y, debris(L, 0.12, 80, 0.6, 700, 5500) * pk * db(-20), 0.0)
    place(y, rumble(L, 0.8, 22, 150, 0.06) * pk * db(rum), 0.0)
    y = fade_out_tail(y, 0.6)
    eq = {1: "", 2: "", 3: ", 6kHz LPF", 4: ", 3kHz LPF(멀고 둔하게)", 5: ", 60Hz HPF"}[i]
    make(f"sh_seat_105mm_impact_{i}.wav", y, [f"sh_105_impact_{j}.wav" for j in range(1, 4)], [src],
         f"{src} 속도 {sp}배{eq}, 합성 파편 그레인 -20dB + 합성 저역 럼블 {rum}dB(감쇠 0.8초), {L}초, 꼬리 0.6초 cos² 페이드", pre=True)

# 7, 8 reloads
make("sh_seat_40mm_reload.wav", reload_40(), ["sh_reload_105.wav"], [],
     "합성: make_reload_105.py의 합성 함수(thump/clank/scrape/ring/room/압축/클리퍼)로 40mm용 새 타이밍 "
     "(클립 투입·탄 정렬·클립 뽑기·코킹 래칫·폐쇄기 닫힘), 시드 40, 2.35초. 녹음 재료 없음")
make("sh_seat_105mm_reload.wav", reload_105_seat(), ["sh_reload_105.wav"], [],
     "합성: make_reload_105.py(sh_reload_105와 같은 시드 105·같은 타격음)를 1.85초 배치로 다시 실행 — "
     "0~0.70초 폐쇄기 열림·탄피 배출(sh_reload_105의 앞부분과 같음), 0.75초 탄 장전, 1.15초 폐쇄기 닫힘. 녹음 재료 없음")

# 9 the kill tick
n = int(0.07 * SR); t = tt(n)
tick = (np.sin(2 * np.pi * 2400 * t) + 0.6 * np.sin(2 * np.pi * 3730 * t + 0.7)) * np.exp(-t / 0.009) * (1 - np.exp(-t / 0.0004))
place(tick, burst(0.01, 4000, 10000, 0.0008), 0.0, 0.25)
tick = filt(norm(tick), None, 7000, 2)
seat_fire_db, _ = ref_db(["sh_25mm_rotary_local.wav"] + [f"sh_40mm_report_{i}.wav" for i in range(1, 5)])
make("sh_seat_hitmarker.wav", tick, [], [],
     "합성: 2.4kHz + 3.73kHz 사인(9ms 감쇠) + 4~10kHz 클릭 노이즈, 7kHz LPF, 0.07초. "
     "음량은 사수석 발사음 기준(25mm 로터리·40mm 리포트 평균)보다 8dB 작게",
     target=seat_fire_db - 8, pre=True)

# 11 the engine loop (made before the entry and the departure, which start from it)
eng = own("sh_engine_loop.wav")            # build.js engineLoop: seamless 8 s, props at multiples of 1/8 Hz
L = 3 * len(eng); tl = tt(L); LS = L / SR
tiled = np.tile(eng, 3)
spec = np.abs(np.fft.rfft(eng)); f8 = np.fft.rfftfreq(len(eng), 1 / SR)
fL = np.fft.rfftfreq(L, 1 / SR)
sm = np.convolve(spec, np.ones(64) / 64, "same")                         # the bed's spectrum, smoothed
mag = np.interp(fL, f8, sm)
noise = np.fft.irfft(mag * np.exp(2j * np.pi * rng.random(len(fL))), L)  # random phases: periodic in L
noise = noise / np.sqrt(np.mean(noise ** 2)) * np.sqrt(np.mean(eng ** 2))
w = 0.6 + 0.25 * np.sin(2 * np.pi * tl / LS) + 0.1 * np.sin(2 * np.pi * 3 * tl / LS + 1.1)
bed = tiled * w + noise * (1 - w) * 0.9
props = np.zeros(L)
for k, fr in enumerate((68 + 1 / LS, 68.5 - 1 / LS, 67.625 + 2 / LS, 68.25 - 1 / LS)):  # all multiples of 1/LS
    ph = 2 * np.pi * fr * tl + k * 0.9
    props += np.sin(ph) * 0.30 + np.sin(2 * ph) * 0.14 + np.sin(3 * ph + 0.4) * 0.06
props = filt(props, None, 1500, 2, circular=True)
loop = bed + props * np.sqrt(np.mean(eng ** 2)) / np.sqrt(np.mean(props ** 2)) * db(-12)
loop = filt(loop, 20, 1600, 2, circular=True); loop -= loop.mean()      # cabin / ground: dull top, no DC
eng_db, _ = ref_db(["sh_engine_loop.wav"])
loop = loop * db(eng_db - active_rms_db(loop))
assert np.abs(loop).max() < db(CEIL_DB), "loop peak"
make("sh_ac130_engine_loop.wav", loop, ["sh_engine_loop.wav"], ["sh_engine_loop.wav"],
     "sh_engine_loop(8초 무이음 루프) 3번 이어붙여 24초 + 그 스펙트럼을 본뜬 24초 주기 노이즈(랜덤 위상 FFT 합성)를 "
     "24초 주기로 천천히 섞음 + 합성 프로펠러 4기 배음(1/24Hz 배수 주파수, -12dB). 원형(순환) 20Hz HPF·1.6kHz LPF. "
     "모든 층이 24초로 정확히 반복되므로 끝→처음 이음새 없음. 페이드 없음(루프)",
     target=eng_db, finish=False)

# 10 the entry (6.5 s over the entry video)
n = int(6.5 * SR); te = tt(n)
rate = 1.0 + 0.04 * np.exp(-tt(int(7 * SR)) / 2.5)                      # closing in: a little high, settling
appr = varispeed(np.concatenate([loop, loop]), rate)[:n]
appr = tv_lowpass(appr, lambda s: 350 * (1600 / 350) ** min(1, max(0, s) / 4.5))
gain = db(-18 + 18 * np.minimum(1, te / 4.8) ** 0.7)
entry = appr * gain
fl = own("sh_gunner_flare.wav"); fpk = np.abs(entry).max()
for tf in (1.10, 1.36, 1.60, 1.87, 2.12, 2.40, 2.66, 2.95, 3.22):
    s = respeed(fl, rng.uniform(0.95, 1.05)) * db(rng.uniform(-3, 0))
    place(entry, s * fpk * 1.1, tf)
    place(entry, thump(220, 90, 0.02, 0.1) * fpk * 0.45, tf)              # the cartridge pop
st = own("sh_gunner_static.wav")[:int(0.35 * SR)]
place(entry, st * fpk * 1.2, 6.15)
nb = int(0.04 * SR); tb = tt(nb)
blip = np.sin(2 * np.pi * np.cumsum(1200 + 1200 * tb / 0.04) / SR) * np.exp(-tb / 0.02)
place(entry, blip * fpk * 0.35, 6.15)                                    # sensor switch
make("sh_seat_entry.wav", entry, ["sh_engine_loop.wav"],
     ["sh_engine_loop.wav (11번 루프 경유)", "sh_gunner_flare.wav", "sh_gunner_static.wav"],
     "11번 엔진 루프를 접근하듯 가공(속도 1.04→1.0 도플러, 350Hz→1.6kHz로 열리는 시변 LPF, -18dB→0dB 상승) + "
     "sh_gunner_flare 9발(1.10~3.22초, 속도 0.95~1.05배·-3~0dB 무작위) + 합성 탄통 팝 + 6.15초 sh_gunner_static 0.35초 "
     "잘라내기 + 합성 1.2→2.4kHz 전환음, 6.5초")

# 12 the departure
nd = int(6.0 * SR); td = tt(nd)
rate = 1.0 - 0.07 * (np.minimum(1, tt(int(7 * SR)) / 6.0) ** 1.5)       # going away: the pitch sags
dep = varispeed(np.concatenate([loop, loop]), rate)[:nd]
dep = tv_lowpass(dep, lambda s: 1600 * (120 / 1600) ** min(1, max(0, s) / 6.0))
dep = dep * np.cos(np.linspace(0, np.pi / 2, nd)) ** 2.5
dep = clean(dep); dep = dep * db(eng_db - active_rms_db(dep[:int(1.0 * SR)])); dep = fades(dep, 5, 5)
make("sh_ac130_engine_depart.wav", dep, ["sh_engine_loop.wav"], ["sh_engine_loop.wav (11번 루프 경유)"],
     "11번 엔진 루프의 처음부터 6초: 속도 1.0→0.93(멀어지는 도플러), 1.6kHz→120Hz로 닫히는 시변 LPF, "
     "cos^2.5 음량 감소로 무음까지. 첫 1초 음량을 루프와 같게",
     target=eng_db, finish=False)


# ---- write + checks --------------------------------------------------------------------------------
def write(path, y):
    q = np.round(np.clip(y, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(q.tobytes())
    return q.astype(float) / 32767, int(np.sum(np.abs(q.astype(int)) >= 32767))


def seam_check(x):
    """The loop's end -> start compared with every other spot in the file."""
    d = np.abs(np.diff(np.concatenate([x, x[:1]])))
    blk = int(0.01 * SR); xx = np.concatenate([x, x])
    r = np.array([todb(np.sqrt(np.mean(xx[i:i + blk] ** 2))) for i in range(0, len(x), blk)])
    rd = np.abs(np.diff(np.concatenate([r, r[:1]])))
    win = np.hanning(2048)

    def flux(c):
        a = np.abs(np.fft.rfft(xx[c - 2048:c] * win)); b = np.abs(np.fft.rfft(xx[c:c + 2048] * win))
        return float(np.sqrt(np.mean((a - b) ** 2)) / (np.sqrt(np.mean(a ** 2)) + 1e-12))
    others = [flux(c) for c in range(4096, len(x) - 4096, len(x) // 60)]
    return dict(wrap_jump=float(d[-1]), step_p99=float(np.percentile(d[:-1], 99)),
                wrap_rms_step_db=float(rd[-1]), rms_step_p99_db=float(np.percentile(rd[:-1], 99)),
                wrap_spectral_flux=flux(len(x)), flux_p99=float(np.percentile(others, 99)),
                passed=bool(d[-1] <= np.percentile(d[:-1], 99) and rd[-1] <= np.percentile(rd[:-1], 99)
                            and flux(len(x)) <= np.percentile(others, 99)))


def stream_check(x):
    s = stream(x); per = int(0.070 * SR); blk = int(0.002 * SR); depth = []
    for i in range(14):
        a = s[i * per:(i + 1) * per]
        r = np.array([np.sqrt(np.mean(a[j:j + blk] ** 2)) for j in range(0, len(a) - blk, blk)])
        depth.append(todb(r.max()) - todb(r[-8:].min()))
    tail = todb(np.sqrt(np.sum(x[per:] ** 2) / np.sum(x ** 2)))
    return dict(shots=15, period_ms=70, stream_peak_dbfs=todb(np.abs(s).max()),
                stream_clipped_samples=int(np.sum(np.abs(s) >= 1.0)), stream_active_rms_db=active_rms_db(s),
                min_shot_separation_db=float(min(depth)), energy_after_70ms_db=tail,
                passed=bool(np.abs(s).max() < 1.0 and min(depth) >= 12 and tail <= -20)), s


report = []
for m in made:
    path = os.path.join(SEAT, m["file"]); q, clipped = write(path, m["y"])
    with open(path, "rb") as fh: sha = hashlib.sha256(fh.read()).hexdigest()
    a = active_rms_db(q)
    e = dict(file=m["file"], seconds=round(len(q) / SR, 3), peak_dbfs=round(todb(np.abs(q).max()), 2),
             rms_dbfs=round(todb(np.sqrt(np.mean(q ** 2))), 2), active_rms_dbfs=round(a, 2),
             dc_offset=float(f"{q.mean():.2e}"), clipped_samples=clipped,
             edge_start=float(abs(q[0])), edge_end=float(abs(q[-1])),
             limiter_peak_reduction_db=round(m["gr"], 2),
             reference=m["refs"], reference_active_rms_db=None if m["ref_db"] is None else round(m["ref_db"], 2),
             target_active_rms_db=round(m["target_db"], 2), sha256=sha, sources=m["sources"], method=m["method"])
    if m["ref_db"] is not None and m["file"] != "sh_seat_25mm_fire.wav":
        e["delta_vs_reference_db"] = round(a - m["ref_db"], 2)
    if m["file"] == "sh_ac130_engine_loop.wav": e["seam_check"] = seam_check(q)
    if m["file"] == "sh_seat_25mm_fire.wav":
        e["stream_check"], s25 = stream_check(q)
        e["delta_vs_reference_db"] = round(e["stream_check"]["stream_active_rms_db"] - m["ref_db"], 2)
    if m["file"] == "sh_ac130_engine_depart.wav":
        e["first_1s_active_rms_db"] = round(active_rms_db(q[:SR]), 2)
        e["delta_vs_reference_db"] = round(e["first_1s_active_rms_db"] - m["ref_db"], 2)
    if m["file"] == "sh_seat_entry.wav":
        e["delta_vs_reference_db"] = round(a - m["ref_db"], 2)
    report.append(e)

# previews: everything in one file (0.6 s apart, the 25mm also as a 1 s stream, the loop twice
# around its seam), and the 25mm stream and the loop seam on their own
gap = np.zeros(int(0.6 * SR)); parts = []
for e in report:
    q = load(os.path.join(SEAT, e["file"]))
    if e["file"] == "sh_seat_25mm_fire.wav": parts += [q, gap, stream(q), gap]
    elif e["file"] == "sh_ac130_engine_loop.wav": parts += [q[-int(6 * SR):], q[:int(6 * SR)], gap]
    else: parts += [q, gap]
write(os.path.join(OUT_PREVIEW, "preview_all.wav"), np.concatenate(parts))
write(os.path.join(OUT_PREVIEW, "preview_25mm_stream_1s.wav"), stream(load(os.path.join(SEAT, "sh_seat_25mm_fire.wav"))))
lp = load(os.path.join(SEAT, "sh_ac130_engine_loop.wav"))
write(os.path.join(OUT_PREVIEW, "preview_engine_loop_x2.wav"), np.concatenate([lp, lp]))
with open(os.path.join(OUT_PREVIEW, "report.json"), "w", encoding="utf-8") as fh:
    json.dump(report, fh, ensure_ascii=False, indent=1)
for e in report:
    print(f'{e["file"]:32s} {e["seconds"]:6.3f}s peak {e["peak_dbfs"]:6.2f} act {e["active_rms_dbfs"]:6.2f} '
          f'ref {e["reference_active_rms_db"]} d {e.get("delta_vs_reference_db")} clip {e["clipped_samples"]} '
          f'gr {e["limiter_peak_reduction_db"]} dc {e["dc_offset"]} edges {e["edge_start"]:.4f}/{e["edge_end"]:.4f}')
    for key in ("seam_check", "stream_check"):
        if key in e: print("   ", key, e[key])
