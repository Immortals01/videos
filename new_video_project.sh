#!/usr/bin/env bash
# Scaffold a clean, isolated video project folder that reuses (or auto-bootstraps on a fresh
# git clone) the shared Python venv, AI models (Kokoro TTS + Depth-Anything-V2), fonts,
# textures, and generic engine code, without touching the Surveyor 3 project files.
#
# Usage:
#   ./new_video_project.sh <new_project_slug>
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <new_project_slug>"
  exit 1
fi

SLUG="$1"
BASE="$(cd "$(dirname "$0")" && pwd)"
SHARED="$BASE/production"
DEST="$BASE/projects/$SLUG"

if [ -e "$DEST" ]; then
  echo "Error: $DEST already exists."
  exit 1
fi

# 1. Auto-bootstrap shared Python venv if missing (e.g. fresh git clone on another machine)
if [ ! -x "$SHARED/.venv/bin/python" ]; then
  echo "[bootstrap] Creating shared Python virtual environment at $SHARED/.venv ..."
  if command -v uv >/dev/null 2>&1; then
    uv venv -q "$SHARED/.venv" --python 3.12 || uv venv -q "$SHARED/.venv"
    uv pip install -q --python "$SHARED/.venv/bin/python" \
      numpy pillow scipy soundfile onnxruntime kokoro-onnx opencv-python-headless gradio_client
  else
    python3 -m venv "$SHARED/.venv"
    "$SHARED/.venv/bin/pip" install -q --upgrade pip
    "$SHARED/.venv/bin/pip" install -q \
      numpy pillow scipy soundfile onnxruntime kokoro-onnx opencv-python-headless gradio_client
  fi
fi

# 2. Auto-bootstrap ONNX models (Kokoro-82M TTS + Depth-Anything-V2-small) if missing
mkdir -p "$SHARED/models"
if [ ! -s "$SHARED/models/kokoro-v1.0.onnx" ]; then
  echo "[bootstrap] Downloading kokoro-v1.0.onnx (311 MB) ..."
  curl -L --fail -o "$SHARED/models/kokoro-v1.0.onnx" \
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
fi
if [ ! -s "$SHARED/models/voices-v1.0.bin" ]; then
  echo "[bootstrap] Downloading voices-v1.0.bin (27 MB) ..."
  curl -L --fail -o "$SHARED/models/voices-v1.0.bin" \
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
fi
if [ ! -s "$SHARED/models/depth_small.onnx" ]; then
  echo "[bootstrap] Downloading depth_small.onnx (95 MB) ..."
  curl -L --fail -o "$SHARED/models/depth_small.onnx" \
    "https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model.onnx"
fi

# 3. Create isolated project directory structure
mkdir -p "$DEST/production/src" \
         "$DEST/production/plates/depth" \
         "$DEST/production/plates/inputs" \
         "$DEST/production/audio/voice" \
         "$DEST/production/audio/stems" \
         "$DEST/production/build/chunks" \
         "$DEST/production/reference" \
         "$DEST/production/scratch" \
         "$DEST/deliverables"

# 4. Symlink heavy shared read-only assets so new projects start in <1 second
ln -s "$SHARED/.venv"    "$DEST/production/.venv"
ln -s "$SHARED/models"   "$DEST/production/models"
ln -s "$SHARED/fonts"    "$DEST/production/fonts"
ln -s "$SHARED/textures" "$DEST/production/textures"

# 5. Copy reusable engine & template scripts
for f in fx.py depth.py flux.py tts.py timeline.py render.py audio.py scenes.py script_lines.py plates_batch.py thumbnail.py; do
  cp "$SHARED/src/$f" "$DEST/production/src/$f"
done

cat > "$DEST/STATE.md" <<EOF
# Video Project State: $SLUG

- **Project Root:** \`$DEST\`
- **Production Dir:** \`$DEST/production\`
- **Deliverables Dir:** \`$DEST/deliverables\`
- **Python Binary:** \`$DEST/production/.venv/bin/python\`

## Milestone Checklist
- [ ] Step 1: Clarifying questions & secrets confirmed
- [ ] Step 2: Fact-check & \`src/script_lines.py\` written
- [ ] Step 3: Voice synthesized (\`src/tts.py\`) & timeline solved (\`src/timeline.py\`)
- [ ] Step 4: Shot list planned
- [ ] Step 5: Plates generated & contact-sheet QA passed
- [ ] Step 6: Depth maps generated (\`src/depth.py\`)
- [ ] Step 7: Score & SFX synthesized (\`src/audio.py\`)
- [ ] Step 8: \`src/scenes.py\` written & 24-frame preview sheet verified
- [ ] Step 9: Detached chunk render completed & assembled (\`src/render.py\`)
- [ ] Step 10: Final MP4 verified, thumbnail embedded, docs written
EOF

echo "Created isolated video project at: $DEST"
echo "Run scripts with: $DEST/production/.venv/bin/python $DEST/production/src/<script>.py"
