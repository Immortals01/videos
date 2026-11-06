# Agent Instructions (`AGENTS.md`)

> **MANDATORY FIRST STEP FOR ANY NEW VIDEO PROJECT:**
> Read `/home/mohammed/.t3/projects/nasa/VIDEO_PRODUCTION_PLAYBOOK.md` (or `./VIDEO_PRODUCTION_PLAYBOOK.md` relative to the repo root) first. Run `./new_video_project.sh <slug>` and do all work inside `projects/<slug>/` (do **not** touch the finished Surveyor 3 files in `production/` or `deliverables/`). Delegate long waits, batch plate runs, and verification to `gemini-4-argon` via `delegate_task` to save Opus quota.

---

## 1. Project Isolation Rules
- **`production/`** and **`deliverables/`** at the root of this repository belong **exclusively** to the finished **Surveyor 3 & Opportunity 90s Cinematic Trailer (*"Abandoned, But Not Forgotten"*)**. Treat them as a **read-only archive** unless the user explicitly asks to edit the Surveyor 3 film.
- For **any new video prompt**, scaffold an isolated project folder first:
  ```bash
  ./new_video_project.sh <new_project_slug>
  ```
  This creates `projects/<new_project_slug>/{production,deliverables}`, symlinks the shared `.venv`, `models`, `fonts`, and `textures` (or sets them up if freshly cloned), copies the reusable `src/*.py` 2.5D/procedural engine scripts, and initializes `projects/<new_project_slug>/production/STATE.md`.
- Do **all** work for the new video inside `projects/<new_project_slug>/`.

## 2. Quota & Delegation Rules (Save Claude Opus Quota)
- **What the main agent (Claude Opus) does directly:**
  1. Resolve prompt contradictions (e.g., duration conflicts) and write `STATE.md`.
  2. Write creative/architectural code (`src/script_lines.py`, `src/timeline.py`, `src/scenes.py`, `src/audio.py`, `src/plates_batch.py`).
  3. Inspect visual contact sheets (`scratch/contact_all.jpg` and `scratch/final_contact.jpg`) to verify quality, anatomical accuracy, and subtitle/HUD legibility.
- **What MUST be delegated to `gemini-4-argon` via T3 `delegate_task`:**
  - Call `orchestrator_capabilities` once per thread before the first `delegate_task`.
  - Delegate batch plate generation (`src/plates_batch.py`), depth map extraction (`src/depth.py`), detached render launching + progress monitoring (`src/render.py`), `ffprobe` / EBU R128 loudness verification, contact sheet assembly, and boilerplate deliverable Markdown generation to `gemini-4-argon`.
- **Never attach long renders to your foreground tool call:** Always launch renders detached (`setsid nohup env WORKERS=4 .venv/bin/python src/render.py > scratch/render.log 2>&1 < /dev/null & disown`) so user chat messages or provider handoffs cannot kill the render.

## 3. Core Technical Rules (Summary — see `VIDEO_PRODUCTION_PLAYBOOK.md` for full details)
1. **Audio-first timeline:** Generate all Kokoro-82M TTS voice clips (`src/tts.py`) *before* locking scene boundaries in `src/timeline.py`, with a `>= 0.25s` gap between clips and `>= 0.15s` margin before scene cuts.
2. **No spacecraft anatomical hallucinations:** Never allow AI image generators to put human faces, eyes, mouths, or rover wheels on stationary landers. Use real NASA photos + `FLUX.1-Kontext-Dev` (with an authenticated free Hugging Face Read token) to lock authentic geometry across shots.
3. **Never use watermarks or paid APIs without permission:** Do not use unauthenticated Pollinations.ai (adds bottom-right watermarks and ignores structural constraints).
4. **Chunked resumable rendering:** Render in 2-second (`48`-frame) atomic chunks (`c00.mp4`..`c44.mp4`) so any fix only requires re-rendering a single 2-second chunk (`python src/render.py <chunk_id>`).
5. **Subtitle & HUD safety:** Keep lower-third location/date labels above `y = 890` with an edge-to-edge feathered dark scrim (`fx.label`), reserving `y = 955..1050` exclusively for narration subtitles (`fx.subtitle`).
