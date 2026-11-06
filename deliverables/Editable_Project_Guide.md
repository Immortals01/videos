# ABANDONED, BUT NOT FORGOTTEN — Editable Project & Asset Package Guide

Because this film was produced through a deterministic, code-driven Python/OpenCV/NumPy/FFmpeg compositor rather than a closed cloud editor, **the `production/` directory is the complete, non-destructive editable project file** (Deliverable 2), and contains every generated plate, depth map, voice clip, music/SFX stem, and reference image (Deliverable 3).

---

## 1. Directory & Asset Inventory

```text
nasa/
├── deliverables/
│   ├── Abandoned_But_Not_Forgotten_90s_1080p.mp4   # DELIVERABLE 1: Final 90.000s 1080p24 H.264/AAC film
│   ├── Editable_Project_Guide.md                   # DELIVERABLE 2: Editable project documentation
│   ├── Script_and_Timestamps.md                    # DELIVERABLE 4: Complete timestamped English script
│   └── Production_and_Historical_Report.md         # DELIVERABLE 5: Provenance & NASA accuracy report
└── production/                                     # Editable source project + all raw/rendered assets
    ├── src/
    │   ├── script_lines.py    # All 31 narration lines (TTS spelling + subtitle formatting)
    │   ├── timeline.py        # Master 90.000s dialogue-locked timeline & scene cut calculator
    │   ├── tts.py             # Local Kokoro-82M character voice generator -> audio/voice/*.wav
    │   ├── audio.py           # Procedural orchestral score, SFX, ambience, ducking & stem mixer
    │   ├── fx.py              # 2.5D depth-parallax camera rig, 3D spheres, stars, dust, LUT grades, type
    │   ├── scenes.py          # 23-shot storyboard/compositor, mechanical warps, labels & subtitles
    │   ├── depth.py           # Depth-Anything-V2 ONNX depth-map generator -> plates/depth/*.npy
    │   ├── plates_batch.py    # Reference-locked FLUX.1 Kontext shot plate definitions
    │   └── render.py          # Multi-worker 1080p24 x264 chunk renderer + EBU R128 loudness muxer
    ├── plates/                # DELIVERABLE 3 (Visuals): 17 16:9 3D-style character & environment plates
    │   ├── p_hero.jpg, p_camera.jpg, p_lowangle.jpg, p_space.jpg
    │   ├── k_camera_front.jpg, k_launch.jpg, k_cruise.jpg, k_descent.jpg, k_touchdown.jpg, k_scoop.jpg
    │   ├── k_apollo_wide.jpg, k_apollo_examine.jpg, k_apollo_beside.jpg
    │   ├── k_opp_hero.jpg, k_opp_arm.jpg, k_opp_storm.jpg, k_opp_sunset.jpg
    │   ├── depth/             # 17 dense float32 depth maps (.npy) + visual previews (.png)
    │   └── inputs/            # Pre-cropped NASA archival/concept inputs for restyled plates
    ├── textures/              # Planetary maps: moon_2k.tif (NASA LRO), mars_2k.jpg, earth_2k.jpg
    ├── reference/             # Official NASA archival reference photos (Apollo 12, Surveyor 3, MER)
    ├── audio/                 # DELIVERABLE 3 (Audio): Full voice, stems, and master mixes
    │   ├── voice/             # 31 individual 24 kHz WAV dialogue lines (s1_01.wav .. s7_05.wav)
    │   ├── stems/             # Separate 48 kHz stereo stems: voice.wav, music.wav, sfx.wav, ambience.wav
    │   ├── mix_premaster.wav  # 48 kHz float stereo pre-master mix
    │   └── mix_final.wav      # EBU R128 loudness-normalized (-16 LUFS, -1.5 dBTP) 24-bit master
    └── build/
        ├── chunks/            # 45 lossless-grade CRF 16 2-second video chunks (c000.mp4 .. c044.mp4)
        └── video_only.mp4     # Concatenated 90.000s 1080p24 video master
```

---

## 2. How to Edit & Re-Render Any Part of the Film

Activate the self-contained Python 3.12 virtual environment inside `production/`:

```bash
cd /home/mohammed/.t3/projects/nasa/production
source .venv/bin/activate
```

### Edit Dialogue or Subtitles
1. Edit text or subtitle line breaks (`|`) in `src/script_lines.py`.
2. Re-synthesize only the changed line(s), e.g.:
   ```bash
   python src/tts.py s2_03
   ```
3. Inspect updated scene/line timings:
   ```bash
   python src/timeline.py
   ```

### Edit Score, Sound Effects, or Mix Balance
1. Edit instruments, chord voicings, SFX placement, or stem levels in `src/audio.py`.
2. Rebuild all 48 kHz stems (`audio/stems/{voice,music,sfx,ambience}.wav`) and `audio/mix_premaster.wav`:
   ```bash
   python src/audio.py
   ```
3. Re-mux with existing video chunks in seconds (no video re-render needed):
   ```bash
   python src/render.py --assemble
   ```

### Edit Camera Moves, Grades, Motion Graphics, or Titles
1. Edit any shot function (`s1_space` … `s7_title`) or `LABELS` in `src/scenes.py`, or color-grading LUTs (`GRADES`) in `src/fx.py`.
2. Preview specific timestamps rapidly to `scratch/preview.jpg`:
   ```bash
   python src/scenes.py 8.5 29.5 59.0 81.5 88.2
   ```
3. Re-render only the affected 2-second chunk(s) (each chunk `i` covers `[2*i, 2*(i+1))` seconds) and re-assemble:
   ```bash
   python src/render.py 40 41 42 43 44
   ```
   Or re-render all 2,160 frames from scratch:
   ```bash
   WORKERS=4 python src/render.py --force
   ```
