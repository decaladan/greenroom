#!/usr/bin/env python3
"""Cut art off a flat magenta background, with de-spill.

Why magenta and not a sky knock-out: guessing which blue is "sky" cost us a whole
morning — the same colour is sky, blue rock shadow, hazy peak and cloud, so any
threshold either ate the mountains or kept the sky. Painting the background a colour
that cannot occur in the art makes the cut exact instead of inferred.

magentaness = min(R,B) - G.  Pure #FF00FF scores 255; foliage, rock, snow and sky all
score at or below zero. Edge pixels blend toward magenta, so they get partial alpha AND
a de-spill pass that pulls the borrowed magenta back out — without it every silhouette
keeps a pink rim.

Usage: chroma_knockout.py <in.png> <out.png>
"""
import sys

import numpy as np
from PIL import Image

LO, HI = 40, 150            # magentaness: below LO fully art, above HI fully background

src, out = sys.argv[1], sys.argv[2]
a = np.array(Image.open(src).convert("RGBA"))
rgb = a[:, :, :3].astype(np.float32)
R, G, B = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
m = np.minimum(R, B) - G

t = np.clip((m - LO) / (HI - LO), 0, 1)
alpha = 255 * (1 - t * t * (3 - 2 * t))

# de-spill: wherever red and blue both sit above green, that excess is borrowed magenta.
# Pull it out on the pixels we are keeping, or every silhouette edge keeps a pink rim.
keep = alpha > 0
spill = np.clip(np.minimum(R, B) - G, 0, None) * (alpha / 255.0)
rgb[:, :, 0] = np.where(keep, R - spill, R)
rgb[:, :, 2] = np.where(keep, B - spill, B)

a[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
a[:, :, 3] = np.clip(alpha, 0, 255).astype(np.uint8)
Image.fromarray(a).save(out)

A = a[:, :, 3]
ys, xs = np.nonzero(A > 8)
print("%s  clear %.0f%%  partial %.0f%%  solid %.0f%%  content bbox x%d-%d y%d-%d" % (
    out.rsplit("/", 1)[-1], 100 * (A == 0).mean(),
    100 * ((A > 0) & (A < 255)).mean(), 100 * (A == 255).mean(),
    xs.min(), xs.max(), ys.min(), ys.max()))
