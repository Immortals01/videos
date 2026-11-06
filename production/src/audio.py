"""Original score, sound design and mix for "Abandoned, But Not Forgotten".

Everything is synthesized procedurally with numpy/scipy (no samples, no third-party music):
  piano (inharmonic additive), string ensemble (detuned saws), horns, timpani, celesta,
  impacts, risers, whooshes, rocket, thrusters, servos, radio static, data ticks, winds.
Writes 48 kHz stereo stems to audio/stems/ and audio/mix_premaster.wav.
"""
import functools, math, os, sys
import numpy as np, soundfile as sf
from scipy import signal

sys.path.insert(0, os.path.dirname(__file__))
from timeline import T, E, SCENES, DURATION
from script_lines import LINES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000
N = int(round(DURATION * SR))
SC = {k: v[0] for k, v in SCENES.items()}
rng = np.random.default_rng(1967)
OUT = os.path.join(ROOT, "audio", "stems")
os.makedirs(OUT, exist_ok=True)


# ============================================================================ basics
def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def nm(s):
    """'F#4' -> midi"""
    pc = _PC[s[0]]
    i = 1
    if s[i] == "#":
        pc += 1; i += 1
    elif s[i] == "b":
        pc -= 1; i += 1
    return 12 * (int(s[i:]) + 1) + pc


def chord(s):
    return [nm(x) for x in s.split()]


def tv(n):
    return np.arange(n, dtype=np.float64) / SR


def buf():
    return np.zeros((2, N), np.float32)


def place(dst, x, t0, gain=1.0, pan=0.0):
    """Add mono (n,) or stereo (2,n) signal x into dst starting at t0 seconds."""
    if x.ndim == 1:
        a = (pan + 1) * math.pi / 4
        x = np.stack([x * math.cos(a), x * math.sin(a)]) * math.sqrt(2)
    a = int(round(t0 * SR))
    s0 = max(0, -a)
    a = max(0, a)
    n = min(x.shape[1] - s0, N - a)
    if n > 0:
        dst[:, a:a + n] += x[:, s0:s0 + n] * gain
    return dst


@functools.lru_cache(maxsize=None)
def _sos(kind, f, order):
    return signal.butter(order, f, kind, fs=SR, output="sos")


def lp(x, f, order=2):
    return signal.sosfilt(_sos("lowpass", float(f), order), x, axis=-1).astype(np.float32)


def hp(x, f, order=2):
    return signal.sosfilt(_sos("highpass", float(f), order), x, axis=-1).astype(np.float32)


def bp(x, f0, f1, order=2):
    return signal.sosfilt(_sos("bandpass", (float(f0), float(f1)), order), x, axis=-1).astype(np.float32)


def noise(n, ch=1):
    x = rng.standard_normal((ch, n)).astype(np.float32)
    return x[0] if ch == 1 else x


def brown(n, ch=1):
    x = np.cumsum(rng.standard_normal((ch, n)), axis=1)
    x = hp(x.astype(np.float32), 18, 1)
    x /= np.abs(x).max() + 1e-9
    return x[0] if ch == 1 else x


def smoothstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def env_note(n, dur, att, rel, att_curve="cos"):
    t = tv(n)
    e = np.ones(n)
    if att > 0:
        e = np.where(t < att, 0.5 - 0.5 * np.cos(np.pi * np.clip(t / att, 0, 1)), 1.0)
    e = e * np.where(t > dur, np.exp(-(t - dur) * 5.0 / max(rel, 1e-3)), 1.0)
    k = min(n, int(0.004 * SR))
    e[-k:] *= np.linspace(1, 0, k)
    return e.astype(np.float32)


def shape_env(n, pts):
    """Piecewise-linear envelope from [(t, value), ...] in seconds relative to start."""
    t = tv(n)
    xs, ys = zip(*pts)
    return np.interp(t, xs, ys).astype(np.float32)


def saw(f, n, vib=0.0, vib_rate=5.5, vib_delay=0.6):
    t = tv(n)
    if vib:
        fi = f * (1 + vib * np.sin(2 * np.pi * vib_rate * t + rng.uniform(0, 6.28)) * np.clip(t / vib_delay, 0, 1))
        ph = np.cumsum(fi) / SR + rng.random()
    else:
        ph = f * t + rng.random()
    return (2 * (ph % 1.0) - 1).astype(np.float32)


def stereo(x, width=0.0):
    return np.stack([x, x])


# ============================================================================ instruments
def strings_note(m, dur, vel=0.5, att=0.8, rel=1.5, bright=2400.0, voices=6, det=9.0, vib=0.0028):
    n = int((dur + rel) * SR)
    f = mtof(m)
    out = np.zeros((2, n), np.float32)
    for i in range(voices):
        c = ((i / (voices - 1)) * 2 - 1) * det + rng.normal(0, 1.5)
        s = saw(f * 2 ** (c / 1200), n, vib=vib, vib_rate=4.8 + rng.random() * 1.4, vib_delay=att + 0.3)
        a = (i / (voices - 1) * 1.3 - 0.65 + 1) * math.pi / 4
        out[0] += s * math.cos(a)
        out[1] += s * math.sin(a)
    br = min(bright * (0.6 + 0.6 * vel), SR * 0.45)
    out = lp(lp(out, br, 2), br * 1.7, 1)
    out = hp(out, 70, 2)
    return out * env_note(n, dur, att, rel) * (vel / voices) * 1.6


def strings_chord(dst, t0, dur, notes, vel=0.5, **kw):
    for m in notes:
        place(dst, strings_note(m, dur, vel * (0.85 if m < 48 else 1.0), **kw), t0)


def stacc(m, vel=0.5, dur=0.16, bright=2600):
    """Short bowed (spiccato) string note."""
    n = int((dur + 0.25) * SR)
    f = mtof(m)
    x = sum(saw(f * 2 ** (c / 1200), n) for c in (-7, -2, 4, 9)) / 4
    x = lp(lp(x, bright * (0.6 + 0.6 * vel)), bright * 1.5, 1)
    e = env_note(n, dur, 0.012, 0.18)
    return hp(x * e * vel, 60)


