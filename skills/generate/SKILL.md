---
name: generate
description: Generate images and videos through OpenRouter, on the cheapest model that fits, quoting cost before paid video runs.
argument-hint: "<what to make>"
license: MIT
metadata:
  author: Michael Shepanski
  inspired-by: https://github.com/Blotato-Inc/blotato-skills (generate)
---

# Generate

Make the image or video the user asks for with `generate.py` (in this skill's
folder; use its absolute path). It needs `python3` and an OpenRouter key:
`OPENROUTER_API_KEY` in the environment, or `AI_ENV_FILE` pointing at a
`KEY=value` file. Set `AI_ENV_FILE` on the command itself, and never print the
key.

```bash
generate.py models image|video        # options per model
generate.py price <model> [--duration S] [--resolution R] [--audio]
generate.py image <model> "<prompt>" [--aspect 16:9] [--resolution 1K] [--ref FILE] [--limit USD]
generate.py video <model> "<prompt>" [--duration 8] [--resolution 720p] [--audio] [--first FILE] [--limit USD]
generate.py resume <job-id>           # finish a video that was cut off
generate.py balance                   # key limit, usage, this month's ledger
```

Files go to `$GENERATIONS_DIR` (default `~/generations`), each with a `.json`
sidecar (model, prompt, params, cost). Every run is logged to `ledger.jsonl`.

**Spend limit:** $5 per calendar month by default, counted from the ledger
(`GENERATE_MONTHLY_LIMIT` changes the default). If the request names a limit
("limit $10", "budget $2"), pass it as `--limit 10` on every run for that
request. The script refuses a run that would cross the limit. When it does,
tell the user the month's total and that they can name a higher limit. Never
raise it yourself.

## Models

Start with the cheapest model that fits. Prices are from 2026-11; check with
`price` before quoting.

| Need | Model | About |
|---|---|---|
| Image draft | `black-forest-labs/flux-3-image-klein` | $0.009 |
| Image, general | `google/gemini-3.1-flash-image` | $0.07 |
| Image, edits or reference photos | `google/gemini-3.1-flash-image` | $0.07 |
| Image with readable text, UI, transparency | `openai/gpt-image-2` | token-billed |
| Image, best quality | `google/gemini-3-pro-image` | $0.13 |
| Video preview | `google/gemini-omni-1.2-flash` at 360p | $0.023/s |
| Video, cheap | `google/veo-3.1-lite` | $0.03/s, $0.05 with audio |
| Video, image-to-video | `bytedance/seedance-2.0-fast` | ~$0.04/s |
| Video, strong motion | `kwaivgi/kling-v3.0-std` | $0.084/s |
| Video, quality | `google/veo-3.1-fast` | $0.08/s, $0.10 with audio |

Use a pricier model only when the user asks or the cheap one failed at the
job. Check a model's sizes, durations and reference limits with `models`.

## Steps

1. **Pin down the request:** image or video, aspect ratio, length, audio,
   reference files. Ask only if the answer changes the result.
2. **Quote.** Run `price`. Images under $0.10 run without asking. For any
   video, or a run over $0.10, ask with the harness's question tool (model,
   settings, cost, `balance` remaining) and wait for a yes. One yes covers one
   run.
3. **Video starts from a still.** Unless the user gave a starting image or
   asked for text-to-video, make a cheap still first, show it, and animate it
   with `--first` once approved.
4. **Run it.** Videos can take minutes: run in the background or with a long
   timeout. If cut off, use `resume <job-id>`.
5. **Show it.** Open the image to look at it, check it matches the request,
   and give the user the file path and the real cost from the output.

## Rules

- One generation at a time.
- Never describe a logo, face, product or UI in words when you can pass the
  real file with `--ref`.
- On failure, say what failed and offer the next model in the same tier. Never
  switch models silently.
- If the key's limit is nearly used up, say so before quoting.
