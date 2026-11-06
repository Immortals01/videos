"""Render the film: frames -> H.264 chunks (parallel) -> concat -> mux with loudness-normalised mix.

  python src/render.py            # render missing chunks, then assemble
  python src/render.py --force    # re-render everything
  python src/render.py --assemble # only (re)assemble from existing chunks + audio
"""
import os, sys, subprocess, json, time
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CH = os.path.join(ROOT, "build", "chunks")
OUTDIR = os.path.join(ROOT, "..", "deliverables")
FPS = 24
DURATION = 90.0
NF = int(round(DURATION * FPS))
CHUNK = 48
WORKERS = int(os.environ.get("WORKERS", "4"))


def chunk_path(i):
    return os.path.join(CH, f"c{i:03d}.mp4")


def render_chunk(i):
    import numpy as np
    import scenes
    a, b = i * CHUNK, min(NF, (i + 1) * CHUNK)
    tmp = chunk_path(i) + ".part.mp4"
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-tune", "film",
           "-pix_fmt", "yuv420p", "-threads", "1", "-x264-params", "keyint=48:min-keyint=48:scenecut=0",
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", tmp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for f in range(a, b):
        p.stdin.write(scenes.render_frame(f / FPS).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f"ffmpeg failed on chunk {i}")
    os.replace(tmp, chunk_path(i))
    return i, b - a, time.time() - t0


def run(cmd):
    print("+", " ".join(cmd)[:200], flush=True)
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def assemble():
    os.makedirs(OUTDIR, exist_ok=True)
    n = (NF + CHUNK - 1) // CHUNK
    lst = os.path.join(CH, "list.txt")
    with open(lst, "w") as f:
        for i in range(n):
            f.write(f"file '{chunk_path(i)}'\n")
    video = os.path.join(ROOT, "build", "video_only.mp4")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video])
    # two-pass EBU R128 loudness normalisation of the mix (-16 LUFS, -1.5 dBTP; web/festival friendly)
    pre = os.path.join(ROOT, "audio", "mix_premaster.wav")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", pre, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    js = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    print("measured:", {k: js[k] for k in ("input_i", "input_tp", "input_lra")})
    af = (f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
          f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
    mix = os.path.join(ROOT, "audio", "mix_final.wav")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", pre, "-af", af + ",aresample=48000", "-c:a", "pcm_s24le", mix])
    final = os.path.join(OUTDIR, "Abandoned_But_Not_Forgotten_90s_1080p.mp4")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", mix, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-t", f"{DURATION:.3f}", "-movflags", "+faststart",
         "-metadata", "title=Abandoned, But Not Forgotten", final])
    print("wrote", os.path.abspath(final))


def main():
    os.makedirs(CH, exist_ok=True)
    force = "--force" in sys.argv
    if "--assemble" not in sys.argv:
        n = (NF + CHUNK - 1) // CHUNK
        todo = [i for i in range(n) if force or not os.path.exists(chunk_path(i))]
        only = [a for a in sys.argv[1:] if a.isdigit()]
        if only:
            todo = [int(a) for a in only]
        print(f"rendering {len(todo)} chunks with {WORKERS} workers", flush=True)
        t0 = time.time()
        with Pool(WORKERS, maxtasksperchild=4) as pool:
            for i, nfr, dt in pool.imap_unordered(render_chunk, todo):
                print(f"chunk {i:3d}  {nfr} frames  {dt / nfr:.2f}s/frame  elapsed {time.time() - t0:.0f}s", flush=True)
    assemble()


if __name__ == "__main__":
    main()