@functools.lru_cache(maxsize=None)
def _piano_raw(m, velq):
    vel = velq / 20.0
    f = mtof(m)
    L = float(np.clip(1.8 + 700.0 / f, 1.8, 7.0))
    n = int(L * SR)
    t = tv(n)
    x = np.zeros(n)
    B = 0.00035 * (f / 261.0) ** 0.5
    for k in range(1, 11):
        fk = f * k * math.sqrt(1 + B * k * k)
        if fk > 11000:
            break
        amp = (1.0 / k ** 1.15) * vel ** (0.4 + 0.12 * k)
        tau1 = 0.35 * (261.0 / f) ** 0.4 / (1 + 0.25 * k)
        tau2 = 3.2 * (261.0 / f) ** 0.55 / (1 + 0.35 * (k - 1))
        dec = 0.55 * np.exp(-t / tau1) + 0.45 * np.exp(-t / tau2)
        ph = rng.uniform(0, 6.28)
        x += amp * dec * (np.sin(2 * np.pi * (fk - 0.12) * t + ph) + np.sin(2 * np.pi * (fk + 0.12) * t + ph * 1.3)) * 0.5
    att = int(0.002 * SR)
    x[:att] *= np.linspace(0, 1, att)
    h = int(0.012 * SR)
    hn = rng.standard_normal(h) * np.exp(-np.arange(h) / (0.002 * SR))
    x[:h] += lp(hn.astype(np.float32), 2500 + 2000 * vel) * 0.08 * vel
    return (x * 0.5).astype(np.float32)


def piano(m, vel=0.6, dur=None):
    x = _piano_raw(m, int(round(np.clip(vel, 0.05, 1.0) * 20))).copy()
    if dur is not None:
        t = tv(len(x))
        x *= np.where(t > dur, np.exp(-(t - dur) / 0.18), 1.0).astype(np.float32)
    return x


def pplay(dst, t0, m, vel=0.6, dur=None, pan=None):
    pan = (m - 64) / 40.0 if pan is None else pan
    place(dst, piano(m, vel, dur), t0, pan=float(np.clip(pan, -0.6, 0.6)))


def celesta(m, vel=0.4):
    f = mtof(m)
    n = int(2.2 * SR)
    t = tv(n)
    x = np.zeros(n)
    for r, a, d in ((1, 1, 1.1), (2.0, 0.25, 0.5), (3.0, 0.12, 0.3), (4.17, 0.08, 0.18)):
        x += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d)
    x[:96] *= np.linspace(0, 1, 96)
    return (x * vel * 0.4).astype(np.float32)


def horn_note(m, dur, vel=0.5, att=0.35, rel=0.9):
    n = int((dur + rel) * SR)
    f = mtof(m)
    x = sum(saw(f * 2 ** (c / 1200), n, vib=0.0015, vib_rate=5.0) for c in (-5, 0, 6)) / 3
    dark, brt = lp(lp(x, 500), 900, 1), lp(lp(x, 1400 + 1800 * vel), 3000, 1)
    e = env_note(n, dur, att, rel)
    fe = e ** 2 * vel
    y = dark * (1 - fe) + brt * fe
    return hp(y * e * vel, 80) * 1.3


def horn_chord(dst, t0, dur, notes, vel=0.5, **kw):
    for i, m in enumerate(notes):
        place(dst, horn_note(m, dur, vel, **kw), t0, pan=(i / max(1, len(notes) - 1) - 0.5) * 0.5)


def timp(m, vel=0.8, decay=1.6):
    f = mtof(m)
    n = int(decay * 2.2 * SR)
    t = tv(n)
    fd = 1 + 0.06 * np.exp(-t / 0.04)
    x = np.zeros(n)
    for r, a, d in ((1, 1, decay), (1.504, 0.55, decay * 0.6), (1.742, 0.35, decay * 0.45), (2.0, 0.25, decay * 0.4),
                    (2.245, 0.15, decay * 0.3)):
        x += a * np.sin(2 * np.pi * np.cumsum(f * r * fd) / SR) * np.exp(-t / d)
    k = int(0.08 * SR)
    x[:k] += lp(noise(k), 600) * np.exp(-np.arange(k) / (0.015 * SR)) * 0.6
    x[:64] *= np.linspace(0, 1, 64)
    return (x * vel * 0.6).astype(np.float32)


def timp_roll(dst, t0, t1, m, v0=0.15, v1=0.8):
    t = t0
    while t < t1:
        k = (t - t0) / (t1 - t0)
        place(dst, timp(m, (v0 + (v1 - v0) * k ** 1.6) * rng.uniform(0.85, 1.0), 0.6), t, pan=rng.uniform(-0.15, 0.15))
        t += 0.065 + rng.uniform(-0.008, 0.008)


def pluck(m, vel=0.3, decay=0.35):
    f = mtof(m)
    n = int(decay * 4 * SR)
    t = tv(n)
    x = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) * np.exp(-t / (decay * 0.4))) * np.exp(-t / decay)
    x[:48] *= np.linspace(0, 1, 48)
    return (x * vel).astype(np.float32)


def sub_drop(f0=58, f1=28, dur=2.8, vel=1.0):
    n = int(dur * SR)
    t = tv(n)
    f = f1 + (f0 - f1) * np.exp(-t / 0.35)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (dur * 0.35))
    x[:96] *= np.linspace(0, 1, 96)
    return (np.tanh(x * 1.6) * vel).astype(np.float32)


def impact(vel=1.0, dur=3.0, bright=1.0):
    n = int(dur * SR)
    x = np.zeros((2, n), np.float32)
    s = sub_drop(62, 30, dur, 1.0)
    x += s
    k = int(0.5 * SR)
    th = lp(noise(k, 2), 900) * np.exp(-np.arange(k) / (0.07 * SR))
    x[:, :k] += th * 0.8
    k2 = int(dur * SR)
    cr = hp(noise(k2, 2), 4500) * np.exp(-np.arange(k2) / (0.7 * SR)) * 0.18 * bright
    x += cr
    return x * vel


def crash(vel=0.5, dur=3.5):
    n = int(dur * SR)
    x = hp(noise(n, 2), 3800) * np.exp(-np.arange(n) / (0.9 * SR))
    x += bp(noise(n, 2), 2500, 7000) * np.exp(-np.arange(n) / (0.25 * SR)) * 0.5
    return x * vel * 0.35


def reverse_swell(dur=1.2, vel=0.5):
    n = int(dur * SR)
    e = (np.arange(n) / n) ** 3
    x = hp(noise(n, 2), 2500) * e * 0.35 + bp(noise(n, 2), 300, 2500) * e * 0.25
    x[:, -64:] *= np.linspace(1, 0, 64)
    return x * vel


