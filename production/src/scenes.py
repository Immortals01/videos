"""Shot list and per-frame compositor for "Abandoned, But Not Forgotten".

render_frame(t) -> uint8 RGB 1920x1080 frame at time t (seconds).
Preview stills:  python src/scenes.py 3.0 10 21.5 ...   -> scratch/preview.jpg
"""
import functools, math, os, sys
import cv2, numpy as np, soundfile as sf

sys.path.insert(0, os.path.dirname(__file__))
import fx
from fx import W, H, LB, ease, ease_in, ease_out, smooth, sat, lerp, win
from timeline import T, E, SCENES, DURATION
from script_lines import LINES

ROOT = fx.ROOT
SC = {k: v[0] for k, v in SCENES.items()}           # scene start times


# ----------------------------------------------------------------------------- helpers
def noise1(t, seed=0.0):
    """Smooth pseudo-random value in [-1,1] (sum of incommensurate sines)."""
    return (math.sin(t * 7.3 + seed) * 0.5 + math.sin(t * 13.1 + seed * 2.1) * 0.3 +
            math.sin(t * 23.7 + seed * 3.7) * 0.2)


def shake(t, amp):
    return (noise1(t, 1.0) * amp, noise1(t, 5.0) * amp)


def cam(name, u, z=(1.0, 1.1), c0=(0.5, 0.5), c1=None, px=(0.0, 0.0), py=(0.0, 0.0), dolly=0.0,
        focus=None, dof=0.0, warps=(), shk=(0.0, 0.0), roll=(0.0, 0.0), crop=None, curve=ease):
    """Animated virtual camera over a plate; u is shot progress 0..1."""
    p = fx.plate(name, crop=crop)
    e = curve(u)
    c1 = c1 or c0
    zoom = lerp(z[0], z[1], e)
    cx, cy = lerp(c0[0], c1[0], e), lerp(c0[1], c1[1], e)
    # keep the view inside the plate (no reflected borders)
    hw, hh = W / (2 * zoom * p.w), H / (2 * zoom * p.h)
    cx = min(max(cx, hw + 0.004), 1 - hw - 0.004)
    cy = min(max(cy, hh + 0.004), 1 - hh - 0.004)
    img = p.render(zoom=zoom, cx=cx, cy=cy, px=lerp(px[0], px[1], e), py=lerp(py[0], py[1], e),
                   dolly=dolly * e, focus=focus, dof=dof, warps=warps, shake=shk,
                   roll=lerp(roll[0], roll[1], e))
    return img, (p, zoom, cx, cy)


def p2s(view, u, v):
    """Plate-normalized point -> screen pixel for a cam() view."""
    p, zoom, cx, cy = view
    return ((u - cx) * p.w * zoom + W / 2, (v - cy) * p.h * zoom + H / 2)


def space_bg(t, gain=1.0, travel=0.0, pan=(0.0, 0.0), milky=0.5):
    img = np.zeros((H, W, 3), np.float32)
    if milky > 0:
        bg, _ = cam("p_space", sat(t / 90.0), z=(1.0, 1.06), c0=(0.48, 0.5), c1=(0.52, 0.5))
        img += bg * milky
    STARS.render(travel=travel, pan=pan, gain=gain, canvas=img)
    return img


STARS = fx.Starfield(4200, seed=11)


@functools.lru_cache(maxsize=1)
def scene1_voice():
    """Mono 24 kHz track of the scene-1 lines placed on the timeline (drives the waveform)."""
    sr = 24000
    track = np.zeros(int(9 * sr), np.float32)
    for lid in ("s1_01", "s1_02", "s1_03", "s1_04"):
        d, _ = sf.read(os.path.join(ROOT, "audio/voice", lid + ".wav"), dtype="float32")
        a = int(T[lid] * sr)
        track[a:a + len(d)] += d[:len(track) - a]
    return track / (np.abs(track).max() + 1e-6), sr


