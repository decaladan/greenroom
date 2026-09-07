#!/usr/bin/env python3
"""Green-screen still -> keyed RGBA PNG, cropped tight and optionally pre-scaled.

Same key + despill maths as sheet_from_video.py, so a still and a clip-derived sheet
come out of the pipeline looking identical.

Usage: python3 key_still.py <in.png> <out.png> [target_width]
"""
import sys, pathlib
import numpy as np
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
tw = int(sys.argv[3]) if len(sys.argv) > 3 else 0

im = Image.open(src).convert("RGB")
a = np.array(im).astype(int)
r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
gn = g - np.maximum(r, b)
al = np.clip(255 - (gn - 18) * 255 / 82, 0, 255).astype(np.uint8)
al[gn >= 100] = 0
al[gn <= 18] = 255
px = a.copy()
px[:, :, 1] = np.where(gn > 0, np.maximum(px[:, :, 0], px[:, :, 2]), px[:, :, 1])  # despill
img = Image.fromarray(np.dstack([px.astype(np.uint8), al]).astype(np.uint8), "RGBA")

bb = img.getbbox()
if bb:
    img = img.crop(bb)
if tw:
    img = img.resize((tw, round(img.height * tw / img.width)), Image.LANCZOS)

outp = pathlib.Path(out)
outp.parent.mkdir(parents=True, exist_ok=True)
img.save(outp)
print(f"OK {outp.name}  {img.size[0]}x{img.size[1]}  {outp.stat().st_size//1024} KB")
