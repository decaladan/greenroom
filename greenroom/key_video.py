#!/usr/bin/env python3
"""Chroma-key a green-screen mp4 -> transparent WebM (VP9 alpha). Soft key + despill.

Usage: python3 key_video.py <in.mp4> <out.webm>   (scratch frames land in ./out/_key)
"""
import sys, subprocess, shutil, pathlib
import numpy as np
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
work = pathlib.Path("out/_key"); shutil.rmtree(work, ignore_errors=True)
(work / "rgba").mkdir(parents=True)

# 1. get fps + extract frames
import json
info = json.loads(subprocess.run(["ffprobe","-v","quiet","-print_format","json","-show_streams",src],
                                 capture_output=True, text=True).stdout)
v = [s for s in info["streams"] if s["codec_type"] == "video"][0]
fps = eval(v["r_frame_rate"])
subprocess.run(["ffmpeg","-y","-loglevel","error","-i",src,str(work/"f_%04d.png")])
frames = sorted(work.glob("f_*.png"))

LO, HI = 40.0, 110.0   # greenness ramp: <LO opaque, >HI transparent
for f in frames:
    im = np.asarray(Image.open(f).convert("RGB")).astype(np.float32)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    gn = g - np.maximum(r, b)                      # greenness
    alpha = np.clip((HI - gn) / (HI - LO), 0, 1)   # 1=keep, 0=cut
    # despill: pull green down toward max(r,b) where it spikes
    spill = np.minimum(g, np.maximum(r, b))
    g2 = np.where(gn > 0, spill, g)
    rgba = np.dstack([r, g2, b, alpha * 255]).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(work / "rgba" / f.name)

# 2. encode WebM VP9 with alpha
subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(fps),
                "-i",str(work/"rgba"/"f_%04d.png"),
                "-c:v","libvpx-vp9","-pix_fmt","yuva420p","-b:v","0","-crf","30",
                "-auto-alt-ref","0","-an", out])
print(f"OK {out}  {pathlib.Path(out).stat().st_size//1024} KB  ({len(frames)} frames @ {fps:.0f}fps)")
