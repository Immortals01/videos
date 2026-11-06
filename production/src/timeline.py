"""Master timeline. Places every narration line on the 90.000 s timeline and derives
scene boundaries from the dialogue so picture, voice and music stay locked.

Usage: from timeline import T, SCENES, line_times
  T['s2_03']      -> start time (s) of that line
  E['s2_03']      -> end time (s)
  SCENES[k]       -> (start, end) of scene k (1..7)
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from script_lines import LINES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 24
DURATION = 90.0
NFRAMES = int(DURATION * FPS)  # 2160

DUR = json.load(open(os.path.join(ROOT, "audio/voice/durations.json")))

# Pause BEFORE each line (seconds). Scene openers get longer pauses so the picture
# can breathe through the transition; the emotional Apollo 12 lines get room too.
PRE = {
    "s1_01": 1.45, "s1_02": 0.75, "s1_03": 0.70, "s1_04": 0.45,
    "s2_01": 1.55, "s2_02": 0.55, "s2_03": 0.55, "s2_04": 0.35,
    "s3_01": 1.05, "s3_02": 0.35, "s3_03": 0.35, "s3_04": 0.40,
    "s4_01": 0.55, "s4_02": 0.35, "s4_03": 0.40,
    "s5_01": 1.00, "s5_02": 0.65, "s5_03": 0.55, "s5_04": 0.40, "s5_05": 0.55, "s5_06": 0.75,
    "s6_01": 1.00, "s6_02": 0.30, "s6_03": 0.40, "s6_04": 0.30, "s6_05": 0.30,
    "s7_01": 0.85, "s7_02": 0.40, "s7_03": 0.35, "s7_04": 0.45, "s7_05": 0.35,
}
TAIL = 1.35          # title holds after the final word
FIXED = {"s1_01"}    # the hook timing is not scaled

speech = sum(DUR[l[0]] for l in LINES)
flex = sum(v for k, v in PRE.items() if k not in FIXED)
fixed = sum(PRE[k] for k in FIXED)
avail = DURATION - TAIL - speech - fixed
scale = avail / flex
T, E = {}, {}
t = 0.0
for lid, scene, *_ in LINES:
    t += PRE[lid] * (1.0 if lid in FIXED else scale)
    T[lid] = round(t, 3)
    t += DUR[lid]
    E[lid] = round(t, 3)

LEAD = {2: 1.05, 3: 0.85, 4: 0.45, 5: 0.80, 6: 0.85, 7: 0.70}
first = {}
for lid, scene, *_ in LINES:
    first.setdefault(scene, lid)
starts = {1: 0.0}
for k in range(2, 8):
    starts[k] = round(T[first[k]] - LEAD[k] * min(scale, 1.0), 3)
SCENES = {k: (starts[k], starts[k + 1] if k < 7 else DURATION) for k in range(1, 8)}

def frame(t):
    return int(round(t * FPS))

if __name__ == "__main__":
    print(f"speech={speech:.2f}s gap-scale={scale:.3f}")
    for k, (a, b) in SCENES.items():
        print(f"Scene {k}: {a:6.2f} - {b:6.2f}  ({b-a:5.2f}s)")
    for lid, scene, _, text, _ in LINES:
        print(f"  {lid} {T[lid]:6.2f}-{E[lid]:6.2f}  {text[:70]}")
