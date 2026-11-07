#!/usr/bin/env python3
"""generate.py: make images and videos through OpenRouter.

Usage:
  generate.py models image|video            list models and their options
  generate.py price <model> [--duration S] [--resolution R] [--audio]
  generate.py image <model> "<prompt>" [--aspect A] [--resolution R]
                    [--quality Q] [--format F] [--n N] [--ref FILE_OR_URL ...]
                    [--name NAME]
  generate.py video <model> "<prompt>" [--duration S] [--resolution R]
                    [--aspect A] [--audio] [--first FILE_OR_URL]
                    [--last FILE_OR_URL] [--ref FILE_OR_URL ...] [--name NAME]
  generate.py resume <job-id> [--name NAME]  finish a video that was cut off
  generate.py balance                        key limit, usage, local ledger

Keys: OPENROUTER_API_KEY from the environment, else from the KEY=value file
named by AI_ENV_FILE. Key values are never printed.

Output: $GENERATIONS_DIR (default ~/generations). Each file gets a .json
sidecar, and every paid run is appended to ledger.jsonl there.

Spend limit: --limit USD on image, video or price, else $GENERATE_MONTHLY_LIMIT,
else 5. It applies to the calendar month, counted from the ledger. A run whose estimate would cross it is refused; a run
with no estimate is refused once the month has reached it.

Exit codes: 0 ok, 1 generation failed, 2 bad arguments or setup.
"""

import argparse
import base64
import datetime as dt
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://openrouter.ai/api/v1"
OUT_DIR = Path(os.environ.get("GENERATIONS_DIR", "~/generations")).expanduser()
LEDGER = OUT_DIR / "ledger.jsonl"
POLL_TIMEOUT = 30 * 60
MONTHLY_LIMIT = float(os.environ.get("GENERATE_MONTHLY_LIMIT", "5"))


def die(msg, code=2):
    print(f"generate: {msg}", file=sys.stderr)
    sys.exit(code)


def api_key():
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key:
        return key
    env_file = os.environ.get("AI_ENV_FILE", "").strip()
    if not env_file:
        die("no OPENROUTER_API_KEY in the environment and AI_ENV_FILE is not set")
    path = Path(env_file).expanduser()
    if not path.is_file():
        die(f"{path} not found (is its folder locked?)")
    for line in path.read_text().splitlines():
        m = re.match(r"\s*(?:export\s+)?OPENROUTER_API_KEY\s*=\s*(.*)", line)
        if m:
            value = m.group(1).strip().strip("'\"")
            if value:
                return value
    die(f"OPENROUTER_API_KEY is not set in {path}")


def request(method, path, body=None, auth=True, raw=False):
    url = path if path.startswith("http") else API + path
    headers = {"User-Agent": "generate-skill/1.0", "X-OpenRouter-Title": "generate skill"}
    if auth:
        headers["Authorization"] = f"Bearer {api_key()}"
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            payload = resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        try:
            detail = json.loads(detail).get("error", {}).get("message", detail)
        except (ValueError, AttributeError):
            pass
        die(f"{method} {path}: HTTP {e.code}: {detail}", 1)
    except urllib.error.URLError as e:
        die(f"{method} {path}: {e.reason}", 1)
    return payload if raw else json.loads(payload)


def image_ref(value):
    """A URL stays as is; a local file becomes a base64 data URL."""
    if re.match(r"https?://|data:", value):
        url = value
    else:
        path = Path(value).expanduser()
        if not path.is_file():
            die(f"reference not found: {value}")
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        url = f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"
    return {"type": "image_url", "image_url": {"url": url}}


def out_path(name, prompt, ext, index=None):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", (name or prompt).lower()).strip("-")[:40] or "gen"
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = f"-{index}" if index is not None else ""
    return OUT_DIR / f"{slug}_{stamp}{suffix}.{ext}"


def record(path, meta):
    path.with_suffix(path.suffix + ".json").write_text(json.dumps(meta, indent=2) + "\n")
    with LEDGER.open("a") as f:
        f.write(json.dumps({k: meta.get(k) for k in
                            ("created", "kind", "model", "cost_usd", "file", "job_id")}) + "\n")


def now():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


# ---------- pricing ----------

