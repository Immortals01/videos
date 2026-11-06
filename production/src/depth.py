"""Depth maps for every plate with Depth-Anything-V2-small (ONNX, CPU).
Writes plates/depth/<name>.npy  (float16 disparity, 0 = far, 1 = near, same size as plate)."""
import glob, os, sys
import cv2, numpy as np, onnxruntime as ort

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "plates", "depth")
os.makedirs(OUT, exist_ok=True)
sess = ort.InferenceSession(os.path.join(ROOT, "models/depth_small.onnx"))
MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)


def depth(img_bgr):
    h, w = img_bgr.shape[:2]
    s = 518 / min(h, w)
    nh, nw = int(round(h * s / 14)) * 14, int(round(w * s / 14)) * 14
    x = cv2.resize(img_bgr, (nw, nh), interpolation=cv2.INTER_CUBIC)[:, :, ::-1].astype(np.float32) / 255
    x = ((x - MEAN) / STD).transpose(2, 0, 1)[None]
    d = sess.run(None, {"pixel_values": x})[0][0]
    d = cv2.resize(d, (w, h), interpolation=cv2.INTER_CUBIC)
    lo, hi = np.percentile(d, 1), np.percentile(d, 99.5)
    d = np.clip((d - lo) / (hi - lo + 1e-6), 0, 1)
    # edge-aware smoothing so parallax stretches softly instead of tearing
    d = cv2.bilateralFilter(d.astype(np.float32), 9, 0.1, 7)
    d = cv2.GaussianBlur(d, (0, 0), 2.0)
    return d.astype(np.float16)


files = sys.argv[1:] or sorted(glob.glob(os.path.join(ROOT, "plates", "*.jpg")))
for f in files:
    name = os.path.splitext(os.path.basename(f))[0]
    out = os.path.join(OUT, name + ".npy")
    if os.path.exists(out) and not sys.argv[1:]:
        continue
    d = depth(cv2.imread(f))
    np.save(out, d)
    cv2.imwrite(os.path.join(OUT, name + ".png"), (d.astype(np.float32) * 255).astype(np.uint8))
    print("depth", name, d.shape)
