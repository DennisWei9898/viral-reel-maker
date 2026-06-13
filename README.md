# 🎬 Viral Reel Maker

Turn one long video — a livestream, talk, interview, or podcast — into a batch of
**branded 9:16 vertical reels** for Instagram / TikTok / YouTube Shorts.

It's an AI agent (built for [Claude Code](https://claude.com/claude-code) and
compatible agent runtimes). You give it a long video and a **reference image of
the look you want**; it interviews you, learns your style, then auto-produces:

- 🔎 **Finds the highlight moments** — segments on clean semantic boundaries
  (never cuts mid-sentence) and scores clips against a short-form virality rubric
- ✍️ **Serif title cards** with `==highlight==` and `**accent**` keyword treatments
- 🗣️ **Live speaker PIP** — a moving webcam window cropped from the source, bottom-right
- 💬 **Burned subtitles** (auto-wrapped, never full-bleed) + a comment-to-DM **CTA end card**
- 🎞️ **1–3 min compilations** with cold-open + re-hooks for longer-form story arcs

**The look is not baked in.** The engine reads a *style pack* (`bg.png` +
`style.json`) — swap the pack, swap the entire brand. Generate one per project
from a reference with `/huashu-design`, or hand-edit the
neutral starter in `styles/default/`.

---

## Install

```bash
git clone https://github.com/DennisWei9898/viral-reel-maker.git
cd viral-reel-maker
./install.sh
```

This installs the engine + styles to `~/.claude/viral-reel-maker/` and registers
the agent at `~/.claude/agents/viral-reel-maker.md`. Restart your agent runtime,
then just say: **"make reels from this video"** and hand it a video + a reference image.

**Requirements** (macOS): `ffmpeg` (full build, `brew install ffmpeg`), Google
Chrome, Python 3.9+, Node/Playwright (for regenerating backgrounds). See
[`SETUP.md`](SETUP.md).

---

## How it works

```
Phase 1  Interview   → platform, content, vibe
Phase 2  Reference   → you give a reference reel/image →
                       /huashu-design builds your style pack (bg.png + style.json)
Phase 3  Produce     → transcribe → segment → score → title → render → CTA → verify
```

The engine is 100% style-driven and ships with **no proprietary templates,
scoring weights, or data** — `styles/default/` is a neutral, de-branded starter.
Bring your own look and your own footage.

---

## Contact

Built by **Dennis Wei**. If you're interested in the full pipeline, custom style
systems, or working together on AI-driven content production — reach out:

- 💼 LinkedIn: https://www.linkedin.com/in/dennis-wei-47393a14a/
- ✉️ Email: dennis.xd.wei@gmail.com

---

## License

[MIT](LICENSE) © Dennis Wei. Use it, fork it, ship your own reels.
