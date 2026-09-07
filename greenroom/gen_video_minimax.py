#!/usr/bin/env python3
"""minimax/hailuo-2.3 on Replicate.

Schema (probed): prompt (required), first_frame_image (string),
duration in {6,10}, resolution in {"768p","1080p"}.  NO last_frame_image.

Usage: gen_video_minimax.py <first.png> <out.mp4> "<prompt>" [duration] [resolution]
"""
import sys, json, time, base64, pathlib, urllib.request, urllib.error
from keys import replicate_token

MODEL, TOK = "minimax/hailuo-2.3", replicate_token()

def data_uri(p):
    return "data:image/png;base64," + base64.b64encode(pathlib.Path(p).read_bytes()).decode()

def api(method, url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
        method=method, headers={"Authorization": f"Bearer {TOK}",
                                "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=90))
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode()[:500]); raise

kf, out, prompt = sys.argv[1], sys.argv[2], sys.argv[3]
dur = int(sys.argv[4]) if len(sys.argv) > 4 else 6
res = sys.argv[5] if len(sys.argv) > 5 else "1080p"

inp = {"prompt": prompt, "first_frame_image": data_uri(kf),
       "duration": dur, "resolution": res}
print(f"creating prediction  model={MODEL} dur={dur}s res={res} ...")
pred = api("POST", f"https://api.replicate.com/v1/models/{MODEL}/predictions", {"input": inp})
t0 = time.time()
while pred["status"] not in ("succeeded", "failed", "canceled"):
    time.sleep(5)
    pred = api("GET", pred["urls"]["get"])
    print(f"  [{int(time.time()-t0):3d}s] {pred['status']}")
if pred["status"] != "succeeded":
    print("FAILED:", json.dumps(pred.get("error"))[:400]); sys.exit(1)
url = pred["output"] if isinstance(pred["output"], str) else pred["output"][0]
urllib.request.urlretrieve(url, out)
print(f"OK {out}  {pathlib.Path(out).stat().st_size//1024} KB  "
      f"metrics={json.dumps(pred.get('metrics', {}))}")
