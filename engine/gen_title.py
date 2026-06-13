"""Generate a reel title as a transparent PNG (serif headline) — style-driven.

Emphasis markup (in --line):
  ==word==  -> word on a highlight box (highlight_bg / highlight_fg)
  **word**  -> word in the accent red colour
  rest      -> base colour serif

All fonts/colours come from a style pack (--style DIR/style.json), so the
output carries the USER's brand, never the engine's. Series badge via --series.

Usage:
  python gen_title.py --style styles/default --out title.png \
    --series "我的系列｜EP.2" \
    --line "第一行 **紅字**" --line "第二行 ==高光詞==？"
"""
from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from pathlib import Path

from style import Style

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def markup(line: str) -> str:
    line = re.sub(r"==(.+?)==", r'<b class="hl">\1</b>', line)
    line = re.sub(r"\*\*(.+?)\*\*", r'<b class="red">\1</b>', line)
    return line


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", required=True, help="style pack dir (has style.json)")
    ap.add_argument("--line", action="append", required=True)
    ap.add_argument("--series", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, help="override title font px")
    args = ap.parse_args()

    t = Style(args.style)["title"]
    size = args.size or t.get("size", 92)
    series_html = (f"<div class='series'>{args.series}</div>" if args.series else "")
    lines_html = series_html + "".join(f"<div class='ln'>{markup(l)}</div>" for l in args.line)

    html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'><style>
      html,body{{margin:0;background:transparent}}
      .wrap{{width:{t.get('wrap_w',1080)}px;padding:30px 70px;box-sizing:border-box;
        font-family:{t['font']};font-weight:700;text-align:center}}
      .ln{{font-size:{size}px;line-height:1.42;color:{t['base_color']};
        letter-spacing:.01em;white-space:nowrap}}
      .hl{{background:{t['highlight_bg']};color:{t['highlight_fg']};
        padding:.02em .22em;border-radius:6px;box-decoration-break:clone}}
      .red{{color:{t['red']}}}
      .series{{font-size:{round(size*0.43)}px;color:{t['series_color']};
        letter-spacing:.28em;margin-bottom:14px;font-weight:700}}
    </style></head><body><div class='wrap'>{lines_html}</div></body></html>"""

    with tempfile.TemporaryDirectory() as td:
        hp = Path(td) / "t.html"
        hp.write_text(html, encoding="utf-8")
        out = Path(args.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            CHROME, "--headless", "--disable-gpu", "--force-device-scale-factor=1",
            "--default-background-color=00000000",
            f"--screenshot={out}", "--window-size=1080,460", f"file://{hp}",
        ], capture_output=True)
    print("title ->", args.out)


if __name__ == "__main__":
    main()
