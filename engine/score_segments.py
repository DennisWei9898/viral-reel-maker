"""G1 — Viral candidate scoring orchestration.

Flow (text-first, "Claude is the scoring LLM" = zero API cost):

  1. TextTiling segments the SRT (G4).
  2. We compute DETERMINISTIC heuristic features per segment (hook markers,
     question/answer presence, numbers, quotability, filler density, speech
     rate). These give a transparent pre-rank + a fallback score.
  3. We emit:
       - candidates.json        all segments + features + heuristic_score
       - candidates_packed.md   Claude's scoring worksheet (full text + rubric ref)
  4. Claude reads candidates_packed.md + viral_scorer.md, writes
     candidates_scored.json (8-dim rubric scores).
  5. `--finalize candidates_scored.json` merges rubric scores and produces the
     ranked candidates.md checklist (AutoCut-style, human-overridable) +
     selection.json (top-N, ready for v1/v2 to cut).

The heuristic is intentionally simple and explainable — it pre-ranks so the
best segments sit at the top of the worksheet, and it stands in if no LLM pass
happens. The real ranking is the rubric.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import List

import jieba

from srt_io import Segment, parse_srt, fmt_ts
from texttiling_segmenter import segment as texttile, tokenize, _STOP

# --- heuristic feature markers ---------------------------------------------
_QUESTION_RE = re.compile(r"[？?]|嗎|呢|為什麼|為何|怎麼|怎樣|如何|難道|是不是|有沒有|什麼是")
_NUMBER_RE = re.compile(r"\d|[一二三四五六七八九十兩幾]+\s*(個|種|招|步|點|件|招式|步驟|方法|原則|秘訣|重點)")
_HOOK_MARKERS = [
    "其實", "你知道", "你以為", "大多數", "99%", "很多人", "千萬", "別再", "不要再",
    "最大的", "關鍵", "真相", "祕密", "秘密", "重點是", "問題在", "我才發現", "後來才",
    "結果", "沒想到", "竟然", "居然", "錯了", "誤會", "迷思", "終於", "原來",
]
_CONTRARIAN = ["但是", "可是", "然而", "其實不", "並不是", "不是", "反而", "錯"]
# fillers that hurt silent readability (mirror of the editing-rule filler set)
_FILLER = set("嗯 呃 啊 喔 欸 那個 就是 然後 這個 那 對 對啊 的話 一個 一些 其實啦".split())


def _heuristic_features(seg: Segment) -> dict:
    text = seg.text
    toks = list(jieba.cut(text))
    content_toks = [t for t in toks if t.strip() and t not in _STOP and len(t.strip()) > 0]
    n_tok = max(1, len([t for t in toks if t.strip()]))

    first_sentence = re.split(r"[。！？!?，,]", text.strip(), maxsplit=1)[0][:30]

    has_question = bool(_QUESTION_RE.search(text))
    # crude "answer present": a question marker followed later by a resolution cue
    answer_cues = ["因為", "所以", "答案", "就是要", "你可以", "建議", "解法", "方法是", "就是說", "其實是"]
    has_answer = any(c in text for c in answer_cues)
    has_number = bool(_NUMBER_RE.search(text))
    hook_hits = sum(1 for m in _HOOK_MARKERS if m in text)
    contrarian = any(c in text for c in _CONTRARIAN)
    filler_hits = sum(1 for t in toks if t.strip() in _FILLER)
    filler_density = filler_hits / n_tok

    chars = len(re.sub(r"\s", "", text))
    speech_rate = chars / max(1.0, seg.dur)  # chars per second

    return {
        "first_sentence": first_sentence,
        "has_question": has_question,
        "has_answer_cue": has_answer,
        "qa_complete": has_question and has_answer,
        "has_number": has_number,
        "hook_hits": hook_hits,
        "contrarian": contrarian,
        "filler_density": round(filler_density, 3),
        "speech_rate": round(speech_rate, 2),
        "char_count": chars,
    }


def _heuristic_score(f: dict, seg: Segment) -> float:
    """Transparent 0-100 pre-rank. Mirrors rubric weighting at a coarse level."""
    s = 0.0
    # D1 hook: marker hits in first slice + contrarian opener
    s += min(20, f["hook_hits"] * 7)
    if f["contrarian"]:
        s += 6
    # D2 curiosity gap with payoff
    if f["qa_complete"]:
        s += 16
    elif f["has_question"]:
        s += 6
    # D4 concrete value
    if f["has_number"]:
        s += 12
    # D6 silent readability: penalize filler
    s += max(0, 14 - f["filler_density"] * 120)
    # D7 pacing: ideal speech rate ~4-7 chars/s for zh talk
    sr = f["speech_rate"]
    s += 12 if 3.5 <= sr <= 7.5 else (6 if 2.5 <= sr <= 9 else 0)
    # D3 completeness proxy: ideal duration band
    s += 12 if 20 <= seg.dur <= 40 else (6 if seg.dur <= 50 else 2)
    # mild bonus for having real content density
    s += min(8, f["char_count"] / 30)
    return round(min(100.0, s), 1)


def build_candidates(srt_path: str, liberal: bool = True) -> List[dict]:
    entries = parse_srt(srt_path)
    segs = texttile(entries, liberal=liberal)
    cands = []
    for i, s in enumerate(segs, 1):
        f = _heuristic_features(s)
        cands.append({
            "id": i,
            "start": round(s.start, 3),
            "end": round(s.end, 3),
            "dur": round(s.dur, 3),
            "first_index": s.first_index,
            "last_index": s.last_index,
            "text": s.text,
            "features": f,
            "heuristic_score": _heuristic_score(f, s),
            "rubric": None,  # filled by Claude via --finalize
        })
    return cands


def write_packed(cands: List[dict], out: Path, top: int) -> None:
    """Claude's scoring worksheet: pre-ranked by heuristic, full text included."""
    ranked = sorted(cands, key=lambda c: -c["heuristic_score"])
    if top:
        ranked = ranked[:top]
    lines = [
        "# 候選段評分工作表（給 Claude）",
        "",
        "依 `viral_scorer.md` 的 8 維 rubric 對每段打分，輸出 `candidates_scored.json`。",
        "段落已按啟發式分數預排（高→低），但**請獨立判斷**，不要被預排綁架。",
        f"\n共 {len(ranked)} 段（顯示 top {top or '全部'}）。\n",
        "---",
    ]
    for c in ranked:
        f = c["features"]
        flags = []
        if f["qa_complete"]:
            flags.append("問答完整")
        elif f["has_question"]:
            flags.append("⚠只問沒答")
        if f["has_number"]:
            flags.append("有數字")
        if f["contrarian"]:
            flags.append("反直覺")
        if f["hook_hits"]:
            flags.append(f"hook×{f['hook_hits']}")
        if f["filler_density"] > 0.08:
            flags.append(f"⚠贅字{f['filler_density']:.0%}")
        lines += [
            f"\n## id {c['id']}  [{fmt_ts(c['start'])}–{fmt_ts(c['end'])}]  "
            f"{c['dur']:.0f}s  (heur {c['heuristic_score']})",
            f"_flags_: {', '.join(flags) or '—'}  ·  語速 {f['speech_rate']} 字/s  "
            f"·  SRT #{c['first_index']}–{c['last_index']}",
            "",
            c["text"],
        ]
    out.write_text("\n".join(lines), encoding="utf-8")


