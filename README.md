<img src="assets/icon.svg" width="64" height="64" alt="">

# NASA Video Production Workspace

> **FOR AI AGENTS — READ THIS FIRST BEFORE CREATING OR EDITING FILES:**
> 1. **Read [`VIDEO_PRODUCTION_PLAYBOOK.md`](./VIDEO_PRODUCTION_PLAYBOOK.md)** before starting any new video project. It documents the complete reusable 2.5D/procedural animation engine, free AI asset pipeline, delegation rules, and every pitfall to avoid.
> 2. **DO NOT confuse existing project folders with your new project:**
>    - **`production/`** and **`deliverables/`** belong **exclusively** to the finished **Surveyor 3 & Opportunity Cinematic Trailer (*"Abandoned, But Not Forgotten"*)**. Do **not** overwrite, delete, or mix new project plates/audio/chunks into `production/` or `deliverables/`.
>    - You **may** reuse the shared Python virtual environment (`production/.venv/bin/python`), AI weights (`production/models/`), fonts (`production/fonts/`), and planetary textures (`production/textures/`), and you **should** copy generic engine scripts (`fx.py`, `depth.py`, `flux.py`, `tts.py`, `timeline.py`, `audio.py`, `render.py`) from `production/src/` into your new project's folder.
> 3. **Where to put a new video project:** Create a dedicated, self-contained folder under **`projects/<new_project_slug>/`** (with its own `production/` and `deliverables/` subdirectories), or work in the new repository if the user opened a separate project.

---

## Workspace Directory Map

| Path | Owner / Purpose | Agent Rule |
| :--- | :--- | :--- |
| [`VIDEO_PRODUCTION_PLAYBOOK.md`](./VIDEO_PRODUCTION_PLAYBOOK.md) | **Master Agent Playbook** — architecture, reusable code map, 19 lessons learned, and workflow | **Read first** on every new video task |
| [`deliverables/`](./deliverables/) | **Finished Project 1 Outputs** (*"Abandoned, But Not Forgotten"* — Surveyor 3 & Opportunity 90s 1080p24 MP4, thumbnails, script, and reports) | **Read-only archive** — do not overwrite |
| [`production/`](./production/) | **Finished Project 1 Source & Shared Runtime** (`src/`, `plates/`, `audio/`, `build/` for Surveyor 3 + shared `.venv/`, `models/`, `fonts/`, `textures/`) | **Read-only for Project 1 assets**; reuse `.venv/`, `models/`, `fonts/`, `textures/`, and copy engine scripts from `src/` |
| `projects/<new_slug>/` | **Future Video Projects** (create one folder per new video prompt) | **Write all new video projects here** |