def find_video_model(model):
    for m in request("GET", "/videos/models", auth=False)["data"]:
        if m["id"] == model:
            return m
    die(f"unknown video model: {model} (see: generate.py models video)")


def find_image_model(model):
    for m in request("GET", "/images/models", auth=False)["data"]:
        if m["id"] == model:
            return m
    return None


def video_rate(skus, resolution, audio):
    """Pick the per-second SKU matching resolution and audio. Returns (usd, sku) or (None, None)."""
    res = (resolution or "").lower()
    best = None
    for sku, value in skus.items():
        if "token" in sku or "input" in sku or "reference" in sku or "continuation" in sku \
                or "long_" in sku or "minimum" in sku:
            continue
        if "second" not in sku:
            continue
        if audio and "without_audio" in sku:
            continue
        if not audio and "with_audio" in sku and "without_audio" not in sku and any(
                "without_audio" in k for k in skus):
            continue
        sku_res = re.search(r"_(\d+p|\dk)$", sku)
        if sku_res and sku_res.group(1) != res:
            continue
        usd = float(value) / (100 if sku.startswith("cents") else 1)
        score = 2 if sku_res else 1  # an exact resolution match beats the default rate
        if best is None or score > best[0]:
            best = (score, usd, sku)
    return (best[1], best[2]) if best else (None, None)


def image_estimate(model, resolution, n):
    """Dollars for n images, or None when the model bills per token."""
    eps = request("GET", f"/images/models/{model}/endpoints", auth=False)
    prices = [p for ep in eps.get("endpoints", []) for p in ep.get("pricing", [])
              if p.get("billable") == "output_image" and p.get("unit") == "image"]
    if not prices:
        return None
    want = (resolution or "").lower()
    match = [p["cost_usd"] for p in prices if (p.get("variant") or "").lower().endswith(want)]
    # No resolution match: assume the priciest variant, so the limit check stays safe.
    return (min(match) if want and match else max(p["cost_usd"] for p in prices)) * n


def video_estimate(model, duration, resolution, audio):
    """Dollars for one clip, or None when the model bills per video token."""
    m = find_video_model(model)
    if audio is None:  # unspecified: assume the model's audio is on, the pricier rate
        audio = bool(m.get("generate_audio"))
    rate, _ = video_rate(m.get("pricing_skus") or {}, resolution, audio)
    duration = duration or (m.get("supported_durations") or [None])[0]
    return rate * duration if rate is not None and duration else None


def month_spent():
    if not LEDGER.is_file():
        return 0.0
    month = dt.date.today().strftime("%Y-%m")
    total = 0.0
    for line in LEDGER.read_text().splitlines():
        if line.strip():
            entry = json.loads(line)
            if (entry.get("created") or "").startswith(month):
                total += entry.get("cost_usd") or 0
    return total


def check_limit(estimate):
    spent = month_spent()
    if estimate is None:
        if spent >= MONTHLY_LIMIT:
            die(f"this month's spend ${spent:.2f} has reached the ${MONTHLY_LIMIT:.2f} limit "
                f"(--limit or GENERATE_MONTHLY_LIMIT)")
        print(f"estimate: unknown until the run; month so far ${spent:.2f} "
              f"of ${MONTHLY_LIMIT:.2f}", flush=True)
        return
    if spent + estimate > MONTHLY_LIMIT:
        die(f"this run (~${estimate:.2f}) would bring this month to ${spent + estimate:.2f}, "
            f"over the ${MONTHLY_LIMIT:.2f} limit (--limit or GENERATE_MONTHLY_LIMIT)")
    print(f"estimate: ${estimate:.2f}; month so far ${spent:.2f} of ${MONTHLY_LIMIT:.2f}",
          flush=True)


