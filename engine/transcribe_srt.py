"""Transcribe a video to sentence-level SRT (+ word-level JSON) for v6_viral.

Why a dedicated script (vs v2/transcribe.py): v2 keeps only word-level data;
v6_viral's segmenter wants sentence-level SRT entries. faster-whisper already
emits sentence-ish segments, so we write those straight to SRT, and ALSO dump
word-level timestamps (used later to trim the 小秋 boundary precisely).

Long-file strategy: for a 100min+ talk, run the full pass with a faster model
(`medium`, good enough to SELECT viral segments). Re-transcribe only the final
short clips with `large-v3` for accurate burn-in subtitles — short clips make
large-v3 fast.

Usage:
  python transcribe_srt.py <video> --out-dir <dir> [--model medium] [--language zh]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

FFMPEG = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"


def extract_audio(video: str, wav: str) -> None:
    subprocess.run(
        [FFMPEG, "-y", "-i", video, "-ac", "1", "-ar", "16000",
         "-c:a", "pcm_s16le", wav],
        check=True, capture_output=True,
    )


def fmt_srt_ts(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    if ms == 1000:
        s += 1
        ms = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--model", default="medium",
                    help="faster-whisper model (medium=fast full pass, large-v3=accurate)")
    ap.add_argument("--language", default="zh")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(args.video).stem
    wav = str(out_dir / "_audio.wav")
    srt_path = out_dir / f"{stem}.srt"
    words_path = out_dir / f"{stem}.words.json"

    if Path(wav).exists() and Path(wav).stat().st_size > 1_000_000:
        print(f"[1/3] reusing existing audio {wav}", flush=True)
    else:
        print(f"[1/3] extracting audio -> {wav}", flush=True)
        extract_audio(args.video, wav)

    print(f"[2/3] transcribing (faster-whisper {args.model}, CPU int8, zh)...", flush=True)
    from faster_whisper import WhisperModel
    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        wav, language=args.language, word_timestamps=True,
        vad_filter=True, vad_parameters={"min_silence_duration_ms": 400},
        # Anti-hallucination: without these, once the model emits a token like
        # "OK" it conditions on its own output and loops it for the whole file
        # (observed: 95% of segments became 40ms "OK"). Disabling context carry
        # + dropping low-speech / over-compressed windows fixes the loop.
        condition_on_previous_text=False,
        no_speech_threshold=0.6,
        compression_ratio_threshold=2.4,
        log_prob_threshold=-1.0,
    )

    srt_lines, words, idx = [], [], 0
    wid = 0
    for seg in segments:
        text = (seg.text or "").strip()
        if not text:
            continue
        idx += 1
        srt_lines.append(str(idx))
        srt_lines.append(f"{fmt_srt_ts(seg.start)} --> {fmt_srt_ts(seg.end)}")
        srt_lines.append(text)
        srt_lines.append("")
        for w in (seg.words or []):
            words.append({"id": wid, "w": w.word.strip(),
                          "s": round(float(w.start), 3), "e": round(float(w.end), 3),
                          "seg": idx})
            wid += 1
        # progress heartbeat every ~25 segments
        if idx % 25 == 0:
            sys.stdout.write(f"  ..{idx} segments ({seg.end:.0f}s done)\n")
            sys.stdout.flush()

    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
    words_path.write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")

    print(f"[3/3] done: {idx} segments, {len(words)} words", flush=True)
    print(f"  -> {srt_path}", flush=True)
    print(f"  -> {words_path}", flush=True)


if __name__ == "__main__":
    main()
