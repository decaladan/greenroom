#!/usr/bin/env python3
"""Re-harden a soft alpha matte on a painted cut-out sprite.

Some of the rush art came back from background-removal with a matte that is soft across
the WHOLE interior, not just at the silhouette. rush_tree2.png was the worst: 39% of it
sat at partial alpha with a median of 165, i.e. the entire canopy was ~65% opaque. That
is invisible against a flat, low-contrast backdrop and becomes glaring the moment there
is a bright detailed mountain range behind it -- the trees read as see-through.

The fix is a hard ramp: everything at or above HI becomes fully opaque, everything below
LO becomes fully clear, and only the narrow band between them stays feathered, which is
where a real antialiased silhouette edge lives. Total covered area barely moves (measured
on rush_tree2: 58.1% -> 56.2%), so the silhouette is preserved; only the interior solidifies.

Safe here because the partial pixels are DARKER than the solid ones (72,70,10 vs
141,101,7) -- the art was not matted against white, so no halo appears when it hardens.
Check that before running this on new art.

Usage: harden_alpha.py <file.png> [file.png ...]
"""
import shutil
import sys

import numpy as np
from PIL import Image

LO, HI = 28, 96

for f in sys.argv[1:]:
    a = np.array(Image.open(f).convert("RGBA"))
    A = a[:, :, 3].astype(np.float32)
    before = (100 * ((A > 0) & (A < 255)).mean(), 100 * (A == 255).mean())
    a[:, :, 3] = np.clip((A - LO) / (HI - LO), 0, 1).__mul__(255).round().astype(np.uint8)
    shutil.copy2(f, f + ".softalpha.bak")
    Image.fromarray(a).save(f)
    N = a[:, :, 3]
    print("%-22s partial %5.1f%%->%5.1f%%  solid %5.1f%%->%5.1f%%" % (
        f.rsplit("/", 1)[-1], before[0], 100 * ((N > 0) & (N < 255)).mean(),
        before[1], 100 * (N == 255).mean()))