def finalize(cands_path: Path, scored_path: Path, out_dir: Path, top: int) -> None:
    cands = json.loads(cands_path.read_text(encoding="utf-8"))
    scored = {s["id"]: s for s in json.loads(scored_path.read_text(encoding="utf-8"))}
    by_id = {c["id"]: c for c in cands}
    for cid, sc in scored.items():
        if cid in by_id:
            by_id[cid]["rubric"] = sc

    rated = [c for c in cands if c.get("rubric")]
    rated.sort(key=lambda c: -c["rubric"].get("total", 0))

    # candidates.md — AutoCut-style markdown checklist (human override gate)
    md = ["# 爆款候選段（已評分・勾選你要剪的）", "",
          "> 由 viral_scorer rubric 排序。勾 `[x]` 的會進 selection.json 給 v1/v2 剪。",
          "> 慣例：使用者勾選的才剪，沒勾的不動。\n", "---\n"]
    for rank, c in enumerate(rated, 1):
        r = c["rubric"]
        check = "x" if rank <= (top or 8) and r.get("total", 0) >= 60 else " "
        md += [
            f"- [{check}] **#{rank}  總分 {r.get('total')}**  "
            f"[{fmt_ts(c['start'])}–{fmt_ts(c['end'])}] {c['dur']:.0f}s  "
            f"`{r.get('verdict')}`",
            f"    - hook: 「{r.get('hook_line','')}」",
            f"    - 金句: 「{r.get('quote','')}」",
            f"    - 評語: {r.get('reason','')}",
            f"    - 維度: {r.get('scores')}",
            "",
        ]
    (out_dir / "candidates.md").write_text("\n".join(md), encoding="utf-8")

    # selection.json — top picks ready to cut (start/end in seconds)
    picks = [c for c in rated if c["rubric"].get("total", 0) >= 60][: (top or 8)]
    sel = [{
        "id": c["id"], "start": c["start"], "end": c["end"], "dur": c["dur"],
        "hook_line": c["rubric"].get("hook_line"),
        "quote": c["rubric"].get("quote"),
        "total": c["rubric"].get("total"),
        "text": c["text"],
    } for c in picks]
    (out_dir / "selection.json").write_text(
        json.dumps(sel, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"finalized: {len(rated)} scored, {len(sel)} selected (>=60)")
    print(f"  -> {out_dir/'candidates.md'}")
    print(f"  -> {out_dir/'selection.json'}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Score long-video segments for virality")
    ap.add_argument("srt", help="path to .srt")
    ap.add_argument("--out-dir", default=".", help="output directory")
    ap.add_argument("--top", type=int, default=0, help="limit worksheet/selection to top N (0=all)")
    ap.add_argument("--conservative", action="store_true", help="fewer segments")
    ap.add_argument("--finalize", metavar="SCORED_JSON",
                    help="merge Claude's candidates_scored.json -> candidates.md + selection.json")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.finalize:
        finalize(out_dir / "candidates.json", Path(args.finalize), out_dir, args.top)
        return

    cands = build_candidates(args.srt, liberal=not args.conservative)
    (out_dir / "candidates.json").write_text(
        json.dumps(cands, ensure_ascii=False, indent=2), encoding="utf-8")
    write_packed(cands, out_dir / "candidates_packed.md", args.top)

    top_h = sorted(cands, key=lambda c: -c["heuristic_score"])[:5]
    print(f"{len(cands)} candidates -> {out_dir}/candidates.json + candidates_packed.md")
    print("top-5 by heuristic:")
    for c in top_h:
        print(f"  id{c['id']:3d} heur{c['heuristic_score']:5.1f} "
              f"[{fmt_ts(c['start'])}] {c['text'][:34]}…")
    print("\nnext: Claude scores candidates_packed.md with viral_scorer.md "
          "-> candidates_scored.json, then run --finalize")


if __name__ == "__main__":
    main()
