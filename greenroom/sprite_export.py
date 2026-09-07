#!/usr/bin/env python3
"""Export a green-screen animation mp4 -> a compact device-ready SPRITE SHEET (N small frames).
This is what an ESP32 build would actually use (it can't decode WebM video). Web demo can use it too.
Outputs: <out>.png (horizontal sheet, transparent) + <out>.json {frames,w,h} + <out>.rgb565 (raw for firmware).

Usage: python3 sprite_export.py <green_mp4> <out_prefix> [frames=8] [size=80]
"""
import sys, subprocess, json, tempfile, shutil, pathlib
import numpy as np
from PIL import Image

src, outpfx = sys.argv[1], sys.argv[2]
NF = int(sys.argv[3]) if len(sys.argv) > 3 else 8
SZ = int(sys.argv[4]) if len(sys.argv) > 4 else 80


def key(im):                                            # green-screen -> RGBA (soft key + despill)
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    gn = g - np.maximum(r, b)
    alpha = np.clip((110.0 - gn) / 70.0, 0, 1)
    g2 = np.where(gn > 0, np.minimum(g, np.maximum(r, b)), g)
    return Image.fromarray(np.dstack([r, g2, b, alpha * 255]).astype(np.uint8), "RGBA")


d = tempfile.mkdtemp()
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, f"{d}/f_%04d.png"])
frames = sorted(pathlib.Path(d).glob("f_*.png"))
if not frames:
    print("no frames"); sys.exit(1)
idx = [round(i * (len(frames) - 1) / (NF - 1)) for i in range(NF)] if NF > 1 else [0]
keyed = [key(Image.open(frames[i])) for i in idx]

boxes = [k.getbbox() for k in keyed if k.getbbox()]     # union bbox so the creature is framed consistently
x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
x1 = max(b[2] for b in boxes); y1 = max(b[3] for b in boxes)

sheet = Image.new("RGBA", (SZ * NF, SZ), (0, 0, 0, 0))
for j, k in enumerate(keyed):
    im = k.crop((x0, y0, x1, y1)); w, h = im.size
    s = min(SZ / w, SZ / h); nw, nh = max(1, int(w * s)), max(1, int(h * s))
    im = im.resize((nw, nh), Image.LANCZOS)
    sheet.paste(im, (j * SZ + (SZ - nw) // 2, SZ - nh), im)   # bottom-anchored (feet aligned)
sheet.save(outpfx + ".png")
json.dump({"frames": NF, "w": SZ, "h": SZ}, open(outpfx + ".json", "w"))

# raw RGB565 for the firmware (what gets stored in flash)
rgb = np.asarray(sheet.convert("RGB")).astype(np.uint16)
r5 = (rgb[..., 0] >> 3) << 11; g6 = (rgb[..., 1] >> 2) << 5; b5 = rgb[..., 2] >> 3
(r5 | g6 | b5).astype("<u2").tobytes().__len__()
open(outpfx + ".rgb565", "wb").write((r5 | g6 | b5).astype("<u2").tobytes())
shutil.rmtree(d, ignore_errors=True)
png_kb = pathlib.Path(outpfx + ".png").stat().st_size // 1024
raw_kb = pathlib.Path(outpfx + ".rgb565").stat().st_size // 1024
print(f"{outpfx}: {NF} frames @ {SZ}x{SZ}  png={png_kb}KB  rgb565={raw_kb}KB")
