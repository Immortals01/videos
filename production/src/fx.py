"""Core image engine for the film: 2.5D depth-parallax cameras, procedural spheres and
starfields, particles, light FX, typography, grading and finishing.
All images are float32 RGB in [0,1+] at 1920x1080 unless stated."""
import functools, math, os
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1920, 1080
LB = 104                      # 2.2:1 letterbox bars (subtitles live in the lower bar)
FPS = 24
cv2.setNumThreads(1)

# ----------------------------------------------------------------------------- helpers
def clamp01(x):
    return np.clip(x, 0.0, 1.0)

def sat(x):
    return max(0.0, min(1.0, x))

def smooth(x):
    x = sat(x)
    return x * x * (3 - 2 * x)

def ease(x):                  # gentle in-out (sine)
    x = sat(x)
    return 0.5 - 0.5 * math.cos(math.pi * x)

def ease_out(x):
    x = sat(x)
    return 1 - (1 - x) ** 3

def ease_in(x):
    x = sat(x)
    return x ** 3

def lerp(a, b, t):
    return a + (b - a) * t

def win(t, a, b, fi=0.3, fo=0.3):
    """1 inside [a,b] with smooth fades of fi/fo seconds."""
    if t < a or t > b:
        return 0.0
    return min(smooth((t - a) / fi) if fi > 0 else 1.0, smooth((b - t) / fo) if fo > 0 else 1.0)

_YY, _XX = np.mgrid[0:H, 0:W].astype(np.float32)
GX = _XX - W / 2
GY = _YY - H / 2

# ----------------------------------------------------------------------------- plates
class Plate:
    """A still plate + depth map rendered through a virtual camera with real parallax."""

    def __init__(self, name, overscan=1.2, crop=None):
        path = os.path.join(ROOT, "plates", name + ".jpg")
        img = cv2.imread(path)
        if img is None:
            raise FileNotFoundError(path)
        dpath = os.path.join(ROOT, "plates", "depth", name + ".npy")
        d = np.load(dpath).astype(np.float32) if os.path.exists(dpath) else np.full(img.shape[:2], 0.5, np.float32)
        if crop:  # (x0,y0,x1,y1) normalized
            h, w = img.shape[:2]
            x0, y0, x1, y1 = int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)
            img, d = img[y0:y1, x0:x1], d[y0:y1, x0:x1]
        h, w = img.shape[:2]
        s = max(W * overscan / w, H * overscan / h)
        nw, nh = int(round(w * s)), int(round(h * s))
        img = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
        bl = cv2.GaussianBlur(img, (0, 0), 1.3)
        img = cv2.addWeighted(img, 1.45, bl, -0.45, 0)        # recover upscale softness
        self.img = img[:, :, ::-1].copy()                        # uint8 RGB
        self.d = cv2.resize(d, (nw, nh), interpolation=cv2.INTER_LINEAR)
        self.w, self.h = nw, nh
        self._blur = None

    @property
    def blurred(self):
        if self._blur is None:
            self._blur = cv2.GaussianBlur(self.img, (0, 0), 7)
        return self._blur

    def render(self, zoom=1.0, cx=0.5, cy=0.5, px=0.0, py=0.0, dolly=0.0, d0=0.5, roll=0.0,
               focus=None, dof=0.0, warps=(), shake=(0.0, 0.0)):
        """zoom: 1 => one plate pixel per screen pixel. cx,cy: view centre (normalized plate coords).
        px,py: parallax in plate pixels per unit disparity (camera translation).
        dolly: extra depth-dependent magnification (positive = dolly-in feel)."""
        X, Y = GX, GY
        if roll:
            c, s = math.cos(roll), math.sin(roll)
            X, Y = c * GX - s * GY, s * GX + c * GY
        Cx, Cy = cx * self.w + shake[0], cy * self.h + shake[1]
        dd = np.full_like(GX, d0) if (dolly or px or py) else None
        mx = my = None
        for _ in range(2 if dd is not None else 1):
            if dd is None:
                z = zoom
                mx, my = Cx + X / z, Cy + Y / z
                break
            z = zoom * (1.0 + dolly * (dd - d0))
            mx = Cx + X / z + px * (dd - d0)
            my = Cy + Y / z + py * (dd - d0)
            dd = cv2.remap(self.d, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        if dd is not None:
            z = zoom * (1.0 + dolly * (dd - d0))
            mx = Cx + X / z + px * (dd - d0)
            my = Cy + Y / z + py * (dd - d0)
        for (wx, wy, rx, ry, dx, dy) in warps:   # local mechanical motion (plate-normalized)
            ex = (mx - wx * self.w) / (rx * self.w)
            ey = (my - wy * self.h) / (ry * self.h)
            m = np.clip(1.0 - (ex * ex + ey * ey), 0, 1) ** 2
            mx = mx - m * dx * self.w
            my = my - m * dy * self.h
        out = cv2.remap(self.img, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT).astype(np.float32) / 255
        if dof > 0 and focus is not None:
            if dd is None:
                dd = cv2.remap(self.d, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            b = cv2.remap(self.blurred, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32) / 255
            wgt = np.clip(np.abs(dd - focus) * dof, 0, 1)[..., None]
            out = out * (1 - wgt) + b * wgt
        return out


@functools.lru_cache(maxsize=5)
def plate(name, overscan=1.2, crop=None):
    return Plate(name, overscan, crop)

# ----------------------------------------------------------------------------- textures / spheres
@functools.lru_cache(maxsize=4)
def texture(name):
    p = os.path.join(ROOT, "textures", name)
    im = np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255
    return im


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], np.float32)


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], np.float32)


