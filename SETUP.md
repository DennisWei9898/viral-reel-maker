# Viral Reel Maker — Setup

Turn a long video into branded 9:16 reels. Interview → learn your style from a
reference → auto-produce. No proprietary templates or data included.

## Requirements
- **macOS** (uses Google Chrome headless for title/bg rendering; ffmpeg paths assume mac)
- **ffmpeg** with `subtitles`/`ass`/`drawtext` filters — e.g. `brew install ffmpeg`
  (the full build). Point the engine at it: `export FFMPEG=/path/to/ffmpeg`
- **Google Chrome** (for `gen_title.py` / background screenshots), or swap in Playwright
- **Python 3.9+** with: `pip install -r requirements.txt`
- **Node** with Playwright (`npx playwright`) — only for regenerating `bg.png`
- Optional: the **`/huashu-design`** skill (Phase 2 style generation). Without it,
  edit `styles/default/` by hand.

## Install
1. Drop `AGENT.md` into your `~/.claude/agents/` (rename to `viral-reel-maker.md`),
   or register however your agent runtime loads agents.
2. Keep the `engine/` and `styles/` folders together; the agent calls them by path.
3. `pip install -r requirements.txt`
4. Smoke test (uses the neutral default style):
   ```bash
   export FFMPEG=/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg   # your ffmpeg
   python3 engine/gen_title.py --style styles/default --out /tmp/t.png \
     --line "Your **hook** here" --line "with a ==highlight==？"
   # then render over any video segment with a slide image + an SRT:
   # python3 engine/render_reel.py --style styles/default --source v.mp4 \
   #   --start 60 --end 80 --mode clip --srt clip.srt --title-png /tmp/t.png --out /tmp/r.mp4
   ```

## Make it your brand
Don't edit the engine. Make a style pack:
- **With /huashu-design**: give it a reference reel + the zone spec; it writes
  `styles/<you>/bg.png` + `style.json`.
- **By hand**: `cp -r styles/default styles/<you>`, edit `style.json` (colours,
  fonts, CTA copy) and `bg.html`, then
  `npx playwright screenshot --viewport-size=1080,1920 file://$PWD/styles/<you>/bg.html styles/<you>/bg.png`.

Then pass `--style styles/<you>` to every engine call.
