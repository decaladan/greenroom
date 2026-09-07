#!/usr/bin/env python3
"""Seamless-loop a keyframe through Seedance (Replicate). first frame == last frame.
House model: bytedance/seedance-2.0-fast (~$0.18/4s clip).

Usage:
  python3 gen_video.py <keyframe.png> <out.mp4> "<motion prompt>" [resolution] [duration] [model] [aspect]
"""
import sys, json, time, base64, pathlib, urllib.request, urllib.error
from keys import replicate_token

MODEL = "bytedance/seedance-2.0-fast"
TOK = replicate_token()


def data_uri(path):
    b = pathlib.Path(path).read_bytes()
    return "data:image/png;base64," + base64.b64encode(b).decode()


def api(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": f"Bearer {TOK}",
                                          "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode()[:500]); raise


def main():
    kf, out, prompt = sys.argv[1], sys.argv[2], sys.argv[3]
    resolution = sys.argv[4] if len(sys.argv) > 4 else "480p"
    duration = int(sys.argv[5]) if len(sys.argv) > 5 else 4
    model = sys.argv[6] if len(sys.argv) > 6 else MODEL
    aspect = sys.argv[7] if len(sys.argv) > 7 else "1:1"
    uri = data_uri(kf)
    inp = {
        "prompt": prompt,
        "image": uri,
        "last_frame_image": uri,          # identical -> seamless loop
        "resolution": resolution,
        "duration": duration,
        "aspect_ratio": aspect,
        "generate_audio": False,
        "seed": 7,
    }
    print(f"creating prediction  model={model} res={resolution} dur={duration}s ...")
    pred = api("POST", f"https://api.replicate.com/v1/models/{model}/predictions",
               {"input": inp})
    pid = pred["id"]
    get_url = pred["urls"]["get"]
    t0 = time.time()
    while pred["status"] not in ("succeeded", "failed", "canceled"):
        time.sleep(4)
        pred = api("GET", get_url)
        print(f"  [{int(time.time()-t0):3d}s] {pred['status']}")
    if pred["status"] != "succeeded":
        print("FAILED:", json.dumps(pred.get("error"))[:400]); sys.exit(1)
    url = pred["output"] if isinstance(pred["output"], str) else pred["output"][0]
    print("output:", url)
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, out)
    kb = pathlib.Path(out).stat().st_size // 1024
    print(f"OK {out}  {kb} KB  metrics={json.dumps(pred.get('metrics',{}))}")


if __name__ == "__main__":
    main()
