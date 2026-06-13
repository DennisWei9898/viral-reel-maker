"""Load a style pack (style.json + bg.png). The engine reads ONLY this — no
brand is ever hardcoded. Generate a pack per user with /huashu-design."""
from __future__ import annotations

import json
from pathlib import Path


class Style:
    def __init__(self, style_dir: str):
        self.dir = Path(style_dir)
        self.d = json.loads((self.dir / "style.json").read_text(encoding="utf-8"))
        self.bg = str(self.dir / self.d.get("bg", "bg.png"))

    def __getitem__(self, k):
        return self.d[k]

    @property
    def canvas(self):
        return tuple(self.d.get("canvas", [1080, 1920]))