def cmd_price(args):
    image = find_image_model(args.model)
    if image:
        eps = request("GET", f"/images/models/{args.model}/endpoints", auth=False)
        for ep in eps.get("endpoints", []):
            for p in ep.get("pricing", []):
                if p.get("billable") != "output_image":
                    continue
                variant = f" ({p['variant']})" if p.get("variant") else ""
                if p["unit"] == "image":
                    price = f"${p['cost_usd']} per image"
                else:
                    price = f"${p['cost_usd'] * 1e6:.2f} per 1M output tokens"
                print(f"{ep['provider_name']}: {price}{variant}")
        return
    m = find_video_model(args.model)
    skus = m.get("pricing_skus") or {}
    rate, sku = video_rate(skus, args.resolution, args.audio)
    duration = args.duration or (m.get("supported_durations") or [None])[0]
    if rate is None:
        kind = "per video token" if any("token" in k for k in skus) else "by unmatched SKUs"
        print(f"no per-second rate: billed {kind}; the exact cost is reported after the run. "
              f"SKUs: {json.dumps(skus)}")
        return
    total = f"; {duration}s = ${rate * duration:.2f}" if duration else ""
    print(f"${rate:.4f}/s ({sku}){total}")
    print(f"month so far: ${month_spent():.2f} of ${MONTHLY_LIMIT:.2f}")


# ---------- commands ----------

def cmd_models(args):
    if args.kind == "image":
        for m in request("GET", "/images/models", auth=False)["data"]:
            params = m.get("supported_parameters", {})
            res = params.get("resolution", {}).get("values", [])
            refs = params.get("input_references", {}).get("max", 0)
            print(f"{m['id']}  res={','.join(res) or '-'}  refs={refs}")
    else:
        for m in request("GET", "/videos/models", auth=False)["data"]:
            durs = m.get("supported_durations") or []
            span = f"{min(durs)}-{max(durs)}s" if durs else "-"
            print(f"{m['id']}  {span}  res={','.join(m.get('supported_resolutions') or [])}"
                  f"  audio={bool(m.get('generate_audio'))}")


def cmd_image(args):
    body = {"model": args.model, "prompt": args.prompt, "n": args.n}
    for field in ("aspect_ratio", "resolution", "quality", "output_format", "seed"):
        value = getattr(args, field)
        if value is not None:
            body[field] = value
    if args.ref:
        body["input_references"] = [image_ref(r) for r in args.ref]
    estimate = image_estimate(args.model, args.resolution, args.n)
    check_limit(estimate)
    result = request("POST", "/images", body)
    images = result.get("data") or []
    if not images:
        die(f"no image returned: {json.dumps(result)[:300]}", 1)
    cost = (result.get("usage") or {}).get("cost")
    estimated = cost is None and estimate is not None
    if estimated:
        cost = estimate
    for i, img in enumerate(images):
        ext = (img.get("media_type") or "image/png").split("/")[-1].replace("jpeg", "jpg")
        path = out_path(args.name, args.prompt, ext, i if len(images) > 1 else None)
        path.write_bytes(base64.b64decode(img["b64_json"]))
        record(path, {
            "created": now(), "kind": "image", "model": args.model, "prompt": args.prompt,
            "params": {k: v for k, v in body.items() if k not in ("prompt", "input_references")},
            "refs": args.ref or [], "cost_usd": cost if i == 0 else 0,
            "cost_estimated": estimated, "file": str(path), "job_id": None,
        })
        print(path)
    print(cost_line(cost, estimated))


def cmd_video(args):
    body = {"model": args.model, "prompt": args.prompt}
    for field in ("duration", "resolution", "aspect_ratio", "seed"):
        value = getattr(args, field)
        if value is not None:
            body[field] = value
    if args.audio is not None:
        body["generate_audio"] = args.audio
    frames = []
    if args.first:
        frames.append({**image_ref(args.first), "frame_type": "first_frame"})
    if args.last:
        frames.append({**image_ref(args.last), "frame_type": "last_frame"})
    if frames:
        body["frame_images"] = frames
    if args.ref:
        body["input_references"] = [image_ref(r) for r in args.ref]
    estimate = video_estimate(args.model, args.duration, args.resolution, args.audio)
    check_limit(estimate)
    job = request("POST", "/videos", body)
    job_id = job.get("id") or die(f"no job id returned: {json.dumps(job)[:300]}", 1)
    print(f"job: {job_id}", flush=True)
    meta = {"model": args.model, "prompt": args.prompt,
            "params": {k: v for k, v in body.items()
                       if k not in ("prompt", "frame_images", "input_references")},
            "refs": [r for r in (args.first, args.last, *(args.ref or [])) if r]}
    finish_video(job_id, args.name or args.prompt, meta, estimate)


def cost_line(cost, estimated):
    if cost is None:
        return "cost: not reported"
    return f"cost: ~${cost:.4f} (estimated; not reported)" if estimated else f"cost: ${cost}"


