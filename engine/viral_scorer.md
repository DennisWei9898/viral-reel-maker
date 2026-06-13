# viral_scorer — clip selection rubric (generic, public best-practice)

Score each candidate segment 0-10 on these 5 public short-form principles, then
take the top N. This is a lightweight starting rubric — tune the weights to your
own audience over time.

| # | Dimension | Look for |
|---|---|---|
| 1 | **Hook** | Does the first 1-2 sentences create a pattern interrupt / contrarian claim / curiosity in <1.5s? |
| 2 | **Curiosity gap with payoff** | Opens a question AND answers it inside the clip (never leave the answer outside the cut) |
| 3 | **Self-contained** | Stands alone without surrounding context; has a beginning and a payoff |
| 4 | **Takeaway value** | A concrete number, step, or quotable line the viewer can keep |
| 5 | **Silent readability** | ~85% watch muted — the subtitle alone must carry the message |

Output one JSON object per scored segment into `candidates_scored.json`:
```json
[{"id": 12, "scores": {"hook":8,"gap":9,"standalone":7,"value":7,"silent":8},
  "total": 78, "hook_line": "...", "reason": "...", "quote": "...",
  "verdict": "strong"}]
```
`total` = simple sum × 2 (0-100). `verdict`: strong ≥70 / ok 50-69 / weak <50.

Discipline: every score needs a transcript quote as evidence. Admin/filler
segments ("thanks for coming", "we'll get to that later") score honestly low —
prefer a few strong clips over many mediocre ones.