def sweep_noise(dur, f0, f1, bw=0.6, ch=2, shape=None, src=None):
    """Noise through a band whose centre glides f0->f1 (log), STFT-domain."""
    n = int(dur * SR)
    x = noise(n, ch) if src is None else src
    nper = 2048
    f, tt, Z = signal.stft(x, SR, nperseg=nper, noverlap=nper * 3 // 4)
    fr = np.linspace(0, 1, Z.shape[-1]) if shape is None else np.interp(np.linspace(0, dur, Z.shape[-1]),
                                                                           np.linspace(0, dur, len(shape)), shape)
    fc = np.exp(np.log(f0) + (np.log(f1) - np.log(f0)) * fr)
    lf = np.log(np.maximum(f, 1.0))[:, None]
    g = np.exp(-((lf - np.log(fc)[None]) / bw) ** 2)
    Z = Z * g
    _, y = signal.istft(Z, SR, nperseg=nper, noverlap=nper * 3 // 4)
    y = y[..., :n].astype(np.float32)
    if y.shape[-1] < n:
        y = np.pad(y, [(0, 0)] * (y.ndim - 1) + [(0, n - y.shape[-1])])
    return y / (np.abs(y).max() + 1e-9)


def whoosh(dur=1.2, vel=0.5, f0=250, f1=3500, peak=0.6):
    n = int(dur * SR)
    y = sweep_noise(dur, f0, f1, bw=0.7)
    e = shape_env(n, [(0, 0), (dur * peak, 1), (dur, 0)]) ** 1.5
    # slight doppler stereo motion L -> R
    pan = np.linspace(-0.6, 0.6, n)
    a = (pan + 1) * math.pi / 4
    return np.stack([y[0] * np.cos(a), y[1] * np.sin(a)]) * e * vel * 1.2


def riser(dur=2.0, vel=0.5, f0=300, f1=6000):
    n = int(dur * SR)
    y = sweep_noise(dur, f0, f1, bw=0.5, shape=np.linspace(0, 1, 50) ** 1.7)
    e = (np.arange(n) / n) ** 2.2
    t = tv(n)
    tone = np.sin(2 * np.pi * np.cumsum(110 * 2 ** (2.5 * (t / dur) ** 1.5)) / SR) * 0.25
    out = y * e * 0.8 + np.stack([tone, tone]) * e
    out[:, -96:] *= np.linspace(1, 0, 96)
    return out * vel


# ============================================================================ SCORE
def score():
    mus = buf()
    S = SC

    # ---------------- Scene 1: the mysterious signal (ambience + radio + emerging shimmer)
    n = int(9.5 * SR)
    dr = np.zeros((2, n), np.float32)
    for m, a in ((nm("D1"), 1.0), (nm("D2"), 0.5), (nm("A2"), 0.18)):
        dr += np.stack([saw(mtof(m) * 1.001, n), saw(mtof(m) * 0.999, n)]) * a
    dr = lp(lp(dr, 160), 220, 1) * shape_env(n, [(0, 0), (2.5, 0.8), (6.0, 1.0), (7.5, 0.6), (9.5, 0)])
    place(mus, dr, 0.0, 0.5)
    place(mus, sub_drop(55, 27, 4.0, 0.9), 0.18, 0.8)                      # hook: deep pulse from the dark
    for m, t0 in ((nm("A4"), 2.4), (nm("E5"), 2.9), (nm("D5"), 3.5), (nm("F#5"), 4.6)):   # shimmer as the Moon appears
        place(mus, strings_note(m, 7.4 - t0, 0.22, att=2.4, rel=1.6, bright=3500, vib=0.002), t0)
    place(mus, reverse_swell(1.6, 0.35), 7.0 - 1.6)

    # ---------------- Scene 2: soft piano + warm strings
    e8 = 0.3667
    s2 = [(7.0, "D2", "D3 A3 E4 F#4 A4", "D3 A3 F#4 C#5", ("F#5", "E5")),
          (9.2, "B1", "B2 F#3 D4 F#4 A4", "B2 F#3 D4 A4", ("D5", "C#5")),
          (11.4, "G1", "G2 D3 B3 D4 F#4", "G2 D3 B3 F#4", ("B4", "D5")),
          (13.6, "A1", "A2 E3 D4 E4 A4", "A2 E3 D4 A4", ("E5", "C#5"))]
    for i, (t0, bass, arp, st, mel) in enumerate(s2):
        dur = 2.2 if i < 3 else 2.25
        a = chord(arp)
        pplay(mus, t0, nm(bass) + 12, 0.42, dur + 0.3)
        for j, idx in enumerate((0, 1, 2, 3, 4, 3)):
            pplay(mus, t0 + j * e8 + 0.01 * rng.random(), a[idx], 0.30 + 0.04 * (j == 0), None)
        pplay(mus, t0 + 0.02, nm(mel[0]), 0.5, 1.1)
        pplay(mus, t0 + 1.1, nm(mel[1]), 0.44, 1.0)
        strings_chord(mus, t0 - 0.15, dur + 0.15, chord(st), 0.30 + 0.05 * i, att=1.3, rel=1.4)
    pplay(mus, 14.7, nm("C#4"), 0.25, 1.0)
    place(mus, strings_note(nm("C#4"), 1.0, 0.3, att=0.4, rel=0.5), 14.7)

    # ---------------- Scene 3: orchestral build (launch -> cruise -> descent -> touchdown)
    t_fl = S[3]
    place(mus, reverse_swell(1.1, 0.7), t_fl - 1.1)
    place(mus, impact(0.9, 3.5), t_fl)
    place(mus, timp(nm("B1"), 1.0, 2.0), t_fl)
    place(mus, crash(0.6), t_fl)
    q = 0.25                                                                 # 120 bpm eighths
    launch = [(t_fl, "B1", "B2 F#3 B3 D4", "B2 F#3 D4"), (t_fl + 2.0, "G1", "G2 D3 G3 B3", "G2 D3 B3"),
              (t_fl + 4.0, "D2", "D3 A3 D4 F#4", "D3 A3 F#4")]
    for k, (t0, b, st, hn) in enumerate(launch):
        r = nm(b) + 12
        for j in range(8):
            if t0 + j * q > 20.2:
                break
            for o, v in ((0, 0.42), (12, 0.30)):
                place(mus, stacc(r + o + (7 if j % 4 == 2 else 0), v * (1.15 if j % 4 == 0 else 1.0)), t0 + j * q,
                      pan=-0.3 if o == 0 else 0.3)
        strings_chord(mus, t0, 2.0, chord(st), 0.5 + 0.1 * k, att=0.25, rel=0.9)
        horn_chord(mus, t0 + 0.05, 1.8, chord(hn), 0.45 + 0.12 * k, att=0.3)
        place(mus, timp(r - 12, 0.7 + 0.1 * k, 1.4), t0)
        place(mus, timp(r - 12, 0.45, 1.0), t0 + 1.0)
    # cruise: wonder (sustains + celesta)
    strings_chord(mus, 20.0, 2.2, chord("D3 A3 F#4 C#5 E5"), 0.36, att=1.4, rel=1.6, bright=3000)
    strings_chord(mus, 22.15, 2.2, chord("C#3 A3 E4 A4 E5"), 0.36, att=1.0, rel=1.4, bright=3000)
    for i, m in enumerate(["A5", "C#6", "E6", "F#6", "E6", "C#6", "A5", "E6", "C#6", "A5", "E5", "A5"]):
        place(mus, celesta(nm(m), 0.35), 20.1 + i * 0.36, pan=math.sin(i) * 0.5)
    pplay(mus, 20.05, nm("D2"), 0.45, 2.2)
    pplay(mus, 22.15, nm("C#2"), 0.4, 2.0)
    # descent: tension
    desc = [(24.25, "E1", "E2 B2 G3 B3", 1.5), (25.75, "G1", "G2 D3 B3 D4", 1.5), (27.25, "A1", "A2 E3 A3 D4", 0.75),
            (28.0, "A1", "A2 E3 A3 C#4 E4", 0.76)]
    for k, (t0, b, st, d) in enumerate(desc):
        r = nm(b) + 12
        j = 0
        while j * q < d - 1e-3:
            place(mus, stacc(r + (12 if j % 2 else 0), 0.30 + 0.06 * k), t0 + j * q, pan=-0.2)
            place(mus, stacc(r + 19 + (5 if j % 4 == 3 else 0), 0.22 + 0.05 * k), t0 + j * q, pan=0.25)
            j += 1
        strings_chord(mus, t0, d, chord(st), 0.36 + 0.08 * k, att=0.5, rel=0.4)
    horn_chord(mus, 27.25, 1.5, chord("A2 E3 A3 C#4"), 0.55, att=1.2, rel=0.2)
    timp_roll(mus, 27.7, 28.74, nm("A1"), 0.15, 0.8)
    place(mus, riser(1.4, 0.35), 28.76 - 1.4)
    # touchdown: resolution on D major
    td = S[3] + 12.95
    place(mus, impact(0.8, 3.0, 0.6), td)
    place(mus, timp(nm("D2"), 1.0, 2.2), td)
    place(mus, crash(0.45), td)
    horn_chord(mus, td, 1.6, chord("D3 A3 D4 F#4"), 0.7, att=0.02, rel=1.6)
    strings_chord(mus, td, 3.2, chord("D2 A2 F#3 D4 F#4 A4"), 0.55, att=0.05, rel=2.2)
    place(mus, timp(nm("D2"), 0.45, 1.2), td + 0.75)
    for i, (m, dt) in enumerate((("F#5", 0.9), ("E5", 1.8), ("D5", 2.6))):
        pplay(mus, td + dt, nm(m), 0.38, 1.2)
    strings_chord(mus, 31.2, 1.6, chord("D3 A3 E4 F#4"), 0.25, att=0.8, rel=1.2)

    # ---------------- Scene 4: subtle scientific pulse
    s4 = [(S[4], "E2", "E3 B3 F#4 G4", "E4 G4 B4 F#5"), (S[4] + 3.0, "C2", "C3 G3 B3 E4", "E4 G4 B4 C5"),
          (S[4] + 6.0, "G1", "G2 D3 B3 E4", "D4 G4 B4 E5"), (S[4] + 9.0, "F#1", "F#2 D3 A3 E4", "D4 F#4 A4 D5")]
    s16 = 0.1875
    for k, (t0, b, st, arp) in enumerate(s4):
        a = chord(arp)
        strings_chord(mus, t0, 3.0, chord(st), 0.24, att=0.9, rel=1.0, bright=1800)
        pplay(mus, t0, nm(b) + 12, 0.32, 2.8)
        for j in range(16):
            tt = t0 + j * s16
            if tt > 44.2:
                break
            m = a[[0, 1, 2, 3, 2, 1, 0, 2][j % 8]] + (12 if j >= 8 else 0)
            place(mus, pluck(m, 0.13 + 0.03 * (j % 4 == 0), 0.22), tt, pan=0.35 if j % 2 else -0.35)
            place(mus, pluck(m, 0.05, 0.2), tt + s16 * 1.5, pan=-0.5 if j % 2 else 0.5)   # dotted echo
    place(mus, reverse_swell(1.4, 0.3), 44.4 - 1.4)

    # ---------------- Scene 5: emotional centrepiece (Apollo 12)
    e5 = 0.4
    pplay(mus, 44.5, nm("B2"), 0.32, 3.0)
    pplay(mus, 44.52, nm("F#3"), 0.26, 3.0)
    for m, t0, v in (("D5", 45.25, 0.34), ("C#5", 46.05, 0.3), ("B4", 46.85, 0.3), ("F#4", 47.2, 0.2)):
        pplay(mus, t0, nm(m), v, 0.9)
    place(mus, strings_note(nm("F#5"), 3.0, 0.12, att=2.0, rel=1.4, bright=3200), 44.6)
    s5 = [(47.6, 2.4, "G1", "G2 D3 B3 D4", "G2 D3 B3 D4", 0.30, ("B4", 1.2, "A4", 1.2)),
          (50.0, 2.4, "F#1", "F#2 A3 D4 F#4", "F#2 A3 D4", 0.33, ("F#4", 1.2, "A4", 1.2)),
          (52.4, 2.4, "E1", "E2 G3 B3 D4", "E2 G3 B3 D4", 0.36, ("G4", 0.8, "B4", 0.8, "D5", 0.8)),
          (54.8, 2.4, "A1", "A2 E3 A3 D4", "A2 E3 A3 C#4", 0.40, ("C#5", 1.2, "E5", 1.2)),
          (57.2, 1.7, "B1", "B2 F#3 B3 D4 F#4", "B2 F#3 D4 F#4", 0.48, ("F#5", 0.85, "E5", 0.85)),
          (58.9, 1.3, "G1", "G2 D3 B3 D4 G4", "G2 D3 G3 B3", 0.56, ("D5", 1.3)),
          (60.2, 1.3, "A1", "A2 E3 C#4 E4 A4", "A2 E3 A3 C#4", 0.64, ("C#5", 1.3)),
          (61.5, 2.6, "D1", "D2 A2 F#3 D4 F#4 A4", "D3 A3 D4 F#4", 0.70, ("D5", 2.6))]
    for k, (t0, d, b, st, arp, v, mel) in enumerate(s5):
        a = chord(arp)
        pplay(mus, t0, nm(b) + 12, 0.42 + 0.03 * k, d + 0.4)
        pplay(mus, t0 + 0.005, nm(b) + 24, 0.30, d + 0.4)
        j = 0
        while j * e5 < d - 1e-3:
            pplay(mus, t0 + j * e5 + 0.012 * rng.random(), a[[1, 2, 3, 2, 1, 3][j % 6] % len(a)], 0.22 + 0.03 * (j == 0), None)
            j += 1
        tt = t0
        for m, dd in zip(mel[0::2], mel[1::2]):
            pplay(mus, tt + 0.015, nm(m), 0.5 + 0.03 * k, dd)
            tt += dd
        strings_chord(mus, t0 - 0.1, d + 0.1, chord(st), v, att=1.6 if k < 4 else 0.7, rel=1.8 if k < 7 else 3.0,
                      bright=2200 + 200 * k)
        if k >= 4:
            place(mus, strings_note(nm(mel[0]) , d, v * 0.55, att=0.5, rel=1.2, bright=3200), t0)  # violins double melody
    horn_chord(mus, 57.2, 4.3, chord("D3 F#3 B3"), 0.32, att=1.5, rel=0.5)
    horn_chord(mus, 61.5, 2.4, chord("D3 A3 D4 F#4"), 0.5, att=0.4, rel=2.5)
    timp_roll(mus, 60.6, 61.48, nm("A1"), 0.08, 0.45)
    place(mus, timp(nm("D2"), 0.6, 2.0), 61.5)
    pplay(mus, 61.52, nm("A5"), 0.4, 2.6)
    for i, m in enumerate(("D6", "A5", "F#5", "D6")):
        place(mus, celesta(nm(m), 0.22), 61.6 + i * 0.4, pan=0.3)

    # ---------------- Scene 6: hopeful, adventurous (96 bpm)
    bt = 0.625
    s6 = [(63.13, 2.5, "D2", "D3 A3 F#4 A4"), (65.63, 2.5, "C#2", "A2 E3 C#4 A4"), (68.13, 2.5, "B1", "B2 F#3 D4 F#4"),
          (70.63, 2.4, "G1", "G2 D3 B3 G4"), (73.03, 1.6, "G1", "G2 D3 B3 D4"), (74.63, 1.3, "A1", "A2 E3 A3 D4"),
          (75.93, 1.83, "A1", "A2 E3 A3 C#4 E4")]
    for k, (t0, d, b, st) in enumerate(s6):
        r = nm(b) + 12
        pull = k == 4
        strings_chord(mus, t0, d, chord(st), 0.30 if pull else 0.36 + 0.025 * k, att=0.5 if not pull else 1.0, rel=0.8,
                      bright=2600)
        pplay(mus, t0, r, 0.42, d)
        if not pull:
            j = 0
            while j * bt / 2 < d - 1e-3:
                place(mus, stacc(r + [0, 7, 12, 7][j % 4], 0.26 + 0.05 * (j % 4 == 0)), t0 + j * bt / 2, pan=-0.25)
                if k >= 2:
                    place(mus, stacc(r + 24 + [0, 4, 7, 4][j % 4] - (1 if k == 1 else 0), 0.14), t0 + j * bt / 2, pan=0.3)
                j += 1
            # light percussion (kick + shaker) once the rover appears
            if k >= 1:
                j = 0
                while j * bt < d - 1e-3:
                    if j % 2 == 0 or k >= 5:
                        place(mus, sub_drop(90, 45, 0.45, 0.35), t0 + j * bt)
                    j += 1
                if k >= 2:
                    j = 0
                    while j * bt / 4 < d - 1e-3:
                        kk = int(0.07 * SR)
                        sh = hp(noise(kk), 6000) * np.exp(-np.arange(kk) / (0.018 * SR)) * (0.05 if j % 2 else 0.08)
                        place(mus, sh, t0 + j * bt / 4, pan=0.4)
                        j += 1
        else:
            pplay(mus, t0 + 0.3, nm("B4"), 0.32, 1.2)
            pplay(mus, t0 + 0.9, nm("D5"), 0.32, 0.9)
    for i, (m, t0) in enumerate((("A5", 65.63), ("C#6", 66.25), ("E6", 66.88), ("F#6", 68.13), ("D6", 68.75), ("A5", 69.38),
                                 ("G5", 70.63), ("B5", 71.25), ("D6", 71.88), ("E6", 75.0), ("C#6", 75.63), ("A5", 76.25))):
        place(mus, celesta(nm(m), 0.24), t0, pan=0.35 * math.sin(i * 1.7))
    horn_chord(mus, 70.63, 2.3, chord("G3 B3 D4"), 0.4, att=0.6, rel=0.6)
    horn_chord(mus, 74.63, 3.0, chord("A3 D4 E4"), 0.42, att=1.0, rel=0.4)
    place(mus, timp(nm("A1"), 0.55, 1.2), 74.63)
    place(mus, reverse_swell(1.0, 0.35), 77.76 - 1.0)

    # ---------------- Scene 7: the invitation -> crescendo -> button
    s7 = [(77.76, 1.85, "G1", "G2 D3 B3 D4 G4", 0.34), (79.6, 1.0, "A1", "A2 E3 A3 D4 E4", 0.38),
          (80.6, 0.6, "A1", "A2 E3 A3 C#4 E4", 0.40), (81.2, 1.15, "B1", "B2 F#3 B3 D4 F#4", 0.48),
          (82.35, 1.15, "G1", "G2 D3 G3 B3 D4 G4", 0.56), (83.5, 0.8, "F#1", "F#2 D3 A3 D4 F#4 A4", 0.64),
          (84.3, 0.7, "A1", "A2 E3 A3 C#4 E4 A4", 0.72)]
    for k, (t0, d, b, st, v) in enumerate(s7):
        r = nm(b) + 12
        strings_chord(mus, t0, d, chord(st), v, att=0.5 if k < 3 else 0.12, rel=0.5 if k < 6 else 0.25, bright=2600 + 250 * k)
        pplay(mus, t0, r, 0.45 + 0.04 * k, d)
        pplay(mus, t0, r + 12, 0.35 + 0.04 * k, d)
        if k >= 3:
            horn_chord(mus, t0, d, chord(st)[1:4], 0.4 + 0.08 * (k - 3), att=0.15, rel=0.2)
            j = 0
            while j * 0.1875 < d - 1e-3:
                place(mus, stacc(r + [0, 12, 7, 12][j % 4], 0.3 + 0.05 * k), t0 + j * 0.1875, pan=-0.2)
                j += 1
            place(mus, timp(r - 12, 0.5 + 0.08 * k, 1.0), t0)
    pplay(mus, 78.0, nm("B4"), 0.36, 0.8)
    pplay(mus, 78.8, nm("D5"), 0.36, 0.9)
    pplay(mus, 79.6, nm("E5"), 0.4, 1.0)
    pplay(mus, 80.6, nm("C#5"), 0.4, 0.6)
    timp_roll(mus, 84.3, 84.98, nm("A1"), 0.3, 1.0)
    place(mus, riser(2.0, 0.45), 85.0 - 2.0)
    place(mus, reverse_swell(0.8, 0.5), 85.0 - 0.8)
    # the breath: sudden pull-back as the title card arrives
    place(mus, strings_note(nm("D5"), 3.5, 0.26, att=0.05, rel=1.0, bright=3400), 85.0)
    place(mus, strings_note(nm("A5"), 3.5, 0.2, att=0.05, rel=1.0, bright=3400), 85.0)
    place(mus, strings_note(nm("D3"), 3.5, 0.2, att=0.3, rel=1.0, bright=1500), 85.0)
    for m, t0, v in (("F#5", 85.4, 0.4), ("E5", 86.05, 0.36), ("D5", 86.7, 0.36), ("A4", 87.3, 0.3), ("C#5", 87.95, 0.32)):
        pplay(mus, t0, nm(m), v, 0.9)
    for i, m in enumerate(("D6", "F#6", "A6", "D7")):
        place(mus, celesta(nm(m), 0.18), 86.25 + i * 0.22, pan=-0.3 + 0.2 * i)
    place(mus, riser(1.3, 0.22, 600, 7000), 88.7 - 1.3)
    # final button: full D major
    fh = 88.7
    place(mus, impact(1.0, 3.0), fh)
    place(mus, crash(0.6), fh)
    place(mus, timp(nm("D2"), 1.0, 2.0), fh)
    strings_chord(mus, fh, 1.3, chord("D2 A2 D3 F#3 A3 D4 F#4 A4 D5"), 0.7, att=0.03, rel=2.0, bright=3600)
    horn_chord(mus, fh, 1.3, chord("D3 A3 D4 F#4"), 0.75, att=0.03, rel=1.5)
    for m in ("D2", "A2", "D3", "F#4", "A4", "D5"):
        pplay(mus, fh, nm(m), 0.6, 2.0)
    return mus


# ============================================================================ SOUND DESIGN
def radio_static(dur, vel=0.3):
    n = int(dur * SR)
    x = bp(noise(n, 2), 500, 5500) * 0.5
    k = rng.random((2, n)) < 0.0009                    # crackle
    cr = bp((k * rng.standard_normal((2, n))).astype(np.float32), 800, 6000) * 6
    g = lp(np.abs(noise(n)), 6)                         # flutter
    g = 0.6 + 0.8 * g / (g.max() + 1e-9)
    return (x + cr) * g * vel


def ping(f=1240, vel=0.3):
    n = int(1.6 * SR)
    t = tv(n)
    x = np.sin(2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * f * 1.5 * t) * np.exp(-t / 0.1)) * np.exp(-t / 0.22)
    out = np.zeros((2, n), np.float32)
    for i, (d, g) in enumerate(((0, 1.0), (0.27, 0.45), (0.54, 0.22), (0.81, 0.1))):
        a = int(d * SR)
        out[i % 2, a:] += (x[:n - a] * g).astype(np.float32)
    return out * vel


def servo(dur, f0=180.0, f1=260.0, vel=0.25, grit=0.4):
    n = int(dur * SR)
    t = tv(n)
    k = smoothstep(t / dur)
    f = f0 + (f1 - f0) * k
    ph = np.cumsum(f) / SR
    x = (2 * (ph % 1) - 1) * 0.6 + np.sin(2 * np.pi * ph * 2.01) * 0.4 + np.sin(2 * np.pi * ph * 3.97) * 0.2
    x = bp(x.astype(np.float32), 120, 3500)
    gear = 1 + grit * np.sign(np.sin(2 * np.pi * np.cumsum(f * 0.13) / SR)) * 0.5
    x = x * gear.astype(np.float32)
    x += bp(noise(n), 2000, 8000) * 0.08
    e = shape_env(n, [(0, 0), (0.05, 1), (dur - 0.06, 1), (dur, 0)])
    out = x * e
    for tt in (0.0, dur - 0.02):                         # start/stop clicks
        kk = int(0.02 * SR)
        c = bp(noise(kk), 1500, 7000) * np.exp(-np.arange(kk) / (0.003 * SR)) * 0.7
        a = int(tt * SR)
        out[a:a + kk] += c[:len(out[a:a + kk])]
    return out * vel


def tick(vel=0.12):
    kk = int(0.025 * SR)
    t = tv(kk)
    f = rng.uniform(2200, 4200)
    return (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.006) * vel).astype(np.float32)


