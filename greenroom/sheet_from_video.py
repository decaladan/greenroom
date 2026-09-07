#!/usr/bin/env python3
"""Green-screen mp4 -> horizontal keyed sprite-sheet PNG for the web games.

Where key_video.py gives you a WebM to <video>, this gives you one strip PNG a
canvas can drawImage() a cell out of -- and no video decoder. Frames are sampled evenly across
the clip so a 4s Seedance take becomes an N-frame cycle.

Usage: python3 sheet_from_video.py <in.mp4> <out.png> <n_frames> [--no-loop]
  default drops the last frame (it duplicates the first on a seamless loop);
  --no-loop keeps the full span, for one-shots like a jump or a tumble.
"""
import sys, subprocess, tempfile, pathlib, json
import numpy as np
from PIL import Image

src, out, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
loop = "--no-loop" not in sys.argv

d = pathlib.Path(tempfile.mkdtemp())
subprocess.run(["ffmpeg", "-v", "error", "-i", src, str(d / "f%04d.png")], check=True)
files = sorted(d.glob("f*.png"))
if not files:
    sys.exit("no frames decoded")

# even sample across the clip; on a loop the last frame repeats the first, so stop short
span = len(files) - 1 if loop else len(files) - 1
idx = [round(i * span / n) if loop else round(i * span / max(1, n - 1)) for i in range(n)]

def key(im):
    a = np.array(im.convert("RGB")).astype(int)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    gn = g - np.maximum(r, b)
    al = np.clip(255 - (gn - 18) * 255 / 82, 0, 255).astype(np.uint8)
    al[gn >= 100] = 0
    al[gn <= 18] = 255
    px = np.array(im.convert("RGB")).astype(int)
    px[:, :, 1] = np.where(gn > 0, np.maximum(px[:, :, 0], px[:, :, 2]), px[:, :, 1])  # despill
    return Image.fromarray(np.dstack([px.astype(np.uint8), al]), "RGBA")

frames = [key(Image.open(files[i])) for i in idx]

# one bbox for the WHOLE set: per-frame cropping would make him jitter between cells
boxes = [f.getbbox() for f in frames if f.getbbox()]
x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
x1 = max(b[2] for b in boxes); y1 = max(b[3] for b in boxes)
frames = [f.crop((x0, y0, x1, y1)) for f in frames]

w, h = frames[0].size
sheet = Image.new("RGBA", (w * len(frames), h), (0, 0, 0, 0))
for i, f in enumerate(frames):
    sheet.paste(f, (i * w, 0), f)
outp = pathlib.Path(out); outp.parent.mkdir(parents=True, exist_ok=True)
sheet.save(outp)
meta = {"frames": len(frames), "cell": [w, h], "src": pathlib.Path(src).name}
outp.with_suffix(".json").write_text(json.dumps(meta))
print(f"OK {outp.name}  {len(frames)}f  cell {w}x{h}  sheet {sheet.size[0]}x{sheet.size[1]}  "
      f"{outp.stat().st_size//1024} KB")
