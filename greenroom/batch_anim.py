#!/usr/bin/env python3
"""Batch Seedance 2.0 video generator (parallel). Reads a jobs JSON.

Job fields:
  name        label
  image       first-frame keyframe path
  last        optional last-frame path (default = image -> seamless loop)
  out         output mp4 path
  prompt      motion prompt
  resolution  default 480p
  duration    default 4
  aspect      default 1:1
  model       default bytedance/seedance-2.0-fast
Writes a spend line per clip to out/SPEND.log.
"""
import sys, json, time, base64, pathlib, urllib.request, urllib.error, concurrent.futures, threading
from keys import replicate_token

MODEL = "bytedance/seedance-2.0-fast"       # per-job "model" overrides this
TOK = replicate_token()
PRICE = {                                   # $/sec, measured
    "bytedance/seedance-2.0-fast": {"480p": 0.045, "720p": 0.099},
    "bytedance/seedance-2.0":      {"480p": 0.092, "720p": 0.198},
}
_lock = threading.Lock()
_spend = [0.0]


def data_uri(p):
    return "data:image/png;base64," + base64.b64encode(pathlib.Path(p).read_bytes()).decode()


def api(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            return json.load(urllib.request.urlopen(req, timeout=90))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(5 * (attempt + 1)); continue
            print("HTTP", e.code, e.read().decode()[:300]); raise


def one(j):
    out = pathlib.Path(j["out"])
    if out.exists() and out.stat().st_size > 10000:
        print(f"  {j['name']:22} skip (exists)"); return True
    res = j.get("resolution", "480p"); dur = j.get("duration", 4)
    model = j.get("model", MODEL)
    inp = {"prompt": j["prompt"], "image": data_uri(j["image"]),
           "last_frame_image": data_uri(j.get("last", j["image"])),
           "resolution": res, "duration": dur, "aspect_ratio": j.get("aspect", "1:1"),
           "generate_audio": False, "seed": 7}
    try:
        pred = api("POST", f"https://api.replicate.com/v1/models/{model}/predictions", {"input": inp})
        get_url = pred["urls"]["get"]; t0 = time.time()
        while pred["status"] not in ("succeeded", "failed", "canceled"):
            time.sleep(5); pred = api("GET", get_url)
        if pred["status"] != "succeeded":
            print(f"  {j['name']:22} FAILED {json.dumps(pred.get('error'))[:160]}"); return False
        url = pred["output"] if isinstance(pred["output"], str) else pred["output"][0]
        out.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, out)
        cost = PRICE.get(model, PRICE[MODEL]).get(res, 0.092) * dur
        with _lock:
            _spend[0] += cost
            pathlib.Path("out/SPEND.log").open("a").write(f"{j['name']}\t{res}\t{dur}s\t${cost:.3f}\n")
        print(f"  {j['name']:22} OK {out.stat().st_size//1024}KB {int(time.time()-t0)}s  ${cost:.2f}")
        return True
    except Exception as e:
        print(f"  {j['name']:22} ERR {type(e).__name__}: {str(e)[:140]}"); return False


def main():
    jobs = json.loads(pathlib.Path(sys.argv[1]).read_text())
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    print(f"{len(jobs)} video jobs, {workers} parallel")
    ok = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(one, jobs):
            ok += 1 if r else 0
    print(f"\ndone: {ok}/{len(jobs)}  batch spend: ${_spend[0]:.2f}")


if __name__ == "__main__":
    main()