def finish_video(job_id, name, meta, estimate=None):
    delay, waited = 5, 0
    while True:
        job = request("GET", f"/videos/{job_id}")
        status = job.get("status")
        if status == "completed":
            break
        if status in ("failed", "cancelled", "expired"):
            die(f"job {job_id} {status}: {job.get('error') or ''}", 1)
        if waited >= POLL_TIMEOUT:
            die(f"job {job_id} still {status} after {POLL_TIMEOUT // 60} min; "
                f"run: generate.py resume {job_id}", 1)
        time.sleep(delay)
        waited += delay
        delay = min(delay + 5, 20)
    path = out_path(None, name, "mp4")
    path.write_bytes(request("GET", f"/videos/{job_id}/content?index=0", raw=True))
    cost = (job.get("usage") or {}).get("cost")
    estimated = cost is None and estimate is not None
    if estimated:
        cost = estimate
    record(path, {"created": now(), "kind": "video", **meta, "cost_usd": cost,
                  "cost_estimated": estimated, "file": str(path), "job_id": job_id})
    print(path)
    print(cost_line(cost, estimated))


def cmd_resume(args):
    finish_video(args.job_id, args.name or args.job_id, {"model": None, "prompt": None})


def cmd_balance(args):
    key = request("GET", "/key").get("data", {})
    limit, left = key.get("limit"), key.get("limit_remaining")
    print(f"key: {key.get('label') or '-'}")
    print(f"limit: {'none' if limit is None else f'${limit:.2f}'}"
          f"  remaining: {'-' if left is None else f'${left:.2f}'}"
          f"  resets: {key.get('limit_reset') or 'never'}")
    print(f"usage: today ${key.get('usage_daily', 0):.2f}  month ${key.get('usage_monthly', 0):.2f}")
    print(f"this month: ${month_spent():.2f} of the ${MONTHLY_LIMIT:.2f} limit "
          f"(GENERATE_MONTHLY_LIMIT; ledger {LEDGER})")


def main():
    p = argparse.ArgumentParser(description="Generate images and videos through OpenRouter.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("models")
    s.add_argument("kind", choices=["image", "video"])
    s.set_defaults(fn=cmd_models)

    s = sub.add_parser("price")
    s.add_argument("model")
    s.add_argument("--duration", type=int)
    s.add_argument("--resolution")
    s.add_argument("--audio", action="store_true")
    s.set_defaults(fn=cmd_price)

    s = sub.add_parser("image")
    s.add_argument("model")
    s.add_argument("prompt")
    s.add_argument("--aspect", dest="aspect_ratio")
    s.add_argument("--resolution")
    s.add_argument("--quality")
    s.add_argument("--format", dest="output_format")
    s.add_argument("--seed", type=int)
    s.add_argument("--n", type=int, default=1)
    s.add_argument("--ref", action="append")
    s.add_argument("--name")
    s.set_defaults(fn=cmd_image)

    s = sub.add_parser("video")
    s.add_argument("model")
    s.add_argument("prompt")
    s.add_argument("--duration", type=int)
    s.add_argument("--resolution")
    s.add_argument("--aspect", dest="aspect_ratio")
    s.add_argument("--seed", type=int)
    audio = s.add_mutually_exclusive_group()
    audio.add_argument("--audio", dest="audio", action="store_true", default=None)
    audio.add_argument("--no-audio", dest="audio", action="store_false")
    s.add_argument("--first")
    s.add_argument("--last")
    s.add_argument("--ref", action="append")
    s.add_argument("--name")
    s.set_defaults(fn=cmd_video)

    s = sub.add_parser("resume")
    s.add_argument("job_id")
    s.add_argument("--name")
    s.set_defaults(fn=cmd_resume)

    s = sub.add_parser("balance")
    s.set_defaults(fn=cmd_balance)

    for name in ("price", "image", "video"):
        sub.choices[name].add_argument("--limit", type=float,
                                       help="monthly spend limit in USD for this run")
    args = p.parse_args()
    if getattr(args, "limit", None) is not None:
        global MONTHLY_LIMIT
        MONTHLY_LIMIT = args.limit
    args.fn(args)


if __name__ == "__main__":
    main()