def thud(vel=1.0):
    x = impact(vel * 0.8, 1.6, 0.0)
    k = int(1.2 * SR)
    dust = bp(noise(k, 2), 300, 4000) * np.exp(-np.arange(k) / (0.35 * SR)) * 0.25
    x[:, :k] += dust
    return x


def sound_design(mus_unused=None):
    sfx = buf()
    amb = buf()
    S = SC
    # ---- ambience beds
    n = N
    bed = lp(brown(n, 2), 140) * 0.5
    lfo = 0.75 + 0.25 * np.sin(2 * np.pi * tv(n) / 9.0)
    bed *= lfo.astype(np.float32)
    lvl = np.interp(tv(n), [0, 1.5, 7, 9, S[3], S[3] + 0.1, S[4], S[4] + 1, S[5], S[6], S[6] + 1, S[7], 89.0, 90],
                    [0, 0.9, 0.9, 0.5, 0.5, 0.15, 0.15, 0.45, 0.5, 0.45, 0.3, 0.45, 0.4, 0]).astype(np.float32)
    amb += bed * lvl
    # Mars wind (Scene 6)
    wd = 77.9 - 64.5
    wind = sweep_noise(wd, 260, 900, bw=0.45, shape=0.5 + 0.5 * np.sin(np.linspace(0, 9, 60)))
    we = shape_env(int(wd * SR), [(0, 0), (1.0, 0.35), (8.5, 0.35), (9.0, 1.0), (10.5, 1.0), (11.0, 0.35), (12.5, 0.3), (wd, 0)])
    place(amb, wind * we, 64.5, 0.28)

    # ---- Scene 1: radio static, transmission pings, tuning sweep
    place(sfx, sweep_noise(0.9, 4000, 600, bw=0.35) * shape_env(int(0.9 * SR), [(0, 0), (0.1, 1), (0.9, 0)]), 0.12, 0.22)
    st = radio_static(7.5, 1.0)
    se = np.full(st.shape[1], 0.10, np.float32)
    for lid in ("s1_01", "s1_02", "s1_03", "s1_04"):
        a, b = int((T[lid] - 0.25) * SR), int((E[lid] + 0.25) * SR)
        se[a:b] = np.maximum(se[a:b], shape_env(b - a, [(0, 0.1), (0.15, 0.32), ((b - a) / SR - 0.15, 0.32), ((b - a) / SR, 0.1)]))
    se *= shape_env(len(se), [(0, 0), (0.3, 1), (5.8, 1), (7.4, 0)])
    place(sfx, st * se, 0.0, 0.55)
    for t0 in (0.55, 1.6, 3.2, 4.8):
        place(sfx, ping(1240, 0.16 if t0 > 1 else 0.2), t0)
    # ---- Scene 2: dust, arm twitch, camera turning towards us
    place(sfx, servo(0.7, 150, 175, 0.07, 0.6), 9.6)
    place(sfx, servo(1.25, 210, 300, 0.12, 0.35), 12.12, pan=0.15)
    # ---- Scene 3: flash whoosh, launch, cruise, descent, touchdown
    place(sfx, whoosh(1.0, 0.35, 300, 5000, 0.85), S[3] - 0.85)
    ig = S[3] + 0.35
    rd = 6.4
    nr = int(rd * SR)
    rumble = lp(brown(nr, 2), 260) * 1.2 + bp(noise(nr, 2), 180, 1400) * 0.35
    kk = rng.random((2, nr)) < 0.004
    crk = bp((kk * rng.standard_normal((2, nr))).astype(np.float32), 600, 4000) * 3.0
    re_ = shape_env(nr, [(0, 0), (0.12, 0.7), (0.6, 1.0), (3.6, 1.0), (rd - 1.2, 0.35), (rd, 0)])
    place(sfx, (rumble + crk) * re_, ig, 0.75)
    place(sfx, sub_drop(48, 26, 3.0, 0.7), ig)
    place(sfx, whoosh(1.6, 0.22, 200, 1800, 0.5), 20.05 - 0.9)                 # into cruise
    place(sfx, whoosh(1.0, 0.18, 400, 3000, 0.6), 24.25 - 0.6)                 # into descent
    dd = 28.76 + 0.8 - 24.1
    nd = int(dd * SR)
    thr = bp(noise(nd, 2), 900, 4200) * 0.35 + lp(brown(nd, 2), 200) * 0.6
    place(sfx, thr * shape_env(nd, [(0, 0), (0.4, 0.5), (dd - 1.2, 0.8), (dd - 0.8, 0.9), (dd - 0.05, 0.6), (dd, 0)]), 24.1, 0.35)
    td = S[3] + 12.95
    place(sfx, thud(0.9), td)
    place(sfx, thud(0.45), td + 0.75)
    # ---- Scene 4: scoop servos, soil, lens zoom, data ticks
    place(sfx, servo(0.9, 160, 230, 0.16, 0.6), S[4] + 1.4, pan=-0.2)
    kk = int(0.8 * SR)
    place(sfx, bp(noise(kk, 2), 400, 3500) * shape_env(kk, [(0, 0), (0.1, 0.4), (0.5, 0.2), (0.8, 0)]), S[4] + 2.2, 0.2)
    place(sfx, servo(0.8, 230, 170, 0.14, 0.6), S[4] + 2.9, pan=-0.2)
    place(sfx, servo(1.25, 320, 620, 0.10, 0.15), 36.5, pan=0.1)              # lens zoom whirr
    place(sfx, whoosh(0.7, 0.18, 1500, 7000, 0.8), 37.75 - 0.55)
    t = 37.9
    while t < 40.6:
        x = (t - 37.9) / 2.7
        place(sfx, tick(0.11), t, pan=rng.uniform(-0.5, 0.5))
        t += 0.028 + 0.22 * x ** 2.2
    place(sfx, whoosh(1.0, 0.16, 300, 2500, 0.6), 40.75 - 0.6)
    # ---- Scene 5: time passing, approach, tools, Surveyor's POV
    place(sfx, whoosh(1.6, 0.2, 150, 1200, 0.7), S[5] - 1.0)
    place(sfx, whoosh(1.2, 0.14, 250, 2000, 0.6), 47.55 - 0.7)
    for tt in (55.35, 56.1):
        kk = int(0.25 * SR)
        tk = (np.sin(2 * np.pi * 2900 * tv(kk)) * 0.4 + np.sin(2 * np.pi * 4700 * tv(kk)) * 0.25) * np.exp(-tv(kk) / 0.05)
        place(sfx, tk.astype(np.float32), tt, 0.10, pan=0.2)
    kk = int(2.0 * SR)
    hum = sum(np.sin(2 * np.pi * 60 * h * tv(kk)) / h for h in (1, 2, 3, 5)) * 0.2 + bp(noise(kk), 2000, 7000) * 0.15
    place(sfx, (hum * shape_env(kk, [(0, 0), (0.3, 1), (1.6, 1), (2.0, 0)])).astype(np.float32), T["s5_06"] - 0.2, 0.18)
    # ---- Scene 6: big Moon->Mars whoosh, wheels, mast/arm servo, storm
    place(sfx, whoosh(2.2, 0.4, 120, 2500, 0.55), S[6] - 1.2)
    wd = 70.6 - 66.0
    nw = int(wd * SR)
    crunch = bp(noise(nw, 2), 200, 2500) * (0.5 + 0.5 * np.sin(2 * np.pi * 2.6 * tv(nw)) ** 2)
    kk = rng.random((2, nw)) < 0.002
    crunch += bp((kk * rng.standard_normal((2, nw))).astype(np.float32), 500, 5000) * 2.0
    place(sfx, crunch * shape_env(nw, [(0, 0), (0.5, 1), (wd - 0.6, 1), (wd, 0)]), 66.0, 0.07)
    place(sfx, servo(1.5, 190, 250, 0.12, 0.5), T["s6_03"] - 0.75, pan=-0.15)
    place(sfx, whoosh(1.4, 0.2, 200, 1500, 0.6), T["s6_04"] - 0.9)
    # ---- Scene 7: arrival whoosh, marker blips, final shimmer
    place(sfx, whoosh(1.8, 0.28, 150, 2500, 0.6), S[7] - 1.1)
    for tt in (S[7] + 0.5, S[7] + 0.9):
        place(sfx, ping(1660, 0.07), tt)
    place(sfx, whoosh(1.2, 0.1, 2000, 9000, 0.7), T["s7_02"] - 0.2)
    return sfx, amb


