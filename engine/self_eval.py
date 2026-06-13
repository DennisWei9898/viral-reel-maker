"""G3 — Self-eval loop: turn the manual "交付前自我驗證" checklist into an
automated, evidence-producing gate.

Research (video-use, 2026): after render, sample frames around every cut +
the first/last frames, lay them on a contact sheet, and let the agent VISUALLY
verify against the hard rules — iterate up to 3 times. This catches the failure
modes CLAUDE.md warns about (cut mid-sentence, subtitle clipped, title-card fps
mismatch, black/flash frames) that a transcript-only check can't see.

This script produces the EVIDENCE (Claude does the seeing):
  - extracts frames at each cut point (just-before / just-after) + 0s/1s/mid
  - builds a contact sheet PNG per video
  - runs cheap deterministic checks (black frames, fps mismatch, duration)
  - writes eval_report.md with a checklist for Claude to fill from the sheet

Usage:
  python self_eval.py final.mp4 --cuts selection.json --out-dir eval/
  python self_eval.py final.mp4 --srt final.srt --out-dir eval/
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import List, Optional

from srt_io import parse_srt, fmt_ts

FFMPEG = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
FFPROBE = "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe"


def probe(path: str) -> dict:
    out = subprocess.check_output([
        FFPROBE, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,nb_read_frames:format=duration",
        "-of", "json", path,
    ], stderr=subprocess.DEVNULL)
    j = json.loads(out)
    st = j.get("streams", [{}])[0]
    num, den = (st.get("r_frame_rate", "0/1").split("/") + ["1"])[:2]
    fps = float(num) / float(den) if float(den) else 0.0
    return {
        "width": st.get("width"),
        "height": st.get("height"),
        "fps": round(fps, 3),
        "duration": float(j.get("format", {}).get("duration", 0.0)),
    }


def _grab(path: str, t: float, out_png: Path) -> bool:
    """Extract one frame at time t. -ss AFTER -i for accurate seek (CLAUDE.md)."""
    t = max(0.0, t)
    r = subprocess.run(
        [FFMPEG, "-y", "-i", path, "-ss", f"{t:.3f}", "-frames:v", "1",
         "-q:v", "3", str(out_png)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return r.returncode == 0 and out_png.exists()


def _is_black(png: Path, thresh: int = 16) -> bool:
    """Cheap black-frame check via ffmpeg signalstats avg luma."""
    try:
        out = subprocess.check_output(
            [FFMPEG, "-i", str(png), "-vf", "signalstats,metadata=print:key=lavfi.signalstats.YAVG",
             "-f", "null", "-"],
            stderr=subprocess.STDOUT, text=True,
        )
        for line in out.splitlines():
            if "YAVG" in line:
                val = float(line.split("=")[-1].strip())
                return val < thresh
    except Exception:
        pass
    return False


def cut_times_from_srt(srt: str) -> List[float]:
    entries = parse_srt(srt, drop_long=False)
    # cut points = boundaries between entries (use each entry start after the first)
    return [e.start for e in entries[1:]]


def cut_times_from_cuts(cuts_json: str) -> List[float]:
    """selection.json holds source timestamps; on a concatenated final video the
    cut points are the cumulative durations. We reconstruct them from dur."""
    data = json.loads(Path(cuts_json).read_text(encoding="utf-8"))
    times, acc = [], 0.0
    for c in data[:-1]:
        acc += float(c.get("dur", 0))
        times.append(acc)
    return times


def build_contact_sheet(frames: List[Path], out: Path, cols: int = 4) -> Optional[Path]:
    """Tile frames into one PNG. Robust method: normalize each frame to an
    identically-sized numbered file, then run ffmpeg's `tile` over the sequence
    (works for any frame count, unlike a 70-input filter_complex)."""
    frames = [f for f in frames if f.exists()]
    if not frames:
        return None
    norm_dir = out.parent / "_sheet_tmp"
    norm_dir.mkdir(parents=True, exist_ok=True)
    for old in norm_dir.glob("n_*.png"):
        old.unlink()
    for i, f in enumerate(frames):
        subprocess.run(
            [FFMPEG, "-y", "-i", str(f),
             "-vf", "scale=320:180:force_original_aspect_ratio=decrease,"
                    "pad=320:180:(ow-iw)/2:(oh-ih)/2:color=black",
             str(norm_dir / f"n_{i:03d}.png")],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    rows = (len(frames) + cols - 1) // cols
    r = subprocess.run(
        [FFMPEG, "-y", "-framerate", "1", "-i", str(norm_dir / "n_%03d.png"),
         "-vf", f"tile={cols}x{rows}:padding=4:margin=4:color=white",
         "-frames:v", "1", str(out)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return out if (r.returncode == 0 and out.exists()) else None


def main() -> None:
    ap = argparse.ArgumentParser(description="Self-eval a rendered video against hard rules")
    ap.add_argument("video")
    ap.add_argument("--cuts", help="selection.json (source clips, concatenated)")
    ap.add_argument("--srt", help="final burned-in SRT (cut points = entry edges)")
    ap.add_argument("--out-dir", default="eval")
    ap.add_argument("--expect-fps", type=float, default=30.0)
    ap.add_argument("--max-cuts", type=int, default=18,
                    help="cap sampled cut points (reel has 12-18 cuts)")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    fr_dir = out_dir / "frames"
    fr_dir.mkdir(parents=True, exist_ok=True)

    meta = probe(args.video)
    cuts: List[float] = []
    if args.cuts:
        cuts = cut_times_from_cuts(args.cuts)
    elif args.srt:
        cuts = cut_times_from_srt(args.srt)

    # self-eval targets a FINAL reel; if handed a long track, sample evenly so
    # the sheet stays readable and the run stays fast.
    if len(cuts) > args.max_cuts:
        step = len(cuts) / args.max_cuts
        cuts = [cuts[int(i * step)] for i in range(args.max_cuts)]

    # frames: 0s, 1s, each cut ±0.4s, midpoint, last-0.3s
    samples = [("start_0s", 0.0), ("hook_1s", 1.0)]
    for i, t in enumerate(cuts, 1):
        samples.append((f"cut{i}_before", t - 0.4))
        samples.append((f"cut{i}_after", t + 0.1))
    samples.append(("mid", meta["duration"] / 2))
    samples.append(("end", max(0.0, meta["duration"] - 0.3)))

    frame_paths, black_hits = [], []
    for name, t in samples:
        png = fr_dir / f"{name}.png"
        if _grab(args.video, t, png):
            frame_paths.append(png)
            if _is_black(png):
                black_hits.append(name)

    sheet = build_contact_sheet(frame_paths, out_dir / "contact_sheet.png")

    # deterministic verdicts
    fps_ok = abs(meta["fps"] - args.expect_fps) < 0.5
    ar = (meta["width"] / meta["height"]) if meta["height"] else 0
    orient = "9:16" if ar < 0.75 else ("16:9" if ar > 1.5 else f"{ar:.2f}")

    report = [
        "# self-eval 報告（Claude 看 contact_sheet.png 後填勾選）", "",
        f"- 影片：`{args.video}`",
        f"- 解析度：{meta['width']}×{meta['height']}  ({orient})",
        f"- fps：{meta['fps']}  →  {'✅ 符合' if fps_ok else '❌ 與預期 '+str(args.expect_fps)+' 不符（concat 可能壓成 0 秒！）'}",
        f"- 總長：{meta['duration']:.1f}s  ({'✅ 15-25s reel' if 13 <= meta['duration'] <= 27 else '⚠ 非典型 reel 長度'})",
        f"- 切點數：{len(cuts)}",
        f"- 黑/閃幀偵測：{('❌ '+', '.join(black_hits)) if black_hits else '✅ 無'}",
        "",
        f"contact sheet：`{sheet}`" if sheet else "⚠ contact sheet 產生失敗，請逐張看 frames/",
        "", "---", "",
        "## 人工/Claude 視覺檢查清單（對照 CLAUDE.md 硬規則）",
        "看 contact_sheet.png，逐項勾：", "",
        "- [ ] 每個 `cutN_before` 沒有斷在句中（字幕是完整語意結尾）",
        "- [ ] 每個 `cutN_after` 開頭不是半句",
        "- [ ] `start_0s` / `hook_1s` 第一幀就有文字、人臉/主體已入鏡",
        "- [ ] 所有幀字幕沒有被切掉、對比足夠（白字+黑邊可讀）",
        "- [ ] 無突兀黑幀 / 閃幀 / title card 壓成 0 秒",
        "- [ ] 字幕在安全區 y=15%-65%，每行 ≤ 4 詞",
        "",
        "## 判定",
        "- 全部勾 → PASS，可交付",
        "- 有未勾 → 列出問題切點，回 pipeline 修正，重跑 self_eval（≤3 次）",
    ]
    (out_dir / "eval_report.md").write_text("\n".join(report), encoding="utf-8")

    print(f"self-eval: {len(frame_paths)} frames, fps={'OK' if fps_ok else 'BAD'}, "
          f"black={len(black_hits)}, sheet={'OK' if sheet else 'FAIL'}")
    print(f"  -> {out_dir/'eval_report.md'}")
    print(f"  -> {sheet if sheet else fr_dir}")
    if not fps_ok or black_hits:
        print("  ⚠ deterministic checks flagged issues — see report")


if __name__ == "__main__":
    main()
