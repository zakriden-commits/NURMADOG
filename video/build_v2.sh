#!/usr/bin/env bash
# v2 pipeline: voice-over -> SFX only (no music) -> frames -> muxed mp4
set -euo pipefail
cd "$(dirname "$0")"
FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")

python3 voice.py                 # narration timeline (timer -> audio/timeline.json)
python3 audio2.py                # voice + soft cinematic SFX, no music  -> audio/mix2.wav
python3 render2.py               # 1080x1920@30 frames                 -> out/video_v2.mp4
"$FF" -v error -y -i out/video_v2.mp4 -i audio/mix2.wav \
  -map 0:v -map 1:a -c:v libx264 -preset slow -crf 21 -pix_fmt yuv420p \
  -c:a aac -b:a 192k -shortest -movflags +faststart out/sasny_mma_v2_30s.mp4
echo "done -> out/sasny_mma_v2_30s.mp4"
