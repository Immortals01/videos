"""Generate every narration line with Kokoro-82M (Apache-2.0, runs locally on CPU).
Writes audio/voice/<id>.wav (24 kHz mono) and audio/voice/durations.json."""
import json, sys, os
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
sys.path.insert(0, os.path.dirname(__file__))
from script_lines import LINES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "audio", "voice")
os.makedirs(OUT, exist_ok=True)
VOICE = os.environ.get("VOICE", "af_heart")
SPEED = float(os.environ.get("SPEED", "0.98"))
only = set(sys.argv[1:])

k = Kokoro(os.path.join(ROOT, "models/kokoro-v1.0.onnx"), os.path.join(ROOT, "models/voices-v1.0.bin"))
dur = {}
dpath = os.path.join(OUT, "durations.json")
if os.path.exists(dpath):
    dur = json.load(open(dpath))
for lid, scene, _, text, _ in LINES:
    if only and lid not in only:
        continue
    # A slightly slower, more intimate read for the emotional lines.
    sp = SPEED
    if lid in ("s1_01", "s1_02", "s2_01", "s5_02", "s5_06", "s7_04", "s7_05"):
        sp = SPEED * 0.94
    elif lid in ("s3_01", "s3_02", "s3_03", "s3_04", "s4_03", "s6_02", "s6_05", "s7_03", "s2_02", "s6_01"):
        sp = SPEED * 1.12
    samples, sr = k.create(text, voice=VOICE, speed=sp, lang="en-us")
    samples = np.asarray(samples, dtype=np.float32)
    # trim leading/trailing silence
    thr = 0.01 * np.max(np.abs(samples))
    nz = np.where(np.abs(samples) > thr)[0]
    a, b = max(0, nz[0] - int(0.03 * sr)), min(len(samples), nz[-1] + int(0.08 * sr))
    samples = samples[a:b]
    sf.write(os.path.join(OUT, f"{lid}.wav"), samples, sr)
    dur[lid] = round(len(samples) / sr, 3)
    print(lid, dur[lid], text[:60])
json.dump(dur, open(dpath, "w"), indent=1)
print("TOTAL speech", round(sum(dur.values()), 2))
