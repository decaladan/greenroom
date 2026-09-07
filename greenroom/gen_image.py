#!/usr/bin/env python3
"""Generate/restyle an asset via Replicate's openai/gpt-image-2 (image-edit mode).
Billed to Replicate, which also sidesteps a capped OpenAI account.

Usage: python3 gen_image.py <ref_image[,ref2,...]> <out.png> "<prompt>" [n_images] [aspect]
Refs are comma-separated (first = style anchor). aspect: 1:1 (default), 3:2, 2:3.
With n_images > 1, outputs out_1.png, out_2.png, ...
"""
import sys, json, time, base64, mimetypes, pathlib, urllib.request, urllib.error
from keys import replicate_token

TOK = replicate_token()
refs, out, prompt = sys.argv[1].split(","), sys.argv[2], sys.argv[3]
n = int(sys.argv[4]) if len(sys.argv) > 4 else 1
aspect = sys.argv[5] if len(sys.argv) > 5 else "1:1"


def data_uri(p):
    mime = mimetypes.guess_type(p)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(pathlib.Path(p).read_bytes()).decode()


def api(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=90))
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode()[:400]); raise


inp = {
    "prompt": prompt,
    "input_images": [data_uri(r) for r in refs],
    "quality": "medium",
    "aspect_ratio": aspect,
    "background": "opaque",
    "output_format": "png",
    "number_of_images": n,
}
t0 = time.time()
pred = api("POST", "https://api.replicate.com/v1/models/openai/gpt-image-2/predictions", {"input": inp})
get_url = pred["urls"]["get"]
while pred["status"] not in ("succeeded", "failed", "canceled"):
    time.sleep(3); pred = api("GET", get_url)
if pred["status"] != "succeeded":
    print("FAILED:", json.dumps(pred.get("error"))[:400]); sys.exit(1)
o = pred["output"]
urls = o if isinstance(o, list) else [o]
outp = pathlib.Path(out)
outp.parent.mkdir(parents=True, exist_ok=True)
for i, url in enumerate(urls):
    dest = outp if len(urls) == 1 else outp.with_stem(f"{outp.stem}_{i+1}")
    urllib.request.urlretrieve(url, dest)
    print(f"OK {dest}  {dest.stat().st_size//1024} KB")
print(f"done in {int(time.time()-t0)}s via Replicate")
