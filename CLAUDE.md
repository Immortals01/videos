# Claude Code Instructions (`CLAUDE.md`)

See [`./AGENTS.md`](./AGENTS.md) and [`./VIDEO_PRODUCTION_PLAYBOOK.md`](./VIDEO_PRODUCTION_PLAYBOOK.md) for the complete, mandatory workflow before creating or editing any files in this repository.

1. Read [`./AGENTS.md`](./AGENTS.md) and [`./VIDEO_PRODUCTION_PLAYBOOK.md`](./VIDEO_PRODUCTION_PLAYBOOK.md) first.
2. Run `./new_video_project.sh <slug>` and do all work inside `projects/<slug>/` (do **not** modify `production/` or `deliverables/`, which belong to the finished Surveyor 3 trailer).
3. Delegate routine/long-running tasks (batch plates, depth maps, detached render monitoring, `ffprobe` checks, report writing) to a fast/lightweight subagent to conserve main-model quota.
