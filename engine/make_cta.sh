#!/bin/bash
# Build a 3s CTA end card from the style pack (float-up ease-out cubic).
# Usage: ./make_cta.sh <style_dir> [out.mp4]
# CTA text comes from style.json cta{line1,line2}. Audio: silent stereo matched
# to your source (default 44100 — ffprobe your source & edit if different).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"   # engine/ — where gen_title.py lives
FF="${FFMPEG:-ffmpeg}"
STYLE="${1:?usage: make_cta.sh <style_dir> [out.mp4]}"
OUT="${2:-$STYLE/cta_end.mp4}"

L1=$(python3 -c "import json;print(json.load(open('$STYLE/style.json'))['cta']['line1'])")
L2=$(python3 -c "import json;print(json.load(open('$STYLE/style.json'))['cta']['line2'])")
SZ=$(python3 -c "import json;print(json.load(open('$STYLE/style.json'))['cta'].get('size',84))")

python3 "$HERE/gen_title.py" --style "$STYLE" --out "$STYLE/.cta_text.png" --size "$SZ" \
  --line "$L1" --line "$L2"

# CTA bg = the pack's bg.png without the card (regen a card-less copy once)
if [ ! -f "$STYLE/.cta_bg.png" ]; then
  python3 - "$STYLE" << 'PY'
import sys,re,pathlib
d=pathlib.Path(sys.argv[1])
html=(d/"bg.html").read_text(encoding="utf-8")
html=re.sub(r'<div class="card"></div>','',html)
(pathlib.Path("/tmp/_cta_bg.html")).write_text(html,encoding="utf-8")
PY
  npx --no-install playwright screenshot --viewport-size=1080,1920 \
    "file:///tmp/_cta_bg.html" "$STYLE/.cta_bg.png" >/dev/null 2>&1
fi

"$FF" -y -loop 1 -t 3 -i "$STYLE/.cta_bg.png" -loop 1 -t 3 -i "$STYLE/.cta_text.png" \
  -f lavfi -t 3 -i "anullsrc=channel_layout=stereo:sample_rate=44100" \
  -filter_complex "[1:v]format=rgba,fade=t=in:st=0:d=0.5:alpha=1[txt];\
[0:v][txt]overlay=0:'880-120*(1-pow(1-min(t/0.7,1),3))'[v]" \
  -map "[v]" -map 2:a -r 30 -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 160k -t 3 "$OUT"
echo "CTA -> $OUT"