def sphere(canvas, tex, cx, cy, r, lon=0.0, tilt=0.0, light=(-0.55, 0.25, 0.8), amb=0.015,
           atmo=None, atmo_w=0.05, gain=1.0, gamma=1.0, alpha=1.0, terminator=0.12):
    """Render a textured, lit planet into canvas (in place). light = direction toward the sun
    in screen space (x right, y up, z toward viewer)."""
    if alpha <= 0:
        return canvas
    pad = r * (1 + 3 * atmo_w) if atmo is not None else r + 2
    x0, x1 = int(max(0, cx - pad)), int(min(W, cx + pad + 1))
    y0, y1 = int(max(0, cy - pad)), int(min(H, cy + pad + 1))
    if x0 >= x1 or y0 >= y1:
        return canvas
    xs = (_XX[y0:y1, x0:x1] - cx) / r
    ys = -(_YY[y0:y1, x0:x1] - cy) / r
    rr = np.sqrt(xs * xs + ys * ys)
    inside = rr < 1.0
    z = np.sqrt(np.clip(1 - rr * rr, 0, 1))
    L = np.array(light, np.float32)
    L /= np.linalg.norm(L)
    lam = xs * L[0] + ys * L[1] + z * L[2]
    M = rot_y(lon) @ rot_x(tilt)
    nx = M[0, 0] * xs + M[0, 1] * ys + M[0, 2] * z
    ny = M[1, 0] * xs + M[1, 1] * ys + M[1, 2] * z
    nz = M[2, 0] * xs + M[2, 1] * ys + M[2, 2] * z
    lat = np.arcsin(np.clip(ny, -1, 1))
    lo = np.arctan2(nx, nz)
    th, tw = tex.shape[:2]
    u = ((lo / (2 * math.pi) + 0.5) % 1.0) * (tw - 1)
    v = (0.5 - lat / math.pi) * (th - 1)
    col = cv2.remap(tex, u.astype(np.float32), v.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    if gamma != 1.0:
        col = col ** gamma
    shade = np.clip((lam + terminator) / (1 + terminator), 0, 1) ** 1.2
    limb = 0.75 + 0.25 * z
    lit = col * (shade * limb * gain + amb)[..., None]
    a = np.clip((1.0 - rr) * r * 1.2, 0, 1)[..., None] * alpha
    reg = canvas[y0:y1, x0:x1]
    reg[:] = reg * (1 - a) + lit * a
    if atmo is not None:
        rim = np.exp(-(((rr - 1.0) / atmo_w) ** 2)) * np.where(rr < 1, 0.55, 1.0)
        litside = np.clip((xs * L[0] + ys * L[1]) / np.maximum(rr, 1e-3) * 0.7 + 0.5, 0, 1)
        reg += (rim * litside * alpha)[..., None] * np.array(atmo, np.float32)
    return canvas

# ----------------------------------------------------------------------------- stars
class Starfield:
    def __init__(self, n=5000, seed=1, depth=60.0):
        rng = np.random.default_rng(seed)
        self.p = np.stack([rng.uniform(-60, 60, n), rng.uniform(-34, 34, n), rng.uniform(0.5, depth, n)], 1).astype(np.float32)
        self.b = (rng.pareto(2.2, n) * 0.25 + 0.15).astype(np.float32)
        tint = rng.uniform(0, 1, n)
        self.c = np.stack([0.85 + 0.15 * tint, 0.9 + 0.05 * tint, 1.0 - 0.15 * tint], 1).astype(np.float32)
        self.depth = depth

    def render(self, travel=0.0, pan=(0.0, 0.0), f=900.0, gain=1.0, streak=0.0, canvas=None):
        img = canvas if canvas is not None else np.zeros((H, W, 3), np.float32)
        p = self.p.copy()
        p[:, 2] = (p[:, 2] - travel) % self.depth + 0.3
        x = p[:, 0] / p[:, 2] * f + W / 2 + pan[0]
        y = p[:, 1] / p[:, 2] * f + H / 2 + pan[1]
        ok = (x > 0) & (x < W - 1) & (y > 0) & (y < H - 1)
        bri = self.b * np.clip(3.0 / p[:, 2], 0.25, 2.5) * gain
        lay = np.zeros((H // 2, W // 2, 3), np.float32)
        xi, yi = (x[ok] / 2).astype(int), (y[ok] / 2).astype(int)
        np.add.at(lay, (yi, xi), self.c[ok] * bri[ok, None])
        if streak > 0:
            for k in range(1, 4):
                p2 = p.copy(); p2[:, 2] += streak * k / 3
                x2 = p2[:, 0] / p2[:, 2] * f + W / 2 + pan[0]
                y2 = p2[:, 1] / p2[:, 2] * f + H / 2 + pan[1]
                ok2 = ok & (x2 > 0) & (x2 < W - 1) & (y2 > 0) & (y2 < H - 1)
                np.add.at(lay, ((y2[ok2] / 2).astype(int), (x2[ok2] / 2).astype(int)), self.c[ok2] * bri[ok2, None] * 0.5)
        lay = cv2.GaussianBlur(lay, (0, 0), 0.6)
        up = cv2.resize(lay, (W, H), interpolation=cv2.INTER_LINEAR)
        glow = cv2.GaussianBlur(lay, (0, 0), 3.0)
        img += up * 1.6 + cv2.resize(glow, (W, H)) * 0.8
        return img

# ----------------------------------------------------------------------------- particles
class Dust:
    """Floating motes with depth (z: 0 far .. 1 near), parallaxed by camera motion."""

    def __init__(self, n=220, seed=3, color=(1.0, 0.85, 0.6), drift=(0.004, -0.006), area=(0, 0, 1, 1)):
        rng = np.random.default_rng(seed)
        self.x = rng.uniform(area[0] - 0.1, area[2] + 0.1, n).astype(np.float32)
        self.y = rng.uniform(area[1] - 0.1, area[3] + 0.1, n).astype(np.float32)
        self.z = rng.uniform(0, 1, n).astype(np.float32) ** 1.6
        self.ph = rng.uniform(0, 6.28, n).astype(np.float32)
        self.v = (np.array(drift, np.float32)[None] * rng.uniform(0.5, 1.5, (n, 1))).astype(np.float32)
        self.color = np.array(color, np.float32)

    def render(self, img, t, cam=(0.0, 0.0), gain=1.0):
        x = self.x + self.v[:, 0] * t + cam[0] * (0.2 + self.z) + 0.004 * np.sin(t * 0.7 + self.ph)
        y = self.y + self.v[:, 1] * t + cam[1] * (0.2 + self.z) + 0.004 * np.cos(t * 0.5 + self.ph)
        x, y = x % 1.2 - 0.1, y % 1.2 - 0.1
        tw = 0.6 + 0.4 * np.sin(t * 2.3 + self.ph * 3)
        for lo, hi, sig, k in ((0, 0.45, 0.7, 0.9), (0.45, 0.8, 1.8, 0.8), (0.8, 1.01, 6.0, 2.2)):
            m = (self.z >= lo) & (self.z < hi) & (x > 0) & (x < 1) & (y > 0) & (y < 1)
            if not m.any():
                continue
            lay = np.zeros((H // 2, W // 2), np.float32)
            np.add.at(lay, ((y[m] * (H // 2 - 1)).astype(int), (x[m] * (W // 2 - 1)).astype(int)), tw[m])
            lay = cv2.GaussianBlur(lay, (0, 0), sig) * (sig * sig * 2.0) * k
            img += cv2.resize(lay, (W, H))[..., None] * self.color * gain * 0.6
        return img

# ----------------------------------------------------------------------------- light FX
def glow(img, x, y, r, color, k=1.0):
    x0, x1 = int(max(0, x - 3 * r)), int(min(W, x + 3 * r))
    y0, y1 = int(max(0, y - 3 * r)), int(min(H, y + 3 * r))
    if x0 >= x1 or y0 >= y1 or k <= 0:
        return img
    d2 = ((_XX[y0:y1, x0:x1] - x) ** 2 + (_YY[y0:y1, x0:x1] - y) ** 2) / (r * r)
    img[y0:y1, x0:x1] += (np.exp(-d2) * k)[..., None] * np.array(color, np.float32)
    return img


def flare(img, x, y, k=1.0, color=(1.0, 0.85, 0.6)):
    glow(img, x, y, 60, color, 0.5 * k)
    glow(img, x, y, 14, (1, 1, 1), 0.9 * k)
    y0, y1 = int(max(0, y - 2)), int(min(H, y + 3))
    if y1 > y0:
        streak = np.exp(-np.abs(_XX[0] - x) / 380.0) * 0.35 * k
        img[y0:y1] += streak[None, :, None] * np.array(color, np.float32)
    for f, s, a in ((0.35, 30, 0.06), (0.6, 18, 0.05), (1.3, 50, 0.04)):
        gx, gy = W / 2 + (W / 2 - x) * f, H / 2 + (H / 2 - y) * f
        glow(img, gx, gy, s, (0.5, 0.7, 1.0), a * k)
    return img


def rings(img, x, y, t, color=(0.35, 0.65, 1.0), period=1.6, speed=420, k=1.0, n=3):
    """Expanding transmission rings."""
    lay = np.zeros((H // 2, W // 2), np.float32)
    for i in range(n):
        ph = (t / period + i / n) % 1.0
        r = ph * speed * period / 2
        a = (1 - ph) ** 1.5
        if r > 1:
            cv2.circle(lay, (int(x / 2), int(y / 2)), int(r), float(a), 2, cv2.LINE_AA)
    lay = cv2.GaussianBlur(lay, (0, 0), 1.5) * 1.3 + cv2.GaussianBlur(lay, (0, 0), 8) * 2.5
    img += cv2.resize(lay, (W, H))[..., None] * np.array(color, np.float32) * k
    return img


def tv_look(img, t, k=1.0):
    """Surveyor TV-camera look: monochrome, scan lines, slight jitter and noise."""
    g = img @ np.array([0.3, 0.59, 0.11], np.float32)
    g = np.clip((g - 0.04) * 1.2, 0, 1)
    rng = np.random.default_rng(int(t * 24))
    rows = np.roll(g, int(rng.integers(-2, 3)), axis=1)
    lines = (0.82 + 0.18 * np.cos(_YY[:, :1] * math.pi / 2.0))
    rows = rows * lines + rng.normal(0, 0.035, (H // 4, W // 4)).repeat(4, 0).repeat(4, 1).astype(np.float32)
    out = np.stack([rows * 0.95, rows, rows * 1.02], -1)
    return img * (1 - k) + out * k

# ----------------------------------------------------------------------------- typography
FONTS = {"mont": os.path.join(ROOT, "fonts/Montserrat.ttf"), "serif": os.path.join(ROOT, "fonts/CormorantGaramond.ttf")}


@functools.lru_cache(maxsize=64)
def _font(name, size, weight):
    f = ImageFont.truetype(FONTS[name], size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


@functools.lru_cache(maxsize=128)
def text_sprite(txt, size, font="mont", weight=500, tracking=0.12):
    f = _font(font, size, weight)
    adv = [f.getlength(ch) + tracking * size for ch in txt]
    tw = int(sum(adv) + size)
    asc, desc = f.getmetrics()
    th = asc + desc + size // 2
    im = Image.new("L", (tw, th), 0)
    dr = ImageDraw.Draw(im)
    x = size // 2
    for ch, a in zip(txt, adv):
        dr.text((x, size // 4), ch, font=f, fill=255)
        x += a
    arr = np.asarray(im).astype(np.float32) / 255
    width = int(x - tracking * size + size // 2)
    return arr[:, :max(width, 1)]


def text(img, txt, x, y, size=36, alpha=1.0, font="mont", weight=500, tracking=0.12, color=(1, 1, 1),
         anchor="mm", glow_k=0.0, slide=0.0):
    if alpha <= 0.002:
        return img
    a = text_sprite(txt, size, font, weight, tracking)
    h, w = a.shape
    x0 = x - (w / 2 if anchor[0] == "m" else (w if anchor[0] == "r" else 0)) + slide
    y0 = y - h / 2
    x0, y0 = int(round(x0)), int(round(y0))
    xa, ya = max(0, x0), max(0, y0)
    xb, yb = min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb:
        return img
    sub = a[ya - y0:yb - y0, xa - x0:xb - x0][..., None] * alpha
    col = np.array(color, np.float32)
    if glow_k > 0:
        g = cv2.GaussianBlur(sub[..., 0], (0, 0), size * 0.25)[..., None] * glow_k
        img[ya:yb, xa:xb] += g * col
    img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - sub) + col * sub
    return img


def hline(img, x0, y, x1, alpha, color=(1, 1, 1), th=1.2):
    if alpha <= 0:
        return img
    y0 = int(y)
    xa, xb = int(min(x0, x1)), int(max(x0, x1))
    img[y0:y0 + max(1, int(th)), xa:xb] = img[y0:y0 + max(1, int(th)), xa:xb] * (1 - alpha) + np.array(color, np.float32) * alpha
    return img


def label(img, t, t0, title, sub=None, x=150, y=None, dur=3.0, size=30, color=(1, 1, 1), align="l"):
    """Restrained documentary label: thin rule wipes in, text fades/slides over a subtle soft scrim."""
    y = y if y is not None else H - LB - 90
    a = win(t, t0, t0 + dur, 0.5, 0.6)
    if a <= 0:
        return img
    p = ease_out((t - t0) / 0.8)
    anchor = "lm" if align == "l" else "rm"
    sgn = 1 if align == "l" else -1
    # Soft local darkening scrim so white labels read cleanly over sunlit regolith
    w_est = int(max(len(title) * size * 0.82, len(sub or "") * size * 0.50) + 140)
    sx0 = 0 if align == "l" else max(0, int(x - w_est))
    sx1 = min(W, int(x + w_est)) if align == "l" else W
    sy0, sy1 = max(LB, int(y - size * 1.6)), min(H - LB, int(y + size * 2.2))
    if sx1 > sx0 and sy1 > sy0:
        ux = np.linspace(0, 1, sx1 - sx0, dtype=np.float32)
        hx = (1 - ux) ** 1.6 if align == "l" else ux ** 1.6
        vy = np.maximum(0.0, np.sin(np.linspace(0, math.pi, sy1 - sy0, dtype=np.float32))) ** 1.1
        scrim = (vy[:, None] * hx[None, :])[..., None] * (0.45 * a)
        img[sy0:sy1, sx0:sx1] *= (1.0 - scrim)
    hline(img, x, y - size * 0.95, x + sgn * 70 * p, a * 0.9, color, 2)
    text(img, title, x + 2, y + 2, size, a * 0.55, "mont", 600, 0.22, (0, 0, 0), anchor, slide=sgn * (1 - p) * 18)
    text(img, title, x, y, size, a, "mont", 600, 0.22, color, anchor, slide=sgn * (1 - p) * 18)
    if sub:
        text(img, sub, x + 1, y + size * 1.15 + 1, int(size * 0.6), a * 0.55, "mont", 400, 0.2, (0, 0, 0), anchor, slide=sgn * (1 - p) * 10)
        text(img, sub, x, y + size * 1.15, int(size * 0.6), a * 0.88, "mont", 400, 0.2, color, anchor, slide=sgn * (1 - p) * 10)
    return img

# ----------------------------------------------------------------------------- grading & finishing
GRADES = {
    "space":  dict(lift=(0.0, 0.004, 0.012), gamma=(1.0, 1.0, 0.97), gain=(0.98, 1.0, 1.05), sat=1.0),
    "lunar":  dict(lift=(0.004, 0.006, 0.014), gamma=(0.98, 1.0, 1.02), gain=(1.04, 1.0, 0.95), sat=0.92),
    "flash":  dict(lift=(0.02, 0.012, 0.0), gamma=(0.95, 1.0, 1.08), gain=(1.08, 1.0, 0.86), sat=0.88),
    "apollo": dict(lift=(0.008, 0.007, 0.01), gamma=(0.98, 1.0, 1.03), gain=(1.06, 1.0, 0.92), sat=0.85),
    "mars":   dict(lift=(0.012, 0.004, 0.0), gamma=(0.96, 1.0, 1.06), gain=(1.06, 0.98, 0.9), sat=1.05),
    "final":  dict(lift=(0.0, 0.006, 0.02), gamma=(1.0, 1.0, 0.96), gain=(1.0, 1.0, 1.04), sat=1.0),
    "archival": dict(lift=(0.01, 0.009, 0.008), gamma=(1.0, 1.0, 1.0), gain=(1.03, 1.0, 0.95), sat=0.6),
}


def grade(img, name):
    g = GRADES[name]
    out = np.clip(img, 0, None)
    out = out * np.array(g["gain"], np.float32) + np.array(g["lift"], np.float32) * (1 - out)
    out = np.clip(out, 0, None) ** (1.0 / np.array(g["gamma"], np.float32))
    if g["sat"] != 1.0:
        lum = (out @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
        out = lum + (out - lum) * g["sat"]
    return out


_vig = None
_grain = None


def finish(img, t, bloom=0.22, vignette=0.32, grain=0.022, letterbox=True):
    global _vig, _grain
    if _vig is None:
        r = np.sqrt((GX / (W * 0.62)) ** 2 + (GY / (H * 0.68)) ** 2)
        _vig = (1 - vignette * np.clip(r, 0, 1.4) ** 2.2).astype(np.float32)[..., None]
        rng = np.random.default_rng(7)
        _grain = [cv2.resize(rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32), (W, H)) for _ in range(6)]
    small = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    br = np.clip(small - 0.72, 0, None)
    b = cv2.GaussianBlur(br, (0, 0), 6) * 0.6 + cv2.GaussianBlur(br, (0, 0), 22) * 0.9
    img = img + cv2.resize(b, (W, H)) * bloom
    img = img * _vig
    # soft highlight roll-off (filmic shoulder)
    img = np.where(img > 0.8, 0.8 + (1 - np.exp(-(img - 0.8) * 2.5)) * 0.2 / 1.0, img)
    img = img + _grain[int(t * FPS) % 6][..., None] * grain * (0.6 + 0.4 * (1 - img))
    if letterbox:
        img[:LB] = 0
        img[H - LB:] = 0
    return clamp01(img)


def to_u8(img):
    return (clamp01(img) * 255 + 0.5).astype(np.uint8)
