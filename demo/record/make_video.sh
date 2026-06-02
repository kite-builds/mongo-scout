#!/usr/bin/env bash
# Record the narrated mongo-scout demo and render it to GIF + MP4.
# Deterministic, no key, no account. Requires: asciinema, agg, ffmpeg, node.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="$here/../media"
mkdir -p "$out"

cast="$out/demo.cast"
gif="$out/mongo-scout-demo.gif"
mp4="$out/mongo-scout-demo.mp4"

echo "[1/3] recording terminal session…"
export TERM="${TERM:-xterm-256color}"
asciinema rec --overwrite --cols 100 --rows 34 \
  -c "bash '$here/play.sh'" "$cast"

echo "[2/3] rendering GIF (agg)…"
agg --theme monokai --font-size 18 --speed 1.0 "$cast" "$gif"

echo "[3/3] transcoding GIF -> MP4 (ffmpeg, yuv420p for broad compatibility)…"
ffmpeg -y -loglevel error -i "$gif" \
  -movflags +faststart -pix_fmt yuv420p \
  -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" "$mp4"

echo "done:"
ls -lh "$cast" "$gif" "$mp4"
