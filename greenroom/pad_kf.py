#!/usr/bin/env python3
"""Pad a green-screen keyframe so Seedance keeps the whole creature in frame.

Content is scaled to 80% and centred on a canvas filled with the SOURCE's own
green — gpt-image-2 green is ~(11,227,33), not pure #00FF00, and a mismatched
fill leaves a visible square the model animates as a prop.

Usage: python3 pad_kf.py <in.png> <out.png> [fraction]
"""
import sys, pathlib
import numpy as np
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
frac = float(sys.argv[3]) if len(sys.argv) > 3 else 0.80

im = Image.open(src).convert("RGB")
W, H = im.size

# the source's own green: modal colour of the 8px border ring
a = np.array(im)
ring = np.concatenate([a[:8].reshape(-1, 3), a[-8:].reshape(-1, 3),
                       a[:, :8].reshape(-1, 3), a[:, -8:].reshape(-1, 3)])
cols, counts = np.unique(ring, axis=0, return_counts=True)
green = tuple(int(v) for v in cols[counts.argmax()])

w, h = int(round(W * frac)), int(round(H * frac))
canvas = Image.new("RGB", (W, H), green)
canvas.paste(im.resize((w, h), Image.LANCZOS), ((W - w) // 2, (H - h) // 2))

outp = pathlib.Path(out)
outp.parent.mkdir(parents=True, exist_ok=True)
canvas.save(outp)
print(f"OK {outp.name}  {W}x{H}  content {int(frac*100)}%  green {green}")
