"""Publish-metadata scaffolder — the runnable half of the publish workflow.

Given a finished reel's subtitles + title, it (1) extracts the spoken keywords
and a quotable line, then (2) emits a per-platform `publish.md` worksheet pre-
seeded with those, plus the checklist from publish_kit.md. The agent then writes
the final titles/captions into it using publish_kit.md's 3-layer rules (platform
search SEO / GEO / social algorithm).

Usage:
  python publish_meta.py --srt clip.srt --title "我讓效率提高60%｜卻被PIP" \
    --platforms ig,tiktok,youtube,fb --out publish_clientA.md
"""
from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

import jieba

from srt_io import parse_srt
from texttiling_segmenter import _STOP, _PUNCT_RE

PLATFORMS = {
    "ig":      "Instagram Reels",
    "tiktok":  "TikTok",
    "youtube": "YouTube Shorts",
    "fb":      "Facebook",
}


def keywords(text: str, n: int = 12) -> list[str]:
    c = Counter()
    for t in jieba.cut(text):
        t = t.strip().lower()
        if not t or _PUNCT_RE.fullmatch(t) or t in _STOP:
            continue
        if len(t) == 1 and t.isascii():
            continue
        if len(t) < 2 and not t.isascii():
            continue
        c[t] += 1
    return [w for w, _ in c.most_common(n)]


def longest_line(srt: str) -> str:
    entries = parse_srt(srt, drop_long=False)
    if not entries:
        return ""
    return max((e.text for e in entries), key=len)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--srt", required=True, help="the clip's subtitle file")
    ap.add_argument("--title", default="", help="the on-screen title (for reference)")
    ap.add_argument("--platforms", default="ig,tiktok,youtube,fb")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    full = " ".join(e.text for e in parse_srt(args.srt, drop_long=False))
    kws = keywords(full)
    quote = longest_line(args.srt)
    plats = [p.strip() for p in args.platforms.split(",") if p.strip() in PLATFORMS]

    L = [
        f"# 發佈 metadata 工作表",
        "",
        f"- 影片標題（畫面上）：{args.title or '—'}",
        f"- 抽出的內容關鍵字（依出現頻率）：{', '.join(kws) or '—'}",
        f"- 可引用金句（最長句）：「{quote}」" if quote else "",
        "",
        "> 規則見 `publish_kit.md`：三層（平台搜尋 SEO ／ GEO 被 AI 引用 ／ 社群演算法）。",
        "> 關鍵字塞進每個平台的「前 1-2 行 + hashtag」；caption 第一行是社群 hook；",
        "> 把影片重點寫成文字（AI 讀文字不讀影像）；CTA 用留言關鍵字/存起來。",
        "",
        "---",
    ]
    for p in plats:
        L += [
            f"\n## {PLATFORMS[p]}",
            "",
            "- **標題 / 第一行 hook**：",
            "- **Caption 內文**（前 125 字含關鍵字 + 把重點寫成文字 + CTA）：",
            "- **Hashtags**（3-5 個精準 + 1-2 個大流量；用上面的關鍵字）：",
            "- **首則留言**（放連結/補充關鍵字，避免 caption 被連結降權）：",
            "- **Alt text / 無障礙描述**（含關鍵字，平台與 Google 都讀）：" if p in ("ig", "fb") else "- **字幕檔 / 逐字稿**（YouTube 上傳 .srt；TikTok 開字幕）：",
        ]
    L += ["", "---", "",
          "## 發佈後（GEO 飛輪）",
          "- 把這支的重點濃縮成一段 80-120 字文字貼文（FB/Threads/部落格），讓 AI 引擎讀得到（影像它讀不到）。",
          "- 追蹤：平台站內搜尋曝光、Google video 收錄、AI 引擎是否提及/引用品牌。"]

    Path(args.out).write_text("\n".join(x for x in L if x is not None), encoding="utf-8")
    print(f"publish worksheet -> {args.out}")
    print(f"  keywords: {', '.join(kws[:8])}")


if __name__ == "__main__":
    main()
