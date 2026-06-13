"""Render one branded 9:16 reel — fully style-driven (no hardcoded brand).

Layout: style-pack bg.png + a card holding either a static slide (--slide) or
the source video segment (--mode clip); a serif title PNG (from gen_title.py)
overlaid at style.title.png_y; an optional LIVE webcam window cropped from the
source (--face-crop, bottom-right); burned subtitles styled from style.subtitle.

Everything geometric/colour comes from --style DIR/style.json, so swapping the
pack swaps the whole look. Build the pack with /huashu-design per user.

Usage — static slide card + live face PIP:
  python gen_title.py --style S --out title.png --line "..." --line "..."
  python render_reel.py --style S --source v.mp4 --start 60 --end 80 \
    --mode slide --slide deck/p3.png --srt clip.srt \
    --title-png title.png --face-crop 300:188:978:534 --out out.mp4
Usage — source video in the card (speaker screen-share):
  python render_reel.py --style S --source v.mp4 --start 60 --end 80 \
    --mode clip --srt clip.srt --title-png title.png --out out.mp4
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

from style import Style

FFMPEG = os.environ.get("FFMPEG", "ffmpeg")


def _ass_ts(t: str) -> str:
    h, m, rest = t.split(":")
    s, ms = rest.split(",")
    return f"{int(h)}:{m}:{s}.{int(ms)//10:02d}"


def build_sub_ass(srt_path: str, ass_path: str, st: Style) -> None:
    sub = st["subtitle"]
    cw, ch = st.canvas
    raw = Path(srt_path).read_text(encoding="utf-8-sig").strip()
    header = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {cw}\nPlayResY: {ch}\nWrapStyle: 0\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, "
        "BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV\n"
        f"Style: Sub,{sub['font']},{sub['size']},{sub['fill']},&H00000000,"
        f"{sub['box']},1,0,3,20,0,2,{sub['margin_h']},{sub['margin_h']},{sub['margin_v']}\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text\n"
    )
    lines = []
    for block in re.split(r"\n\s*\n", raw):
        rows = [r for r in block.splitlines() if r.strip()]
        tl = next((r for r in rows if "-->" in r), None)
        if not tl:
            continue
        a, b = [x.strip() for x in tl.split("-->")]
        txt = " ".join(r for r in rows if r != tl and not r.strip().isdigit())
        lines.append(f"Dialogue: 0,{_ass_ts(a)},{_ass_ts(b)},Sub,,0,0,0,,{txt}")
    Path(ass_path).write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--start", type=float, required=True)
    ap.add_argument("--end", type=float, required=True)
    ap.add_argument("--mode", choices=["slide", "clip"], default="slide")
    ap.add_argument("--slide", help="slide image (required for --mode slide)")
    ap.add_argument("--srt", required=True)
    ap.add_argument("--title-png", required=True, help="from gen_title.py")
    ap.add_argument("--face-crop", metavar="W:H:X:Y",
                    help="LIVE webcam window cropped from source -> bottom-right PIP")
    ap.add_argument("--card-crop", metavar="W:H:X:Y",
                    help="clip mode: crop source frame before scaling into card")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.mode == "slide" and not args.slide:
        ap.error("--slide required for --mode slide")

    st = Style(args.style)
    W, H = st.canvas
    card = st["card"]
    pip = st["pip"]
    dur = args.end - args.start
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    ass_dir = out.parent / ".ass_tmp"
    ass_dir.mkdir(exist_ok=True)
    ass_path = str(ass_dir / (out.stem + ".ass"))
    build_sub_ass(args.srt, ass_path, st)
    ass = ass_path.replace(":", r"\:")

    inputs = ["-loop", "1", "-i", st.bg]
    idx = 1
    if args.mode == "slide":
        inputs += ["-loop", "1", "-i", args.slide]
        card_in, idx = 1, 2
    inputs += ["-ss", f"{args.start}", "-t", f"{dur}", "-i", args.source]
    src_in = idx
    idx += 1
    inputs += ["-loop", "1", "-i", args.title_png]
    title_in = idx
    idx += 1
    if args.mode == "clip":
        card_in = src_in

    card_pre = ""
    if args.card_crop and args.mode == "clip":
        cw, ch, cx, cy = args.card_crop.split(":")
        card_pre = f"crop={cw}:{ch}:{cx}:{cy},"
    f = [
        f"[{card_in}:v]{card_pre}scale={card['w']}:-1[s]",
        f"[0:v][s]overlay={card['x']}:{card['y']}[v1]",
        f"[{title_in}:v]scale={W}:-1[t]",
        f"[v1][t]overlay=0:{st['title']['png_y']}[v2]",
    ]
    last = "v2"
    if args.face_crop:
        w, h, x, y = args.face_crop.split(":")
        bw = pip.get("border", 4)
        px = W - pip["w"] - 2 * bw - pip.get("x_from_right", 38)
        f += [
            f"[{src_in}:v]crop={w}:{h}:{x}:{y},scale={pip['w']}:-1,"
            f"pad=iw+{2*bw}:ih+{2*bw}:{bw}:{bw}:color={pip.get('border_color','white')}[face]",
            f"[{last}][face]overlay={px}:{pip['y']}[v3]",
        ]
        last = "v3"
    f.append(f"[{last}]ass='{ass}'[v]")

    cmd = [FFMPEG, "-y", *inputs, "-filter_complex", ";".join(f),
           "-map", "[v]", "-map", f"{src_in}:a", "-r", "30",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
           "-t", f"{dur}", str(out)]
    print("rendering", out, f"({dur:.0f}s)")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FFMPEG ERROR:\n", r.stderr[-1800:])
        raise SystemExit(1)
    print("done ->", out)


if __name__ == "__main__":
    main()
