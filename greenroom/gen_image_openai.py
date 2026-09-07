#!/usr/bin/env python3
"""Restyle an asset via OpenAI gpt-image-2 images.edit (direct). Fallback when Replicate has no credit.

Usage: python3 gen_image_openai.py <ref_image> <out.png> "<prompt>" [n_images]
With n_images > 1, outputs out_1.png, out_2.png, ...
"""
import sys, base64, pathlib, time
from keys import openai_key
from openai import OpenAI

client = OpenAI(api_key=openai_key())

ref, out, prompt = sys.argv[1], sys.argv[2], sys.argv[3]
n = int(sys.argv[4]) if len(sys.argv) > 4 else 1

t = time.time()
r = client.images.edit(
    model="gpt-image-2",
    image=[open(ref, "rb")],
    prompt=prompt,
    size="1024x1024",
    quality="medium",
    n=n,
)
outp = pathlib.Path(out)
outp.parent.mkdir(parents=True, exist_ok=True)
for i, d in enumerate(r.data):
    dest = outp if len(r.data) == 1 else outp.with_stem(f"{outp.stem}_{i+1}")
    dest.write_bytes(base64.b64decode(d.b64_json))
    print(f"OK {dest}  {dest.stat().st_size//1024} KB")
print(f"done in {time.time()-t:.0f}s via OpenAI direct")
