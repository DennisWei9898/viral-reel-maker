"""Shared SRT parsing for the v6_viral pipeline.

One entry == one subtitle block. We keep original timestamps untouched so
downstream cuts land exactly on entry edges (CLAUDE.md: cuts must fall on
complete semantic boundaries, and -ss math must trust the source SRT).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

_TIME_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
)

# Gemini chunking can emit absurd entries; CLAUDE.md says drop anything > 60s.
MAX_ENTRY_SEC = 60.0


@dataclass
class Entry:
    index: int          # original SRT 1-based index
    start: float        # seconds
    end: float          # seconds
    text: str

    @property
    def dur(self) -> float:
        return self.end - self.start


@dataclass
class Segment:
    """A topic-coherent run of consecutive entries."""
    entries: List[Entry] = field(default_factory=list)

    @property
    def start(self) -> float:
        return self.entries[0].start

    @property
    def end(self) -> float:
        return self.entries[-1].end

    @property
    def dur(self) -> float:
        return self.end - self.start

    @property
    def text(self) -> str:
        return "".join(e.text for e in self.entries)

    @property
    def first_index(self) -> int:
        return self.entries[0].index

    @property
    def last_index(self) -> int:
        return self.entries[-1].index


def _to_sec(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_srt(path: str | Path, drop_long: bool = True) -> List[Entry]:
    """Parse an SRT file into Entry objects.

    drop_long: skip entries longer than MAX_ENTRY_SEC (Gemini chunk errors).
    """
    raw = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    # Split on blank lines between blocks.
    blocks = re.split(r"\n\s*\n", raw.strip())
    entries: List[Entry] = []
    idx = 0
    for block in blocks:
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        # Find the timestamp line (may or may not be preceded by an index line).
        time_line = None
        text_lines: List[str] = []
        for ln in lines:
            if time_line is None and _TIME_RE.search(ln):
                time_line = ln
                continue
            if time_line is None and ln.strip().isdigit():
                continue  # numeric index line
            if time_line is not None:
                text_lines.append(ln.strip())
        if time_line is None:
            continue
        m = _TIME_RE.search(time_line)
        start = _to_sec(*m.groups()[0:4])
        end = _to_sec(*m.groups()[4:8])
        text = " ".join(text_lines).strip()
        if not text or end <= start:
            continue
        if drop_long and (end - start) > MAX_ENTRY_SEC:
            continue
        idx += 1
        entries.append(Entry(index=idx, start=start, end=end, text=text))
    return entries


def fmt_ts(sec: float) -> str:
    """Seconds -> HH:MM:SS for human-readable reports."""
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
