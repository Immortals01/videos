<img src="assets/icon.svg" width="64" height="64" alt="">

# NASA Video Production Workspace

> **FOR AI AGENTS — READ THIS FIRST BEFORE CREATING OR EDITING FILES (also in [`AGENTS.md`](./AGENTS.md)):**
> *Read [`./VIDEO_PRODUCTION_PLAYBOOK.md`](./VIDEO_PRODUCTION_PLAYBOOK.md) first. Run `./new_video_project.sh <slug>` and do all work inside `projects/<slug>/` (do not touch the finished Surveyor 3 files in `production/` or `deliverables/`). Delegate long waits, batch plate runs, and verification to a cheaper/faster subagent (`gemini-4-argon` via `delegate_task` in T3 Code, or native subagents in Claude Code / Codex / OpenCode) to save main-model quota.*
>
> 1. **Read [`VIDEO_PRODUCTION_PLAYBOOK.md`](./VIDEO_PRODUCTION_PLAYBOOK.md)** before starting any new video project. It documents the complete reusable 2.5D/procedural animation engine, free AI asset pipeline, delegation rules, and every pitfall to avoid.
> 2. **DO NOT confuse existing project folders with your new project:**
>    - **`production/`** and **`deliverables/`** belong **exclusively** to the finished **Surveyor 3 & Opportunity Cinematic Trailer (*"Abandoned, But Not Forgotten"*)**. Do **not** overwrite, delete, or mix new project plates/audio/chunks into `production/` or `deliverables/`.
>    - You **may** reuse the shared Python virtual environment (`production/.venv/bin/python`), AI weights (`production/models/`), fonts (`production/fonts/`), and planetary textures (`production/textures/`), and `./new_video_project.sh <slug>` automatically bootstraps/symlinks those and copies the reusable `src/*.py` engine scripts into `projects/<slug>/`.
> 3. **Where to put a new video project:** Run `./new_video_project.sh <new_project_slug>` and do all work inside **`projects/<new_project_slug>/`**.

---

## Workspace Directory Map

| Path | Owner / Purpose | Agent Rule |
| :--- | :--- | :--- |
| [`VIDEO_PRODUCTION_PLAYBOOK.md`](./VIDEO_PRODUCTION_PLAYBOOK.md) | **Master Agent Playbook** — architecture, reusable code map, 19 lessons learned, and workflow | **Read first** on every new video task |
| [`deliverables/`](./deliverables/) | **Finished Project 1 Outputs** (*"Abandoned, But Not Forgotten"* — Surveyor 3 & Opportunity 90s 1080p24 MP4, thumbnails, script, and reports) | **Read-only archive** — do not overwrite |
| [`production/`](./production/) | **Finished Project 1 Source & Shared Runtime** (`src/`, `plates/`, `audio/`, `build/` for Surveyor 3 + shared `.venv/`, `models/`, `fonts/`, `textures/`) | **Read-only for Project 1 assets**; reuse `.venv/`, `models/`, `fonts/`, `textures/`, and copy engine scripts from `src/` |
| `projects/<new_slug>/` | **Future Video Projects** (create one folder per new video prompt) | **Write all new video projects here** |
