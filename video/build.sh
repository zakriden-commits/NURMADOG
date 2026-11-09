#!/usr/bin/env bash
# Full pipeline: voice-over timeline -> sound design -> frames -> muxed mp4
set -euo pipefail
cd "$(dirname "$0")"

FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")

echo "== 1/4 voice-over"
python3 voice.py
echo "== 2/4 sound design"
python3 audio.py
echo "== 3/4 frames"
python3 render.py
echo "== 4/4 mux"
"$FF" -v error -y -i ../out/video_only.mp4 -i ../audio/mix.wav \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart \
  ../out/sasny_mma_30s.mp4
python3 - <<'PY'
import imageio_ffmpeg, subprocess
FF = imageio_ffmpeg.get_ffmpeg_exe()
print(subprocess.run([FF, "-i", "../out/sasny_mma_30s.mp4"], capture_output=True, text=True).stderr.split("\n")[0:3])
PY
echo "done -> out/sasny_mma_30s.mp4"
