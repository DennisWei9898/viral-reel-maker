#!/usr/bin/env bash
# Viral Reel Maker — installer.
# Installs the engine + styles to ~/.claude/viral-reel-maker and registers the
# agent at ~/.claude/agents/viral-reel-maker.md so your agent runtime picks it up.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
DEST="${VRM_DIR:-$HOME/.claude/viral-reel-maker}"
AGENTS_DIR="${CLAUDE_AGENTS_DIR:-$HOME/.claude/agents}"

echo "Viral Reel Maker — installing"
echo "  engine + styles -> $DEST"
echo "  agent           -> $AGENTS_DIR/viral-reel-maker.md"

mkdir -p "$DEST" "$AGENTS_DIR"
cp -R "$REPO_DIR/engine" "$REPO_DIR/styles" "$DEST/"
cp "$REPO_DIR/SETUP.md" "$REPO_DIR/requirements.txt" "$DEST/" 2>/dev/null || true
chmod +x "$DEST/engine/make_cta.sh" 2>/dev/null || true

# register the agent (the file already points the engine at $DEST via $VRM)
cp "$REPO_DIR/AGENT.md" "$AGENTS_DIR/viral-reel-maker.md"

# python deps
if command -v pip3 >/dev/null 2>&1; then
  echo "  installing python deps…"
  pip3 install -q -r "$REPO_DIR/requirements.txt" || \
    echo "  ⚠ pip install failed — run 'pip3 install -r requirements.txt' yourself"
fi

# checks
echo
MISS=()
command -v ffmpeg >/dev/null 2>&1 || MISS+=("ffmpeg (brew install ffmpeg)")
[ -e "/Applications/Google Chrome.app" ] || MISS+=("Google Chrome (for title/bg rendering)")
command -v npx >/dev/null 2>&1 || MISS+=("node/npx (for regenerating bg.png via Playwright)")
if [ ${#MISS[@]} -gt 0 ]; then
  echo "Heads up — these aren't on PATH yet:"
  for m in "${MISS[@]}"; do echo "  · $m"; done
fi

cat <<EOF

✅ Installed.
   Engine:  $DEST/engine
   Agent:   $AGENTS_DIR/viral-reel-maker.md   (restart your agent runtime to load it)

Next: just ask the agent — "make reels from this video" — give it a long video
and a reference image of the look you want. It interviews you, builds your style
pack, and produces. Manual smoke test:

   export FFMPEG=\$(command -v ffmpeg)
   python3 "$DEST/engine/gen_title.py" --style "$DEST/styles/default" \\
     --out /tmp/t.png --line "Your **hook**" --line "with a ==highlight==？"
EOF
