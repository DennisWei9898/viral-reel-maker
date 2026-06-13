"""G4 — Deterministic semantic-boundary segmentation (TextTiling, zh-adapted).

Why this exists (research, 2026-06):
  - Letting an LLM free-hand pick cut points causes "time hallucination" and
    cuts that land mid-sentence (cutback.video measured 11/11 bad cuts).
  - ClipsAI's TextTiling (Hearst 1997) finds topic boundaries from lexical
    cohesion alone — zero cost, deterministic, and it can ONLY cut at entry
    edges. That structurally satisfies CLAUDE.md's "never cut mid-thought".

Pipeline role:
  SRT entries -> jieba tokens -> lexical cohesion between sliding windows ->
  depth scores -> boundaries -> merge into >= MIN_SEG_SEC topic segments.

The LLM (Claude) then scores ONLY within these segments — it never invents
timestamps, it just ranks pre-cut semantic blocks.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import List

import jieba

from srt_io import Entry, Segment, parse_srt, fmt_ts

# --- tuning knobs -----------------------------------------------------------
WINDOW = 3            # entries per side of a gap when measuring cohesion
SMOOTH = 1           # rounds of mean smoothing on the gap-score curve
MIN_SEG_SEC = 20.0    # CLAUDE.md: shortest clip 20s for a complete thought
MAX_SEG_SEC = 90.0    # above this, force a split at the weakest internal gap
SILENCE_GAP = 4.0     # gap (s) between entries that forces a hard boundary —
                      # a long pause is always a topic edge (slide / Q&A / breath)
MIN_KEEP_SEC = 3.0    # drop silence-bounded islands shorter than this

# Chinese + English stopwords / fillers that carry no topic signal.
_STOP = set(
    "的 了 是 在 我 你 他 她 它 們 我們 你們 他們 這 那 這個 那個 就 都 也 還 "
    "和 與 跟 或 而 但 然後 因為 所以 如果 那麼 其實 就是 那種 一個 一些 這樣 "
    "那樣 可以 會 要 想 有 沒有 嗯 呃 啊 喔 欸 對 對啊 那 真的 比較 非常 很 "
    "大家 今天 然後就 的話 之後 一下 一直 已經 開始 覺得 知道 看到 來 去 把 "
    "a an the is are was were be to of in on for and or but so it this that "
    "i you he she we they my your".split()
)
_PUNCT_RE = re.compile(r"[\s，。、！？；：「」『』（）()\[\]【】…—\-~,.!?;:\"'`]+")


def tokenize(text: str) -> List[str]:
    toks = []
    for t in jieba.cut(text):
        t = t.strip().lower()
        if not t or _PUNCT_RE.fullmatch(t):
            continue
        if t in _STOP:
            continue
        if len(t) == 1 and t.isascii():  # stray single latin chars
            continue
        toks.append(t)
    return toks


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _smooth(scores: List[float], rounds: int) -> List[float]:
    for _ in range(rounds):
        out = scores[:]
        for i in range(len(scores)):
            lo, hi = max(0, i - 1), min(len(scores), i + 2)
            out[i] = sum(scores[lo:hi]) / (hi - lo)
        scores = out
    return scores


def _gap_scores(token_lists: List[List[str]]) -> List[float]:
    """Cohesion at each gap between entry i and i+1 (len == n-1)."""
    n = len(token_lists)
    scores = []
    for gap in range(n - 1):
        left = Counter()
        for j in range(max(0, gap - WINDOW + 1), gap + 1):
            left.update(token_lists[j])
        right = Counter()
        for j in range(gap + 1, min(n, gap + 1 + WINDOW)):
            right.update(token_lists[j])
        scores.append(_cosine(left, right))
    return scores


def _depth_scores(gap: List[float]) -> List[float]:
    """Hearst depth score: how deep each valley is vs its surrounding peaks."""
    n = len(gap)
    depths = [0.0] * n
    for i in range(n):
        # climb left to a peak
        lpeak = gap[i]
        j = i
        while j > 0 and gap[j - 1] >= gap[j]:
            j -= 1
            lpeak = max(lpeak, gap[j])
        # climb right to a peak
        rpeak = gap[i]
        j = i
        while j < n - 1 and gap[j + 1] >= gap[j]:
            j += 1
            rpeak = max(rpeak, gap[j])
        depths[i] = (lpeak - gap[i]) + (rpeak - gap[i])
    return depths


def _boundaries(depths: List[float], liberal: bool) -> List[int]:
    if not depths:
        return []
    mean = sum(depths) / len(depths)
    var = sum((d - mean) ** 2 for d in depths) / len(depths)
    std = math.sqrt(var)
    # Hearst: cutoff = mean - std (liberal) or mean - std/2 (conservative=fewer).
    cutoff = mean - (std if liberal else std / 2)
    # A gap index g means boundary AFTER entry g (0-based) i.e. before entry g+1.
    bset = [g for g, d in enumerate(depths) if d > cutoff and d > 0]
    return bset


def _split_long(seg: Segment, token_lists_by_index: dict) -> List[Segment]:
    """Recursively split a segment that exceeds MAX_SEG_SEC at its weakest gap."""
    if seg.dur <= MAX_SEG_SEC or len(seg.entries) < 2:
        return [seg]
    # find weakest internal cohesion gap that still leaves both halves >= MIN
    best_i, best_score = None, 2.0
    for i in range(len(seg.entries) - 1):
        left = seg.entries[i]
        # both halves must clear MIN_SEG_SEC
        left_dur = left.end - seg.entries[0].start
        right_dur = seg.entries[-1].end - seg.entries[i + 1].start
        if left_dur < MIN_SEG_SEC or right_dur < MIN_SEG_SEC:
            continue
        a = token_lists_by_index[seg.entries[i].index]
        b = token_lists_by_index[seg.entries[i + 1].index]
        sc = _cosine(Counter(a), Counter(b))
        if sc < best_score:
            best_score, best_i = sc, i
    if best_i is None:
        return [seg]
    left = Segment(seg.entries[: best_i + 1])
    right = Segment(seg.entries[best_i + 1 :])
    return _split_long(left, token_lists_by_index) + _split_long(
        right, token_lists_by_index
    )


def _runs_by_silence(entries: List[Entry]) -> List[List[Entry]]:
    """Partition entries into runs split wherever a silence gap exceeds
    SILENCE_GAP. Cutting never crosses a long pause, so no clip carries dead air.
    """
    runs: List[List[Entry]] = []
    cur: List[Entry] = []
    for e in entries:
        if cur and (e.start - cur[-1].end) > SILENCE_GAP:
            runs.append(cur)
            cur = []
        cur.append(e)
    if cur:
        runs.append(cur)
    return runs


def _texttile_run(run: List[Entry], liberal: bool, tok_by_idx: dict) -> List[Segment]:
    """TextTiling within a single silence-bounded run."""
    if len(run) <= 2:
        return [Segment(run)]
    token_lists = [tok_by_idx[e.index] for e in run]
    gap = _smooth(_gap_scores(token_lists), SMOOTH)
    depths = _depth_scores(gap)
    bset = set(_boundaries(depths, liberal))

    segments: List[Segment] = []
    cur: List[Entry] = []
    for i, e in enumerate(run):
        cur.append(e)
        if i in bset:  # boundary AFTER entry i (within this run)
            segments.append(Segment(cur))
            cur = []
    if cur:
        segments.append(Segment(cur))

    # Merge forward within the run until each clears MIN_SEG_SEC. We never merge
    # across run edges, so this can't reintroduce a silence-spanning segment.
    merged: List[Segment] = []
    for seg in segments:
        if merged and merged[-1].dur < MIN_SEG_SEC:
            merged[-1] = Segment(merged[-1].entries + seg.entries)
        else:
            merged.append(seg)
    if len(merged) >= 2 and merged[-1].dur < MIN_SEG_SEC:
        last = merged.pop()
        merged[-1] = Segment(merged[-1].entries + last.entries)
    return merged


def segment(entries: List[Entry], liberal: bool = True) -> List[Segment]:
    """Main entry: entries -> list of topic Segments respecting duration bounds.

    Two-stage: (1) hard-split on silence gaps so no segment spans a long pause,
    (2) TextTiling within each silence-bounded run, then split over-long blocks.
    """
    if not entries:
        return []
    tok_by_idx = {e.index: tokenize(e.text) for e in entries}

    final: List[Segment] = []
    for run in _runs_by_silence(entries):
        for seg in _texttile_run(run, liberal, tok_by_idx):
            final.extend(_split_long(seg, tok_by_idx))

    # Drop trivial silence-bounded islands (filler like "好"/"對" with no content).
    final = [s for s in final if s.dur >= MIN_KEEP_SEC]
    return final


def main() -> None:
    ap = argparse.ArgumentParser(description="TextTiling semantic segmentation of an SRT")
    ap.add_argument("srt", help="path to .srt")
    ap.add_argument("--out", help="write segments.json here")
    ap.add_argument("--conservative", action="store_true",
                    help="fewer boundaries (mean - std/2)")
    args = ap.parse_args()

    entries = parse_srt(args.srt)
    segs = segment(entries, liberal=not args.conservative)

    print(f"parsed {len(entries)} entries -> {len(segs)} topic segments")
    for i, s in enumerate(segs, 1):
        preview = s.text[:40].replace("\n", " ")
        print(f"  [{i:3d}] {fmt_ts(s.start)}–{fmt_ts(s.end)} "
              f"({s.dur:5.1f}s, {len(s.entries)} entries) {preview}…")

    if args.out:
        data = [{
            "id": i,
            "start": round(s.start, 3),
            "end": round(s.end, 3),
            "dur": round(s.dur, 3),
            "first_index": s.first_index,
            "last_index": s.last_index,
            "text": s.text,
        } for i, s in enumerate(segs, 1)]
        Path(args.out).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
