# Agent Instructions (`AGENTS.md`)

> **MANDATORY FIRST STEP FOR ANY NEW VIDEO PROJECT:**
> Read [`./VIDEO_PRODUCTION_PLAYBOOK.md`](./VIDEO_PRODUCTION_PLAYBOOK.md) first. Run `./new_video_project.sh <slug>` from the repository root and do all work inside `projects/<slug>/` (do **not** touch the finished Surveyor 3 files in `production/` or `deliverables/`). Delegate long waits, batch plate runs, and verification to a fast/cheaper subagent (e.g., `gemini-4-argon` via `delegate_task` in T3 Code, or a lightweight subagent in Claude Code / Codex / OpenCode) to save main-model quota.

---

## 1. Project Isolation & Cross-Machine Portability
- **No hardcoded machine paths:** All scripts and workflows are relative to the repository root (`$(pwd)`).
- **`production/`** and **`deliverables/`** at the root of this repository belong **exclusively** to the finished **Surveyor 3 & Opportunity 90s Cinematic Trailer (*"Abandoned, But Not Forgotten"*)**. Treat them as a **read-only archive** unless the user explicitly asks to edit the Surveyor 3 film.
- For **any new video prompt**, scaffold an isolated project folder first:
  ```bash
  ./new_video_project.sh <new_project_slug>
  ```
  - On a fresh `git clone` on any machine, `./new_video_project.sh` automatically creates `production/.venv`, installs all Python dependencies (`numpy`, `pillow`, `scipy`, `soundfile`, `onnxruntime`, `kokoro-onnx`, `opencv-python-headless`, `gradio_client`), and downloads the required ONNX models (`kokoro-v1.0.onnx`, `voices-v1.0.bin`, `depth_small.onnx`) into `production/models/` if they are not already present.
  - It then creates `projects/<new_project_slug>/{production,deliverables}`, symlinks the shared `.venv`, `models`, `fonts`, and `textures`, copies the reusable `src/*.py` 2.5D/procedural engine scripts, and initializes `projects/<new_project_slug>/STATE.md`.
- Do **all** work for the new video inside `projects/<new_project_slug>/`.

## 2. Quota & Delegation Rules (Any Harness: T3 Code, Claude Code, Codex, Cursor, OpenCode)
- **What the primary/lead agent does directly:**
  1. Resolve prompt contradictions (e.g., duration conflicts) and write `projects/<slug>/STATE.md`.
  2. Write creative/architectural code (`src/script_lines.py`, `src/timeline.py`, `src/scenes.py`, `src/audio.py`, `src/plates_batch.py`).
  3. Inspect visual contact sheets (`scratch/contact_all.jpg` and `scratch/final_contact.jpg`) to verify quality, anatomical accuracy, and subtitle/HUD legibility.
- **What SHOULD be delegated to a cheaper/faster subagent:**
  - **In T3 Code:** Call `orchestrator_capabilities` once per thread, then use `delegate_task` targeting `gemini-4-argon`.
  - **In Claude Code / Codex / other harnesses:** Use your native subagent tool (with a fast/light model tier where supported) or background task runner.
  - **Tasks to delegate:** Batch plate generation (`src/plates_batch.py`), depth map extraction (`src/depth.py`), detached render launching + progress monitoring (`src/render.py`), `ffprobe` / EBU R128 loudness verification, contact sheet assembly, and boilerplate deliverable Markdown generation.
- **Never attach long renders to your foreground tool call:** Always launch renders detached (`setsid nohup env WORKERS=4 .venv/bin/python src/render.py > scratch/render.log 2>&1 < /dev/null & disown`) so user chat messages or session timeouts cannot kill the render.

## 3. Secrets & API Tokens (Harness-Independent)
- Image generation via `src/flux.py` uses a free Hugging Face Read token stored at `~/.cache/huggingface/token` (or in the `HF_TOKEN` environment variable).
- Check if `~/.cache/huggingface/token` or `$HF_TOKEN` already exists first. If missing:
  - In **T3 Code**, call `request_secret` with `delivery: "file"` and save it to `~/.cache/huggingface/token` (`chmod 600`).
  - In **any other CLI/harness**, ask the user to set `export HF_TOKEN=...` or run `huggingface-cli login` / write `~/.cache/huggingface/token` (never commit tokens to Git).

## 4. Core Technical Rules (Summary — see `VIDEO_PRODUCTION_PLAYBOOK.md` for full details)
1. **Audio-first timeline:** Generate all Kokoro-82M TTS voice clips (`src/tts.py`) *before* locking scene boundaries in `src/timeline.py`, with a `>= 0.25s` gap between clips and `>= 0.15s` margin before scene cuts.
2. **No spacecraft anatomical hallucinations:** Never allow AI image generators to put human faces, eyes, mouths, or rover wheels on stationary landers. Use real NASA photos + `FLUX.1-Kontext-Dev` to lock authentic geometry across shots.
3. **Never use watermarks or paid APIs without permission:** Do not use unauthenticated Pollinations.ai (adds bottom-right watermarks and ignores structural constraints).
4. **Chunked resumable rendering:** Render in 2-second (`48`-frame) atomic chunks (`c00.mp4`..`c44.mp4`) so any fix only requires re-rendering a single 2-second chunk (`python src/render.py <chunk_id>`).
5. **Subtitle & HUD safety:** Keep lower-third location/date labels above `y = 890` with an edge-to-edge feathered dark scrim (`fx.label`), reserving `y = 955..1050` exclusively for narration subtitles (`fx.subtitle`).