# ============================================================================ VOICE
def load_line(lid):
    d, sr = sf.read(os.path.join(ROOT, "audio", "voice", lid + ".wav"), dtype="float32")
    if d.ndim > 1:
        d = d.mean(1)
    if sr != SR:
        g = math.gcd(sr, SR)
        d = signal.resample_poly(d, SR // g, sr // g).astype(np.float32)
    return d


def radio(x):
    y = bp(x, 320, 3300, 3)
    y = np.tanh(y * 3.5) / np.tanh(3.5)
    return y


def voice_track():
    vo = buf()
    for lid, scene, *_ in LINES:
        d = load_line(lid)
        d = d / (np.sqrt(np.mean(d[np.abs(d) > 0.02] ** 2)) + 1e-9) * 0.1          # per-line level match
        d = hp(d, 75, 2)
        d = d + bp(d, 2500, 6000, 1) * 0.12                                       # presence
        if scene == 1:
            r = radio(d) * 0.9
            # the signal clears line by line: more radio at first, warmer by the last question
            k = {"s1_01": 0.92, "s1_02": 0.85, "s1_03": 0.72, "s1_04": 0.6}[lid]
            d = r * k + d * (1 - k) * 0.9
        place(vo, d, T[lid])
    return vo


# ============================================================================ FX / MIX
def make_ir(rt60=2.6, pre=0.018, damp=3500.0):
    n = int(rt60 * 1.2 * SR)
    t = tv(n)
    dec = 10 ** (-3 * t / rt60)
    ir = rng.standard_normal((2, n)) * dec
    lpir = lp(ir.astype(np.float32), damp)
    w = np.clip(t / (rt60 * 0.4), 0, 1)
    ir = (ir * (1 - w) + lpir * w).astype(np.float32)
    ir[:, :int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))
    ir = np.pad(ir, ((0, 0), (int(pre * SR), 0)))
    return ir / np.sqrt((ir ** 2).sum(axis=1, keepdims=True))


