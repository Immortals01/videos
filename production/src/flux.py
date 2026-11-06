"""Free image generation via public Hugging Face FLUX spaces (no key, no credits).
Usage:
  python src/flux.py schnell <out.jpg> "<prompt>" [seed]
  python src/flux.py kontext <out.jpg> <ref.jpg> "<prompt>" [seed]
"""
import shutil, sys, time
from gradio_client import Client, handle_file

import os
mode, out = sys.argv[1], sys.argv[2]
t = time.time()
tok_path = os.path.expanduser("~/.cache/huggingface/token")
TOKEN = os.environ.get("HF_TOKEN") or (open(tok_path).read().strip() if os.path.exists(tok_path) else None)
STEPS = int(os.environ.get("KSTEPS", "24"))
if mode == "schnell":
    prompt = sys.argv[3]
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    c = Client("black-forest-labs/FLUX.1-schnell", token=TOKEN, verbose=False)
    res, s = c.predict(prompt, seed, seed == 0, 1360, 768, 4, api_name="/infer")
else:
    ref, prompt = sys.argv[3], sys.argv[4]
    seed = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    c = Client("black-forest-labs/FLUX.1-Kontext-Dev", token=TOKEN, verbose=False)
    res, s = c.predict(handle_file(ref), prompt, seed, seed == 0, 2.5, STEPS, api_name="/infer")
path = res["path"] if isinstance(res, dict) else res
shutil.copy(path, out)
print("OK", out, "seed", s, f"{time.time()-t:.1f}s")
