# greenroom

A small, boring, working pipeline for making 2D game assets with generative models:

```
gpt-image-2  ──►  Seedance / Hailuo  ──►  chroma key  ──►  sprite sheet or alpha WebM
 (keyframe on      (image → video,        (background       (what the game/firmware
  a flat chroma     start+end frame)       removal)          actually loads)
  background)
```

Every stage is a standalone CLI script that takes files in and writes files out. There is
no framework, no config format, no orchestrator — a batch is a JSON array of jobs, and a
failed job is re-run by editing one line. Built while shipping the art for a handheld
creature game, so the defaults are tuned for **cut-out characters and props on a
transparent background**, not for photoreal video.

## Why a chroma background at all

Generative models will not give you a clean alpha channel. Ask for "transparent
background" and you get a checkerboard painted into the image. So every asset is generated
on a **flat impossible colour**, and the cut is made afterwards with arithmetic instead of
inference:

- **Green `#00FF00`** for characters and creatures — `key_still.py`, `key_video.py`.
- **Magenta `#FF00FF`** for landscape art — `chroma_knockout.py`. Guessing which blue is
  "sky" costs a morning: the same colour is sky, blue rock shadow, hazy peak and cloud, so
  any threshold either eats the mountains or keeps the sky. Magenta cannot occur in the
  art, so the cut is exact rather than inferred.

Both keys measure a colour *distance*, not equality (`g - max(r,b)`, `min(r,b) - g`), ramp
alpha across a band so silhouettes stay antialiased, and then **de-spill** — without that
last step every edge keeps a green or pink rim.

## The stages

### 1 · Keyframe — `gen_image.py`

`openai/gpt-image-2` through Replicate, in **image-edit** mode: pass existing art as a
reference and it stays on-model far better than text-to-image.

```bash
python3 greenroom/gen_image.py ref.png out/hero.png "…on a flat pure green background…" 2
python3 greenroom/batch_gen.py examples/image_jobs.json 4      # parallel, jobs JSON
```

`gen_image_openai.py` is the same call straight to OpenAI, for when Replicate has no credit
(and vice versa — that redundancy is the whole reason both exist).

`pad_kf.py` shrinks the subject to ~80% of the canvas before animating, filling the margin
with **the source image's own green** (gpt-image-2's green is about `(11,227,33)`, not pure
`#00FF00`; a mismatched fill leaves a square the video model animates as a prop).

### 2 · Animate — `gen_video.py`, `gen_transition.py`, `gen_video_minimax.py`

Seedance takes a **first and a last frame**, which is the entire trick behind loops:

| Want | Call | first / last |
|---|---|---|
| Seamless idle loop | `gen_video.py` | same image for both |
| One-way transition (egg hatches, day→night) | `gen_transition.py` | different images |
| Longer, more motion, no end-frame control | `gen_video_minimax.py` | `minimax/hailuo-2.3`, first frame only |

```bash
python3 greenroom/gen_video.py out/hero.png out/hero_idle.mp4 "gentle idle: breathes, blinks, tail flicks, stays in place"
python3 greenroom/batch_anim.py examples/video_jobs.json 5     # parallel + out/SPEND.log
```

Say **"the final frame matches the first exactly, no camera movement, flat unchanged
background"** in the prompt as well as passing the end frame — the two together hold the
loop; either alone drifts.

### 3 · Key out the background

```bash
python3 greenroom/key_still.py  shot.png     out/hero.png 512    # still  → cropped RGBA
python3 greenroom/key_video.py  clip.mp4     out/hero.webm       # clip   → VP9 alpha WebM
python3 greenroom/chroma_knockout.py bg.png  out/bg.png          # magenta landscape art
python3 greenroom/harden_alpha.py out/*.png                      # re-solidify a soft matte
```

### 4 · Turn a clip into frames the game can load

```bash
python3 greenroom/sheet_from_video.py clip.mp4 out/hero.png 8    # strip PNG + .json meta
python3 greenroom/sprite_export.py    clip.mp4 out/hero 8 80     # + raw RGB565 for firmware
python3 greenroom/slice_sheet.py      sheet.png out/ --rows 2 --cols 5
```

`sheet_from_video.py` samples N frames evenly across the clip, drops the last one on a loop
(it duplicates the first), and crops **one union bbox for the whole set** — per-frame
cropping makes the character jitter between cells. `slice_sheet.py` finds connected regions
of real ink rather than cutting a blind grid, because a model asked for an even 2×5 sheet
gets close but never exact, and a fixed crop clips ears and tails.

## Setup

```bash
pip install -r requirements.txt          # pillow, numpy, scipy  (+ openai, optional)
cp .env.example .env                     # then paste your own tokens in
```

`ffmpeg` and `ffprobe` must be on `PATH`.

`keys.py` reads `REPLICATE_API_TOKEN` and `OPENAI_API_KEY` from the environment first, then
from `.env` at the repo root. **`.env` is gitignored — no token, key or account identifier
belongs in a commit.** Nothing in this repo prints a token; if you add a script, keep it
that way.

## What it costs (measured, 2026)

| | |
|---|---|
| gpt-image-2, medium, 1024² | ~$0.05 / image |
| Seedance 2.0 fast, 480p | ~$0.045 / s (~$0.18 per 4 s clip) |
| Seedance 2.0, 480p | ~$0.092 / s |
| Hailuo 2.3, 1080p | per-clip, 6 s or 10 s only |

`batch_anim.py` appends a line per clip to `out/SPEND.log` so a batch's cost is a `wc`
away, not a surprise on the invoice. A full ~15-image / 20-clip character overhaul lands
around **$8**.

## Gotchas worth the money they cost to learn

- **Seedance `duration` must be 4–15 s** (or `-1`). `duration: 3` fails with
  `E006 invalid input`.
- **Hailuo has no `last_frame_image`** and only accepts `duration` 6 or 10, `resolution`
  768p or 1080p. It is the wrong tool for a loop and the right one for a long take.
- **Generate in small batches and look at every result.** Fanning a whole prompt sheet at
  the API in one go buys a folder of near-misses that all need re-running.
- **Relative size instructions do not work.** "Make the strip 1.5× wider" moved a 12.6%
  element to 11.2%. Compose the geometry yourself in PIL and pass *that* as the only
  reference image; a second, contradicting reference makes the model revert.
- **Audit every cut-out with an alpha histogram, not by eye.** Background removal can leave
  the *interior* soft, not just the edge — one tree came back 39% partial alpha with a
  median of 165, invisible against a flat backdrop and glaring over a detailed one. More
  than ~8% partial pixels means run `harden_alpha.py`; the covered area should barely move
  (58.1% → 56.2%), or the threshold is eating the silhouette.
- **To check a transparency complaint, fill the backdrop with magenta and count blended
  pixels.** Nothing else in a scene can produce them. Faster than reasoning about draw
  order (4991 px/frame before a matte fix, 293 after — that remainder is the real outline).
- **Ablate one layer at a time** before theorising about a visual artifact. One render per
  candidate beats an argument about compositing.
- Everything intermediate goes to `out/` — gitignored, regenerable, and safe to delete.