def reverb(x, ir, wet):
    y = np.stack([signal.fftconvolve(x[c], ir[c])[:x.shape[1]] for c in range(2)]).astype(np.float32)
    return x + y * wet


def follower(x, att=0.03, rel=0.35):
    """Envelope follower on |x| (mono sum)."""
    a = np.abs(x).mean(0)
    a = lp(a, 25, 1)
    # asymmetric smoothing via max filter + release lowpass
    k = int(att * SR)
    a = np.maximum.accumulate if False else a
    from scipy.ndimage import maximum_filter1d
    a = maximum_filter1d(a, int(0.12 * SR))
    a = lp(a, 1 / (2 * math.pi * rel) * 2, 1)
    return a


def rms_db(x):
    return 20 * math.log10(math.sqrt(float(np.mean(x ** 2))) + 1e-12)


def main():
    print("score...", flush=True)
    mus = score()
    print("sound design...", flush=True)
    sfx, amb = sound_design()
    print("voice...", flush=True)
    vo = voice_track()

    big = make_ir(2.8, 0.025, 3200)
    mid = make_ir(1.6, 0.012, 4500)
    small = make_ir(0.9, 0.008, 5000)
    mus = reverb(hp(mus, 30), big, 0.42)
    sfx = reverb(sfx, mid, 0.25)
    vo_wet = reverb(vo, small, 0.10)
    # Scene-1 voice: a touch of distant echo
    s1a, s1b = 0, int(SC[2] * SR)
    echo = np.zeros_like(vo_wet)
    for dly, g in ((0.21, 0.28), (0.42, 0.12)):
        k = int(dly * SR)
        echo[:, k:s1b + k] += vo[:, :s1b] * g
    vo_wet[:, :s1b + int(0.5 * SR)] += echo[:, :s1b + int(0.5 * SR)]
    vo_wet = reverb(vo_wet, big, 0.0) if False else vo_wet

    # ---- calibration
    act = np.abs(vo).mean(0) > 0.01
    v_db = rms_db(vo_wet[:, act])
    vo_wet *= 10 ** ((-19.0 - v_db) / 20)
    mus *= 10 ** ((-25.5 - rms_db(mus)) / 20)
    sfx *= 10 ** ((-29.0 - rms_db(sfx)) / 20)
    amb *= 10 ** ((-38.0 - rms_db(amb)) / 20)

    # ---- sidechain ducking under the voice
    env = follower(vo_wet)
    env = np.clip(env / (np.percentile(env[act], 60) + 1e-9), 0, 1)
    duck_m = (1 - 0.5 * env).astype(np.float32)     # up to ~ -6 dB
    duck_s = (1 - 0.3 * env).astype(np.float32)
    mus *= duck_m
    sfx *= duck_s

    # ---- master
    fade = np.ones(N, np.float32)
    k = int(0.75 * SR)
    fade[-k:] = np.linspace(1, 0, k) ** 1.5
    mix = (mus + sfx + amb + vo_wet) * fade
    mix = hp(mix, 22, 2)
    pk = np.abs(mix).max()
    mix = np.tanh(mix / pk * 1.15) / np.tanh(1.15) * 0.89       # gentle soft-clip bus
    for nm_, x in (("music", mus * fade), ("sfx", sfx * fade), ("ambience", amb * fade), ("voice", vo_wet * fade)):
        sf.write(os.path.join(OUT, nm_ + ".wav"), x.T, SR, subtype="FLOAT")
    sf.write(os.path.join(ROOT, "audio", "mix_premaster.wav"), mix.T, SR, subtype="FLOAT")
    # loudness-over-time report for QA
    blk = SR // 2
    print("t     voice   music   sfx    mix   (RMS dBFS, 0.5 s blocks; every 2 s)")
    for i in range(0, N // blk, 4):
        s = slice(i * blk, (i + 1) * blk)
        print(f"{i * 0.5:5.1f} " + " ".join(f"{rms_db(x[:, s]):6.1f}" for x in (vo_wet, mus, sfx, mix)))
    print("done")


if __name__ == "__main__":
    main()