def waveform(img, t, y, k=1.0, color=(0.35, 0.7, 1.0), x0=260, x1=W - 260):
    """Oscilloscope trace of the actual voice signal around time t."""
    if k <= 0.01:
        return img
    tr, sr = scene1_voice()
    n = 900
    a = int((t - 0.06) * sr)
    seg = np.zeros(n * 4, np.float32)
    lo, hi = max(0, a), min(len(tr), a + n * 4)
    if hi > lo:
        seg[lo - a:hi - a] = tr[lo:hi]
    seg = seg.reshape(n, 4).mean(1)
    xs = np.linspace(x0, x1, n)
    env = np.sin(np.linspace(0, math.pi, n)) ** 0.8
    rng = np.random.default_rng(int(t * 24))
    hiss = rng.normal(0, 0.012, n)
    ys = y - (seg * 230 + hiss * 60) * env
    lay = np.zeros((H // 2, W // 2), np.float32)
    pts = np.stack([xs / 2, ys / 2], 1).astype(np.int32)
    cv2.polylines(lay, [pts], False, 1.0, 1, cv2.LINE_AA)
    lay = cv2.GaussianBlur(lay, (0, 0), 0.7) * 1.4 + cv2.GaussianBlur(lay, (0, 0), 6) * 3.0
    img += cv2.resize(lay, (W, H))[..., None] * np.array(color, np.float32) * k
    return img


def disk(img, x, y, r, color, alpha=1.0, th=-1):
    lay = np.zeros((H, W), np.float32)
    cv2.circle(lay, (int(x * 4), int(y * 4)), int(r * 4), 1.0, th if th < 0 else int(th * 4), cv2.LINE_AA, 2)
    img += lay[..., None] * np.array(color, np.float32) * alpha
    return img


def badge(img, src_name, crop, x, y, r, alpha, ring=(1.0, 0.82, 0.5)):
    """Circular host portrait (cropped from a plate) with a glowing ring."""
    if alpha <= 0.01 or r < 2:
        return img
    p = fx.plate(src_name)
    h, w = p.img.shape[:2]
    x0, y0, x1, y1 = int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)
    s = int(2 * r)
    tile = cv2.resize(p.img[y0:y1, x0:x1], (s, s), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    m = np.clip(r - np.sqrt((xx - r + 0.5) ** 2 + (yy - r + 0.5) ** 2), 0, 1)[..., None] * alpha
    xa, ya = int(x - r), int(y - r)
    xb, yb = xa + s, ya + s
    if xa < 0 or ya < 0 or xb > W or yb > H:
        return img
    img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - m) + tile * m
    disk(img, x, y, r + 3, ring, alpha * 0.9, th=2)
    fx.glow(img, x, y, r * 1.3, ring, 0.05 * alpha)
    return img


@functools.lru_cache(maxsize=1)
def tv_tiles():
    """Monochrome TV-frame tiles (Surveyor camera look) for the 6,315 images graphic."""
    srcs = [("k_scoop", 0.55, 0.62), ("p_hero", 0.2, 0.75), ("p_lowangle", 0.75, 0.82), ("k_touchdown", 0.3, 0.85),
            ("k_scoop", 0.8, 0.8), ("p_hero", 0.7, 0.55), ("p_lowangle", 0.25, 0.85), ("k_descent", 0.35, 0.85),
            ("k_scoop", 0.2, 0.85), ("p_hero", 0.45, 0.88), ("k_touchdown", 0.75, 0.82), ("p_camera", 0.15, 0.85)]
    tiles = []
    rng = np.random.default_rng(4)
    for i in range(40):
        name, u, v = srcs[i % len(srcs)]
        im = cv2.imread(os.path.join(ROOT, "plates", name + ".jpg"))
        h, w = im.shape[:2]
        cw, ch = int(w * rng.uniform(0.16, 0.26)), 0
        ch = int(cw * 0.75)
        cx = int(np.clip((u + rng.uniform(-0.12, 0.12)) * w, cw / 2, w - cw / 2))
        cy = int(np.clip((v + rng.uniform(-0.08, 0.05)) * h, ch / 2, h - ch / 2))
        c = im[cy - ch // 2:cy + ch // 2, cx - cw // 2:cx + cw // 2]
        g = cv2.cvtColor(cv2.resize(c, (256, 192), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
        g = np.clip((g - 0.05) * 1.25, 0, 1)
        g *= (0.85 + 0.15 * np.cos(np.arange(192)[:, None] * math.pi / 1.5))
        g += rng.normal(0, 0.03, g.shape).astype(np.float32)
        tiles.append(np.clip(g, 0, 1))
    return tiles


# ----------------------------------------------------------------------------- shots
# Each shot: (start, function(t, u)). A shot lasts until the next one starts. XF[i] is the
# cross-dissolve centred on the boundary between shot i and i+1.

def s1_space(t, u):
    a = smooth((t - 0.15) / 2.6)
    trav = t * 0.9
    img = space_bg(t, gain=a, travel=trav, pan=(-t * 6, t * 2), milky=0.55 * a)
    # the Moon slowly emerges as the source of the signal
    mx, my = lerp(W * 0.64, W * 0.56, ease(t / 7.6)), lerp(H * 0.42, H * 0.47, ease(t / 7.6))
    r = 6 + 260 * ease_in(sat((t - 2.0) / 5.6)) ** 1.15
    malpha = smooth((t - 2.4) / 1.6)
    fx.sphere(img, fx.texture("moon_2k.tif"), mx, my, r, lon=0.25 + t * 0.01, tilt=0.05,
              light=(0.75, 0.25, 0.55), amb=0.01, gain=1.15, alpha=malpha)
    speaking = max(win(t, T[l] - 0.05, E[l] + 0.1, 0.08, 0.3) for l in ("s1_01", "s1_02", "s1_03", "s1_04"))
    sig = smooth((t - 1.2) / 0.5)
    fx.rings(img, mx, my, t, k=sig * (0.25 + 0.55 * speaking) * (1 - 0.6 * smooth((t - 5.8) / 1.2)))
    fx.glow(img, mx, my, 26 + r * 0.25, (0.35, 0.65, 1.0), sig * (0.25 + 0.35 * speaking) * (1 - malpha * 0.6))
    waveform(img, t, H * 0.5, k=sig * (0.25 + 0.75 * speaking) * (1 - smooth((t - 6.2) / 0.7)))
    return fx.grade(img, "space")


def s2_hero(t, u):
    arm = (0.165, 0.83, 0.07, 0.06, 0.0, 0.004 * math.sin(max(0, t - 9.6) * 1.6) * smooth((t - 9.6) / 0.8))
    img, v = cam("p_hero", u, z=(1.0, 1.16), c0=(0.52, 0.56), c1=(0.53, 0.56), px=(-34, 26), py=(4, -4), dolly=0.18,
                 warps=(arm,))
    DUST_LUNAR.render(img, t, cam=(-0.02 * u, 0.0), gain=0.55)
    return fx.grade(img, "lunar")


def s2_camera(t, u):
    # camera assembly turning to look at us: side view -> facing view with a local turn warp
    k = smooth((t - 12.15) / 1.2)
    turn = (0.48, 0.3, 0.12, 0.15, -0.025 * math.sin(k * math.pi), 0.0)
    a, _ = cam("p_camera", u, z=(1.0, 1.12), c0=(0.5, 0.42), c1=(0.48, 0.38), px=(-22, 18), dolly=0.15,
               focus=0.85, dof=1.2, warps=(turn,))
    if k > 0:
        b, _ = cam("k_camera_front", u, z=(1.05, 1.16), c0=(0.47, 0.42), c1=(0.46, 0.38), px=(-18, 16), dolly=0.12,
                   focus=0.85, dof=1.2)
        a = a * (1 - k) + b * k
    DUST_LUNAR.render(a, t, cam=(0.01 * u, 0), gain=0.45)
    return fx.grade(a, "lunar")


def s3_launch(t, u):
    lt = t - SC[3]
    ign = smooth((lt - 0.35) / 0.5)
    rise = ease_in(sat((lt - 0.9) / 3.4))
    img, v = cam("k_launch", u, z=(1.0, 1.08), c0=(0.56, 0.66), c1=(0.56, 0.44), px=(0, 0), py=(-30, 30),
                 dolly=0.08, shk=shake(t, 9 * ign * (1 - 0.5 * rise)), curve=lambda x: x)
    fx_x, fx_y = p2s(v, 0.585, 0.83)
    fl = 0.75 + 0.25 * noise1(t * 3.0, 2.0)
    fx.glow(img, fx_x, fx_y - rise * 120, 260, (1.0, 0.55, 0.2), 0.35 * ign * fl)
    fx.glow(img, fx_x, fx_y - rise * 120, 70, (1.0, 0.9, 0.7), 0.45 * ign * fl)
    img *= (0.8 + 0.2 * ign * fl)
    return fx.grade(img, "flash")


def s3_cruise(t, u):
    img, v = cam("k_cruise", u, z=(1.0, 1.1), c0=(0.47, 0.5), c1=(0.53, 0.48), px=(-30, 30), dolly=0.1)
    return fx.grade(img, "flash")


def s3_descent(t, u):
    img, v = cam("k_descent", u, z=(1.04, 1.18), c0=(0.52, 0.42), c1=(0.52, 0.5), px=(16, -16), py=(-10, 10),
                 dolly=0.12, shk=shake(t, 3.0))
    fl = 0.8 + 0.2 * noise1(t * 4.0, 7.0)
    for pu in (0.465, 0.555):
        x, y = p2s(v, pu, 0.6)
        fx.glow(img, x, y, 70, (0.5, 0.8, 1.0), 0.28 * fl)
    return fx.grade(img, "flash")


def s3_touchdown(t, u):
    td = SC[3] + 12.95            # first contact (Surveyor 3 bounced twice before settling)
    hit = math.exp(-max(0, t - td) * 5) * (t > td) + 0.5 * math.exp(-max(0, t - td - 0.75) * 6) * (t > td + 0.75)
    img, v = cam("k_touchdown", u, z=(1.12, 1.0), c0=(0.45, 0.5), c1=(0.47, 0.5), px=(20, -20), dolly=-0.1,
                 shk=shake(t, 2.0 + 14 * hit), curve=ease_out)
    DUST_LUNAR.render(img, t, cam=(0.01 * u, -0.02 * u), gain=0.6 + 1.2 * hit)
    return fx.grade(img, "flash")


def s4_scoop(t, u):
    lt = t - SC[4]
    dig = (0.18, 0.86, 0.09, 0.08, 0.0, -0.006 * smooth((lt - 1.4) / 0.9) + 0.003 * smooth((lt - 2.9) / 0.8))
    img, v = cam("k_scoop", u, z=(1.05, 1.4), c0=(0.6, 0.55), c1=(0.78, 0.6), px=(-24, 18), dolly=0.2,
                 focus=0.8, dof=1.0, warps=(dig,))
    DUST_LUNAR.render(img, t, cam=(-0.02 * u, 0), gain=0.5)
    return fx.grade(img, "lunar")


def s4_lens(t, u):
    img, v = cam("p_camera", u, z=(1.25, 1.9), c0=(0.47, 0.33), c1=(0.44, 0.33), px=(-10, 10), dolly=0.2,
                 focus=0.9, dof=1.4, curve=ease_in)
    return fx.grade(img, "lunar")


def s4_images(t, u):
    """Motion graphic: the camera's TV frames tile up while the counter runs to 6,315."""
    lt = u
    img = np.zeros((H, W, 3), np.float32) + np.array((0.01, 0.012, 0.02), np.float32)
    tiles = tv_tiles()
    zoom = lerp(1.9, 1.0, ease_out(sat(lt * 1.15)))
    tw, th, gap = 256, 192, 18
    cols, rows = 9, 5
    gx0 = W / 2 - (cols * (tw + gap)) / 2 * zoom
    gy0 = H / 2 - (rows * (th + gap)) / 2 * zoom - 30
    for i in range(cols * rows):
        r, c = divmod(i, cols)
        d = abs(c - cols // 2) + abs(r - rows // 2)
        a = smooth((lt * 2.4 - d * 0.16))
        if a <= 0:
            continue
        x = gx0 + c * (tw + gap) * zoom
        y = gy0 + r * (th + gap) * zoom
        s = (int(tw * zoom), int(th * zoom))
        xa, ya = int(x), int(y)
        xb, yb = xa + s[0], ya + s[1]
        if xb <= 0 or yb <= 0 or xa >= W or ya >= H:
            continue
        tile = cv2.resize(tiles[i % len(tiles)], s, interpolation=cv2.INTER_LINEAR)
        cx0, cy0 = max(0, -xa), max(0, -ya)
        xa2, ya2, xb2, yb2 = max(xa, 0), max(ya, 0), min(xb, W), min(yb, H)
        sub = tile[cy0:cy0 + yb2 - ya2, cx0:cx0 + xb2 - xa2]
        img[ya2:yb2, xa2:xb2] = img[ya2:yb2, xa2:xb2] * (1 - a) + (sub[..., None] * np.array((0.92, 0.95, 1.0))) * a
    n = int(round(6315 * ease_out(sat((lt - 0.08) / 0.75))))
    ca = smooth((lt - 0.05) / 0.12)
    y = H - LB - 120
    fx.glow(img, W / 2, y, 300, (0, 0, 0), 0)
    img[int(y - 70):int(y + 70)] *= 1 - 0.55 * ca
    fx.text(img, f"{n:,} IMAGES", W / 2, y - 8, 64, ca, "mont", 600, 0.18, (1.0, 0.93, 0.8), glow_k=0.25)
    fx.text(img, "TELEVISION PICTURES RETURNED BY SURVEYOR 3", W / 2, y + 48, 20, ca * 0.8, "mont", 400, 0.25)
    return fx.grade(img, "lunar")


def s4_lowangle(t, u):
    img, v = cam("p_lowangle", u, z=(1.12, 1.0), c0=(0.45, 0.5), c1=(0.55, 0.5), px=(40, -40), dolly=-0.12)
    DUST_LUNAR.render(img, t, cam=(0.03 * u, 0), gain=0.5)
    return fx.grade(img, "lunar")


def s5_waiting(t, u):
    # time passes: the light slowly swings and dims as the lander waits alone
    img, v = cam("p_hero", u, z=(1.18, 1.02), c0=(0.5, 0.55), c1=(0.5, 0.55), px=(20, -20), dolly=-0.1)
    sweep = 0.8 + 0.2 * math.cos(u * math.pi * 2)
    img = img * sweep
    STARS.render(travel=0, pan=(0, 0), gain=0.15, canvas=img)
    return fx.grade(img, "apollo")


def s5_wide(t, u):
    img, v = cam("k_apollo_wide", u, z=(1.0, 1.2), c0=(0.5, 0.52), c1=(0.56, 0.55), px=(-30, 24), dolly=0.15)
    DUST_LUNAR.render(img, t, cam=(-0.02 * u, 0), gain=0.35)
    return fx.grade(img, "apollo")


def s5_examine(t, u):
    img, v = cam("k_apollo_examine", u, z=(1.0, 1.16), c0=(0.5, 0.55), c1=(0.47, 0.6), px=(-24, 20), dolly=0.14,
                 focus=0.7, dof=0.6)
    return fx.grade(img, "apollo")


def s5_beside(t, u):
    img, v = cam("k_apollo_beside", u, z=(1.0, 1.22), c0=(0.48, 0.58), c1=(0.47, 0.63), px=(-20, 18), dolly=0.18,
                 focus=0.75, dof=0.7)
    x, y = p2s(v, 0.49, 0.6)
    fx.glow(img, x, y, 260, (1.0, 0.8, 0.5), 0.05 + 0.05 * u)
    return fx.grade(img, "apollo")


def s5_pov(t, u):
    # Surveyor 3's own point of view: its TV camera looks up at the visitor
    img, v = cam("k_apollo_beside", u, z=(1.9, 2.2), c0=(0.49, 0.6), c1=(0.49, 0.58), px=(0, 0), dolly=0.0)
    img = fx.tv_look(img, t, 0.85)
    iris = np.clip(1.25 - np.sqrt((fx.GX / (W * 0.55)) ** 2 + (fx.GY / (H * 0.55)) ** 2), 0, 1) ** 0.7
    img = img * iris[..., None]
    fx.glow(img, W / 2, H / 2, 600, (1.0, 0.85, 0.6), 0.04)
    return fx.grade(img, "archival")


def s6_space(t, u):
    img = space_bg(t, gain=1.0, travel=t * 2.5 + u * 18, pan=(-u * 120, 0), milky=0.35)
    mr = lerp(420, 90, ease(u))
    fx.sphere(img, fx.texture("moon_2k.tif"), lerp(W * 0.3, -160, ease_in(u)), H * 0.52, mr, lon=0.2, light=(0.7, 0.3, 0.6),
              gain=1.1, alpha=1.0)
    k = ease_out(sat((u - 0.15) / 0.85))
    fx.sphere(img, fx.texture("mars_2k.jpg"), lerp(W * 1.15, W * 0.58, k), H * 0.5, lerp(70, 560, ease_in(sat(u * 1.05))),
              lon=-0.6 + u * 0.3, tilt=0.15, light=(-0.4, 0.3, 0.85), gain=1.1, atmo=(0.9, 0.5, 0.3), atmo_w=0.035)
    return fx.grade(img, "space")


def s6_hero(t, u):
    img, v = cam("k_opp_hero", u, z=(1.0, 1.15), c0=(0.47, 0.5), c1=(0.52, 0.48), px=(-36, 28), dolly=0.15)
    DUST_MARS.render(img, t, cam=(-0.03 * u, 0), gain=0.6)
    return fx.grade(img, "mars")


def s6_arm(t, u):
    lt = t - (T["s6_03"] - 0.75)
    reach = (0.33, 0.68, 0.08, 0.08, 0.004 * smooth(lt / 1.5), -0.002 * smooth(lt / 1.5))
    img, v = cam("k_opp_arm", u, z=(1.05, 1.3), c0=(0.45, 0.6), c1=(0.3, 0.68), px=(22, -18), dolly=0.15,
                 focus=0.8, dof=0.8, warps=(reach,))
    DUST_MARS.render(img, t, cam=(0.02 * u, 0), gain=0.5)
    return fx.grade(img, "mars")


def s6_storm(t, u):
    img, v = cam("k_opp_storm", u, z=(1.0, 1.1), c0=(0.48, 0.5), c1=(0.52, 0.52), px=(-14, 14), dolly=0.1,
                 shk=shake(t, 1.5))
    DUST_STORM.render(img, t * 3.0, cam=(-0.2 * u, 0), gain=1.1)
    return fx.grade(img, "mars")


def s6_sunset(t, u):
    img, v = cam("k_opp_sunset", u, z=(1.15, 1.0), c0=(0.55, 0.5), c1=(0.5, 0.5), px=(28, -28), dolly=-0.12)
    x, y = p2s(v, 0.325, 0.5)
    fx.glow(img, x, y, 220, (0.6, 0.75, 1.0), 0.08)
    return fx.grade(img, "mars")


# Scene 7 geometry (map of the two worlds)
MOON = (W * 0.27, H * 0.565, 185)
MARS = (W * 0.73, H * 0.565, 168)
SITE_MOON = (-0.397, 0.052)     # Surveyor 3: 3.0 S, 23.4 W  (disk coords, y down)
SITE_MARS = (-0.096, 0.034)     # Opportunity, Meridiani Planum: 1.95 S, 5.5 W


def s7_map(t, u):
    lt = t - SC[7]
    img = np.zeros((H, W, 3), np.float32)
    r = np.sqrt((fx.GX / W) ** 2 + (fx.GY / H) ** 2)
    img += (np.array((0.012, 0.03, 0.075), np.float32) * (1 - np.clip(r * 1.3, 0, 1))[..., None])
    STARS.render(travel=t * 0.3, pan=(-lt * 8, 0), gain=0.8, canvas=img)
    drift = lt * 6
    (mx, my, mr), (rx, ry, rr) = MOON, MARS
    mx, rx = mx - drift * 0.5, rx + drift * 0.5
    a_in = smooth(lt / 1.2)
    fx.sphere(img, fx.texture("moon_2k.tif"), mx, my, mr, lon=0.0, light=(0.35, 0.25, 0.9), gain=1.05, alpha=a_in)
    fx.sphere(img, fx.texture("mars_2k.jpg"), rx, ry, rr, lon=0.0, light=(-0.35, 0.25, 0.9), gain=1.1, alpha=a_in,
              atmo=(0.9, 0.5, 0.3), atmo_w=0.035)
    sm = (mx + SITE_MOON[0] * mr, my + SITE_MOON[1] * mr)
    sr = (rx + SITE_MARS[0] * rr, ry + SITE_MARS[1] * rr)
    gold = (1.0, 0.8, 0.45)
    # glowing location markers
    for (x, y), t0 in ((sm, 0.5), (sr, 0.9)):
        a = smooth((lt - t0) / 0.4)
        if a > 0:
            fx.glow(img, x, y, 10, gold, 1.2 * a)
            ph = ((lt - t0) * 0.8) % 1.0
            disk(img, x, y, 6 + ph * 30, gold, a * (1 - ph) * 0.8, th=1.5)
    # arc connecting the two worlds, drawn on, with a travelling light
    draw = ease(sat((lt - 1.1) / 1.8))
    if draw > 0:
        n = 160
        s = np.linspace(0, draw, n)
        c = ((sm[0] + sr[0]) / 2, min(sm[1], sr[1]) - 310)
        xs = (1 - s) ** 2 * sm[0] + 2 * (1 - s) * s * c[0] + s ** 2 * sr[0]
        ys = (1 - s) ** 2 * sm[1] + 2 * (1 - s) * s * c[1] + s ** 2 * sr[1]
        lay = np.zeros((H // 2, W // 2), np.float32)
        for i in range(0, n - 1, 2):
            cv2.line(lay, (int(xs[i] / 2), int(ys[i] / 2)), (int(xs[i + 1] / 2), int(ys[i + 1] / 2)), 0.9, 1, cv2.LINE_AA)
        lay = cv2.GaussianBlur(lay, (0, 0), 0.6) + cv2.GaussianBlur(lay, (0, 0), 5) * 2
        img += cv2.resize(lay, (W, H))[..., None] * np.array(gold, np.float32) * 0.7
        q = ((lt - 1.1) / 2.4) % 1.0
        qs = q * draw
        px_ = (1 - qs) ** 2 * sm[0] + 2 * (1 - qs) * qs * c[0] + qs ** 2 * sr[0]
        py_ = (1 - qs) ** 2 * sm[1] + 2 * (1 - qs) * qs * c[1] + qs ** 2 * sr[1]
        fx.glow(img, px_, py_, 8, (1, 0.95, 0.85), 1.0)
        fx.glow(img, px_, py_, 30, gold, 0.25)
    # the two hosts appear cleanly above the planet limbs
    tb = T["s7_02"] - SC[7] - 0.2
    for (x, y), src, crop, name, sub, dx, t0 in (
            (sm, "p_hero", (0.27, 0.17, 0.67, 0.88), "SURVEYOR 3", "THE MOON  ·  1967", -1, tb),
            (sr, "k_opp_hero", (0.28, 0.08, 0.84, 0.92), "OPPORTUNITY", "MARS  ·  2004", 1, tb + 0.35)):
        a = smooth((lt - t0) / 0.5)
        pop = ease_out(sat((lt - t0) / 0.6))
        bx, by = x + dx * 36, 282
        if a > 0:
            lay = np.zeros((H, W), np.float32)
            cv2.line(lay, (int(x), int(y - 12)), (int(bx), int(by + 112 * pop)), 0.55 * a, 1, cv2.LINE_AA)
            img += lay[..., None] * np.array(gold, np.float32)
            badge(img, src, crop, bx, by, 72 * (0.6 + 0.4 * pop), a)
            fx.text(img, name, bx, by - 102, 25, a, "mont", 600, 0.24, (1, 1, 1))
            fx.text(img, sub, bx + 1, by + 95, 16, a * 0.6, "mont", 400, 0.28, (0, 0, 0))
            fx.text(img, sub, bx, by + 94, 16, a * 0.9, "mont", 400, 0.28, (1, 0.9, 0.75))
    ua = win(lt, T["s7_03"] - SC[7], 99, 0.6, 0.1)
    fx.text(img, "EXPLORE   ·   TRAVEL   ·   DISCOVER", W / 2, H - LB - 54, 22, ua * 0.88, "mont", 500, 0.32,
            (0.85, 0.92, 1.0))
    return fx.grade(img, "final")


def s7_title(t, u):
    lt = t - 85.0
    img = np.zeros((H, W, 3), np.float32)
    r = np.sqrt((fx.GX / W) ** 2 + (fx.GY / H) ** 2)
    img += (np.array((0.014, 0.034, 0.085), np.float32) * (1 - np.clip(r * 1.25, 0, 1))[..., None])
    STARS.render(travel=t * 0.3 + lt * 1.5, pan=(-lt * 8, 0), gain=0.7, canvas=img)
    ta = smooth((t - 85.15) / 1.25)
    sp = 0.13 + 0.05 * (1 - ease_out(sat((t - 85.15) / 3.4)))
    fx.glow(img, W / 2, H / 2 - 30, 520, (1.0, 0.75, 0.4), 0.06 * ta)
    fx.text(img, "ABANDONED, BUT NOT FORGOTTEN", W / 2, H / 2 - 42, 68, ta, "serif", 600, sp, (1.0, 0.96, 0.88),
            glow_k=0.35)
    la = smooth((t - 86.85) / 1.0)
    fx.hline(img, W / 2 - 260 * la, H / 2 + 26, W / 2 + 260 * la, la * 0.75, (1.0, 0.8, 0.45), 1.5)
    fx.text(img, "Every machine has a story. Every discovery deserves to be remembered.", W / 2, H / 2 + 70, 30,
            la * 0.94, "serif", 500, 0.06, (0.9, 0.93, 1.0))
    return fx.grade(img, "final")


DUST_LUNAR = fx.Dust(160, seed=3, color=(1.0, 0.9, 0.75), drift=(0.003, -0.002))
DUST_MARS = fx.Dust(200, seed=5, color=(1.0, 0.75, 0.5), drift=(0.008, -0.002))
DUST_STORM = fx.Dust(700, seed=9, color=(0.85, 0.6, 0.4), drift=(0.05, 0.004))

SHOTS = [
    (0.0, s1_space, 0.9),
    (SC[2], s2_hero, 0.7),
    (11.35, s2_camera, 0.35),
    (SC[3], s3_launch, 0.7),
    (20.05, s3_cruise, 0.7),
    (24.25, s3_descent, 0.45),
    (28.15, s3_touchdown, 0.7),
    (SC[4], s4_scoop, 0.6),
    (36.5, s4_lens, 0.3),
    (37.75, s4_images, 0.8),
    (40.75, s4_lowangle, 1.0),
    (SC[5], s5_waiting, 1.0),
    (47.55, s5_wide, 0.8),
    (T["s5_04"] - 0.25, s5_examine, 0.8),
    (T["s5_05"] - 0.2, s5_beside, 0.6),
    (T["s5_06"] - 0.25, s5_pov, 1.0),
    (SC[6], s6_space, 0.9),
    (T["s6_02"] + 0.1, s6_hero, 0.6),
    (T["s6_03"] - 0.4, s6_arm, 0.6),
    (T["s6_04"] - 0.15, s6_storm, 0.8),
    (T["s6_05"] + 0.35, s6_sunset, 1.0),
    (SC[7], s7_map, 1.4),
    (85.0, s7_title, None),
]


def shot_range(i):
    s = SHOTS[i][0] - (SHOTS[i - 1][2] / 2 if i > 0 else 0)
    e = SHOTS[i + 1][0] + SHOTS[i][2] / 2 if i + 1 < len(SHOTS) else DURATION
    return s, e


def render_shot(i, t):
    s, e = shot_range(i)
    return SHOTS[i][1](t, sat((t - s) / (e - s)))


# ----------------------------------------------------------------------------- overlays
LABELS = [
    # (time, title, sub, align)
    (T["s2_03"] - 0.1, "SURVEYOR 3", "ROBOTIC LUNAR LANDER  ·  OCEANUS PROCELLARUM", "l", 3.2),
    (T["s3_01"], "APRIL 17, 1967", "ATLAS-CENTAUR LAUNCH  ·  CAPE KENNEDY, FLORIDA", "l", 3.4),
    (SC[3] + 13.2, "APRIL 20, 1967", "TOUCHDOWN  ·  OCEANUS PROCELLARUM", "r", 3.2),
    (T["s4_01"], "SOIL ANALYSIS", "APRIL 1967  ·  SURFACE SAMPLER", "l", 3.6),
    (T["s4_03"] + 4.6, "APOLLO LANDING PREPARATION", "PROVING THE LUNAR SURFACE COULD SUPPORT A LANDING", "r", 3.4),
    (T["s5_03"] - 0.1, "NOVEMBER 1969", "APOLLO 12  ·  31 MONTHS LATER", "r", 3.3),
    (T["s5_04"] + 0.2, "RETURNED TO EARTH", "TV CAMERA  ·  SAMPLING SCOOP  ·  CABLES AND TUBING", "r", 3.1),
    (T["s6_02"] + 0.6, "OPPORTUNITY", "MARS EXPLORATION ROVER  ·  LANDED JANUARY 2004", "l", 3.4),
    (T["s6_03"] - 0.1, "EVIDENCE OF ANCIENT WATER", "MERIDIANI PLANUM, MARS", "r", 2.5),
    (T["s6_04"] + 0.05, "JUNE 2018", "PLANET-WIDE DUST STORM", "l", 2.1),
    (T["s6_05"] + 0.6, "NEARLY 15 YEARS ON MARS", "45 KILOMETRES DRIVEN  ·  MISSION ENDED 2019", "l", 2.5),
]
RECON = [(SC[3], SC[4]), (SC[5] + 2.8, SC[6])]     # dramatized historical reconstructions


def subtitles(img, t):
    for lid, scene, _, text, sub in LINES:
        a, b = T[lid], E[lid]
        if t < a - 0.1 or t > b + 0.35:
            continue
        parts = sub.split("|")
        if len(parts) > 1:
            w = np.cumsum([len(p) for p in parts]) / sum(len(p) for p in parts)
            k = int(np.searchsorted(w, sat((t - a) / (b - a)), side="right"))
            k = min(k, len(parts) - 1)
            seg_a = a + (w[k - 1] if k else 0) * (b - a)
            seg_b = a + w[k] * (b - a)
            txt, al = parts[k].strip(), win(t, seg_a - 0.08, seg_b + (0.35 if k == len(parts) - 1 else 0.02), 0.1, 0.12)
        else:
            txt, al = parts[0], win(t, a - 0.08, b + 0.35, 0.12, 0.2)
        fx.text(img, txt, W / 2, H - LB / 2 + 2, 30, al * 0.95, "mont", 400, 0.03, (0.93, 0.93, 0.93))
    return img


def overlays(img, t):
    for t0, title, sub, align, dur in LABELS:
        x = 150 if align == "l" else W - 150
        fx.label(img, t, t0, title, sub, x=x, dur=dur, size=30, align=align)
    return img


def bars(img, t):
    for a, b in RECON:
        al = win(t, a + 0.4, b - 0.3, 0.5, 0.5)
        fx.text(img, "DRAMATIZED RECONSTRUCTION", W - 70, LB / 2, 15, al * 0.55, "mont", 500, 0.3, (1, 1, 1), anchor="rm")
    return subtitles(img, t)


# ----------------------------------------------------------------------------- frame
def compose(t):
    idx = [i for i in range(len(SHOTS)) if shot_range(i)[0] <= t < shot_range(i)[1]] or [len(SHOTS) - 1]
    if len(idx) == 1:
        img = render_shot(idx[0], t)
    else:
        i, j = idx[0], idx[-1]
        xf = SHOTS[i][2]
        k = smooth((t - (SHOTS[j][0] - xf / 2)) / xf)
        img = render_shot(i, t) * (1 - k) + render_shot(j, t) * k
    # white flash into the 1967 flashback
    fl = math.exp(-((t - SC[3]) / 0.18) ** 2) * 0.9
    if fl > 0.01:
        img = img + fl * np.array((1.0, 0.92, 0.8), np.float32)
    return img


def render_frame(t):
    img = compose(t)
    img = overlays(img, t)
    img = fx.finish(img, t, bloom=0.22, vignette=0.3, grain=0.02)
    img = img * (smooth(t / 0.6) if t < 0.6 else 1.0) * (1 - smooth((t - 89.22) / 0.75))
    img = bars(img, t)
    return fx.to_u8(img)


if __name__ == "__main__":
    ts = [float(a) for a in sys.argv[1:]] or [1.6, 5.0, 8.5, 13.5, 17.5, 22.0, 26.0, 29.5, 34.0, 37.0, 39.0, 42.0,
                                              46.0, 51.0, 55.5, 59.0, 62.2, 64.5, 68.0, 71.5, 74.0, 76.5, 81.5, 88.0]
    tiles = []
    for t in ts:
        f = render_frame(t)
        f = cv2.resize(f, (480, 270), interpolation=cv2.INTER_AREA)[:, :, ::-1].copy()
        cv2.putText(f, f"{t:.1f}", (8, 22), 0, 0.6, (0, 255, 255), 1, cv2.LINE_AA)
        tiles.append(f)
        print("rendered", t, flush=True)
    while len(tiles) % 4:
        tiles.append(np.zeros_like(tiles[0]))
    sheet = np.vstack([np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)])
    cv2.imwrite(os.path.join(ROOT, "scratch", "preview.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
