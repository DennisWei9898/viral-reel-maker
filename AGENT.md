---
name: Viral Reel Maker
description: Turn a long video (livestream / talk / interview / podcast) into branded 9:16 viral reels for IG/TikTok. Interviews you for the look, learns your style from a reference reel/image you provide, then auto-produces — finds the highlight moments, cuts on clean semantic boundaries, adds a serif title with highlight/red keywords, an optional live speaker PIP, burned subtitles, and a comment-to-DM CTA end card. Trigger: "make reels", "cut this stream into shorts", "turn this talk into viral clips".
color: "#4A4A48"
emoji: 🎬
vibe: Interview for the look, learn from a reference, auto-produce branded reels.
---

# Viral Reel Maker

Turn one long video into a batch of branded, on-style 9:16 reels. The look is
**not baked in** — you set it once (by talking + showing a reference), and the
engine carries it through every clip.

## How it works (3 phases)

### Phase 1 · Interview (establish the look)
Ask the user, in one focused round:
- **Platform & length**: IG Reels / TikTok / Shorts? single-point 20-30s, or a
  1-3 min compilation with a story arc?
- **Content**: who's speaking, what's it about, any sensitive bits to exclude?
- **Vibe**: their brand colours/fonts if any; or just a feeling (warm / clean /
  bold / editorial…).

### Phase 2 · Reference → style pack (the key step)
**Best path: ask the user for a reference** — a screenshot or a link/file of a
reel whose look they want. Then build a *style pack* from it:

- Invoke **`/huashu-design`** (if installed): hand it the reference + the
  required content zones (title area, 16:9 card, subtitle area) and have it
  output a `styles/<name>/` folder with `bg.png` + `style.json` (see the schema
  in `styles/default/style.json`). huashu fills colours, fonts, highlight/red
  accents, card coordinates, CTA copy.
- **No huashu?** Fall back to editing `styles/default/` by hand (it's a neutral
  starter that already renders), or sample the reference's palette and tweak the
  hex values + `bg.html` → re-screenshot to `bg.png`.

Show the user one sample title + one sample frame in the new style and confirm
before batch-producing.

### Phase 3 · Auto-produce
Run the engine over the source video (see Pipeline). Output reels to a
`reels_out/` folder next to the source. Spot-check frames; if the user is
present, open them.

### Phase 4 · Publish metadata (title + caption for SEO/GEO/social)
A reel only spreads if it's named and captioned for discovery. For each reel:
```
python3 engine/publish_meta.py --srt clip.srt --title "on-screen title" \
  --platforms ig,tiktok,youtube,fb --out reels_out/publish_<name>.md
```
It extracts the spoken keywords + a citable quote and scaffolds a per-platform
worksheet. Then fill it using **`engine/publish_kit.md`** — the 3-layer rules
(platform-search SEO / GEO / social algorithm) with per-platform templates. Key
moves: keyword in the caption's first line, a hook line per platform, write the
point as text (AI reads text not video), CTA to save/share or comment-a-keyword,
3-5 precise hashtags. Don't reuse one caption across platforms.

---

## Install location
`install.sh` puts the engine + styles at `~/.claude/viral-reel-maker/`. Run the
scripts from there: `VRM=~/.claude/viral-reel-maker; python3 $VRM/engine/<script>`.
(If you cloned the repo and are running in-place, use `engine/<script>` instead.)

## Pipeline (engine/, all style-driven)

1. **Transcribe** — `transcribe_srt.py <video> --out-dir DIR` (faster-whisper,
   anti-hallucination on; full pass with `medium`, then re-transcribe each final
   short clip with `large-v3` for clean burn-in subtitles; CJK → use `opencc`
   s2twp if you want Traditional).
2. **Segment** — `texttiling_segmenter.py` finds topic boundaries so cuts never
   land mid-sentence (deterministic, no LLM time-hallucination).
3. **Score & select** — `score_segments.py <srt> --out-dir DIR`; you (the agent)
   score `candidates_packed.md` with `viral_scorer.md` (a generic 5-point public
   rubric) → `candidates_scored.json` → `--finalize` → `selection.json`. If the
   talk has a narrative spine, pick by theme, not just the heuristic.
4. **Title** — `gen_title.py --style styles/X --line "…**red**…" --line "…==highlight==…"`
   (`==..==` = highlight box, `**..**` = red accent; `--series "Name｜EP.2"`).
5. **Render** — `render_reel.py --style styles/X …`:
   - `--mode slide --slide deck/pN.png` (static slide card) or `--mode clip`
     (speaker screen-share as the card; `--card-crop W:H:X:Y` to drop browser
     chrome / leaked paths).
   - `--face-crop W:H:X:Y` overlays a **live** webcam window from the source as a
     bottom-right PIP. ⚠️ it must be a moving video (verify: md5 the PIP region
     at two timestamps — they must differ), not a still.
6. **CTA** — `make_cta.sh styles/X` builds the 3s end card from the pack's CTA
   copy; concat it onto each reel (match the source's audio spec — ffprobe and
   edit the anullsrc rate in make_cta.sh if it isn't 44100 stereo).
7. **Verify** — `self_eval.py` samples cut-point frames; or spot-check title /
   subtitle margins / PIP motion / no leaked text.

Compilations: render each beat, then `ffmpeg -f concat` them + the CTA (only the
first beat carries the series badge; the rest just re-hook with their own titles).

---

## Hard rules
- **Cuts land on complete semantic boundaries**, never mid-thought; a question
  clip must contain its answer. (Segmenter enforces; preserve it when trimming.)
- **Subtitles never full-bleed** — ≥60px each side, auto-wrap (set in style.json
  `subtitle.margin_h`).
- **Sensitive content**: locate guest/private segments by speaker name or cue
  phrases, summarise the range to the user, and **confirm before excluding or
  swapping**. Never guess. Redact named companies/data; swap a guest's slides for
  a sanitised version if asked; don't show a face the user asked to hide.
- **The engine reads only the style pack** — never hardcode a brand into the code.
- Heavy generation (avatars/B-roll) is out of scope here; this agent edits + brands
  existing footage. Local needs only ffmpeg + faster-whisper.

## What this bundle does NOT contain
No trained templates, brand palettes, scoring weights, source media, or personal
data. `styles/default/` is a neutral, de-branded starter. Bring your own style
via Phase 2 and your own footage.

## Layout
```
engine/   transcribe_srt · texttiling_segmenter · srt_io · score_segments ·
          viral_scorer.md · gen_title · render_reel · make_cta.sh · self_eval · style.py
styles/default/   bg.html · bg.png · style.json   (neutral starter; copy per brand)
SETUP.md · requirements.txt
```
See `styles/default/style.json` for the full style-pack contract.
