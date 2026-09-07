#!/usr/bin/env python3
"""Cut a magenta concept sheet into one PNG per creature.

WHY NOT A BLIND GRID CROP. The model is asked for an even 2x5 grid and gets close, but
never exact — cells drift by tens of pixels and the creatures are not all the same size.
A fixed crop clips ears and tails. So the grid is used only to decide WHICH BLOB belongs
to which cell: the sheet is knocked off the magenta first, connected regions of real ink
are found, and each region is cropped to its own bounds with a small margin.

That also means a sheet with 9 or 11 creatures, or one where two touch, reports what it
actually found instead of silently writing a wrong slice.

Usage: slice_sheet.py <sheet.png> <outdir> [--rows 2] [--cols 5] [--min-frac 0.004]
"""
import argparse, os, sys

import numpy as np
from PIL import Image
from scipy import ndimage


def magentaness(a):
    """Same measure chroma_knockout uses: pure #FF00FF scores 255, real art scores <= 0."""
    r = a[:, :, 0].astype(np.int16)
    g = a[:, :, 1].astype(np.int16)
    b = a[:, :, 2].astype(np.int16)
    return np.minimum(r, b) - g


def blobs(mask, min_px):
    """(label array, [(id, px, x0, y0, x1, y1)]) for regions of at least min_px pixels."""
    lab, n = ndimage.label(mask)
    if not n:
        return lab, []
    out = []
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        px = int((lab[sl] == i).sum())
        if px >= min_px:
            out.append((i, px, sl[1].start, sl[0].start, sl[1].stop - 1, sl[0].stop - 1))
    return lab, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet")
    ap.add_argument("outdir")
    ap.add_argument("--rows", type=int, default=2)
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--min-frac", type=float, default=0.004,
                    help="ignore blobs smaller than this fraction of the sheet")
    ap.add_argument("--margin", type=int, default=12)
    a = ap.parse_args()

    im = Image.open(a.sheet).convert("RGB")
    arr = np.asarray(im)
    H, W = arr.shape[:2]
    ink = magentaness(arr) < 60          # generous: edge pixels blend toward magenta
    lab, found = blobs(ink, int(H * W * a.min_frac * 0.05))
    if not found:
        sys.exit("no creatures found — is the background actually magenta?")

    # Assign every blob to a grid cell by its centre and UNION the bounds, so bubbles and
    # sparks that float clear of the body stay with their creature.
    cells = {}
    for i, n, x0, y0, x1, y1 in found:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        c = min(a.cols - 1, max(0, int(cx / (W / a.cols))))
        r = min(a.rows - 1, max(0, int(cy / (H / a.rows))))
        key = (r, c)
        if key in cells:
            pn, px0, py0, px1, py1, ids = cells[key]
            cells[key] = (max(pn, n), min(px0, x0), min(py0, y0),
                          max(px1, x1), max(py1, y1), ids + [i])
        else:
            cells[key] = (n, x0, y0, x1, y1, [i])

    # a cell only counts as filled if its LARGEST region is creature-sized
    main = int(H * W * a.min_frac)
    cells = {k: v for k, v in cells.items() if v[0] >= main}
    MAGENTA = np.array([255, 0, 255], np.uint8)

    os.makedirs(a.outdir, exist_ok=True)
    base = os.path.splitext(os.path.basename(a.sheet))[0]
    for (r, c), (n, x0, y0, x1, y1, ids) in sorted(cells.items()):
        m = a.margin
        bx0, by0 = max(0, x0 - m), max(0, y0 - m)
        bx1, by1 = min(W, x1 + 1 + m), min(H, y1 + 1 + m)
        tile = arr[by0:by1, bx0:bx1].copy()
        mine = np.isin(lab[by0:by1, bx0:bx1], ids)
        tile[~mine] = MAGENTA                      # neighbours go back to background
        out = os.path.join(a.outdir, f"{base}_r{r + 1}c{c + 1}.png")
        Image.fromarray(tile).save(out)
        print(f"{os.path.basename(out)}  {bx1-bx0}x{by1-by0}  {n} px")

    want = a.rows * a.cols
    print(f"\n{len(cells)}/{want} cells filled"
          + ("" if len(cells) == want else "  <-- sheet is short or two creatures merged"))


if __name__ == "__main__":
    main()
