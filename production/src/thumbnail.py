"""Video thumbnail: Surveyor 3 low-angle plate + film title, in the film's fonts and grade.
Writes deliverables/Thumbnail_1920x1080.png and deliverables/Thumbnail_1280x720.jpg."""
import os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import fx
from fx import W, H

ROOT = fx.ROOT
OUT = os.path.join(os.path.dirname(ROOT), "deliverables")

# Lander shifted right so the left column is open space for the title without touching the boom/scoop.
src = cv2.imread(os.path.join(ROOT, "plates", "p_lowangle.jpg"))[:, :, ::-1].astype(np.float32) / 255
S, OFF = 0.84, 600
sw, sh = int(round(W * S)), int(round(H * S))
src = cv2.resize(src, (sw, sh), interpolation=cv2.INTER_LANCZOS4)
img = np.zeros((H, W, 3), np.float32)
img[H - sh:, OFF:OFF + min(sw, W - OFF)] = src[:, :W - OFF]
# feather the plate's left edge into the starfield and darken under text
edge = np.clip((fx._XX - OFF) / 360.0, 0, 1) ** 1.35
stars = np.zeros_like(img)
fx.Starfield(2600, seed=21).render(gain=0.55, canvas=stars)
img = img * edge[..., None] + stars * (1 - edge[..., None])
img = fx.grade(img, "lunar")
scrim = np.clip((fx._XX - 560.0) / 320.0, 0, 1) ** 1.2
img *= (0.32 + 0.68 * scrim)[..., None]
fx.glow(img, 340, 470, 480, (1.0, 0.75, 0.4), 0.035)

gold, cream = (1.0, 0.8, 0.45), (1.0, 0.96, 0.88)
fx.text(img, "ABANDONED,", 88, 290, 92, 1.0, "serif", 600, 0.04, cream, anchor="lm", glow_k=0.3)
fx.text(img, "BUT NOT", 88, 394, 92, 1.0, "serif", 600, 0.04, cream, anchor="lm", glow_k=0.3)
fx.text(img, "FORGOTTEN", 88, 498, 92, 1.0, "serif", 600, 0.04, cream, anchor="lm", glow_k=0.3)
fx.hline(img, 96, 584, 440, 0.85, gold, 3)
fx.text(img, "SURVEYOR 3  ·  OPPORTUNITY", 92, 632, 26, 0.95, "mont", 600, 0.20, gold, anchor="lm")
fx.text(img, "Every machine has a story.", 92, 690, 36, 0.92, "serif", 500, 0.03, (0.9, 0.93, 1.0), anchor="lm")
fx.text(img, "NASA SPACE APPS CHALLENGE", 92, H - 90, 22, 0.7, "mont", 500, 0.30, (1, 1, 1), anchor="lm")

img = fx.finish(img, 0.0, bloom=0.2, vignette=0.25, grain=0.012, letterbox=False)
u8 = fx.to_u8(img)[:, :, ::-1]
os.makedirs(OUT, exist_ok=True)
cv2.imwrite(os.path.join(OUT, "Thumbnail_1920x1080.png"), u8)
cv2.imwrite(os.path.join(OUT, "Thumbnail_1280x720.jpg"), cv2.resize(u8, (1280, 720), interpolation=cv2.INTER_AREA),
            [cv2.IMWRITE_JPEG_QUALITY, 92])
print("ok")
