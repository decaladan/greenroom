#!/usr/bin/env python3
"""Batch gpt-image-2 generation via Replicate. Jobs JSON: [{ref, out, prompt, aspect?}].
Runs N workers in parallel, prints per-job status.

Usage: python3 batch_gen.py <jobs.json> [workers]
"""
import sys, json, time, base64, mimetypes, pathlib, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from keys import replicate_token

TOK = replicate_token()
jobs = json.load(open(sys.argv[1]))
workers = int(sys.argv[2]) if len(sys.argv) > 2 else 4


def data_uri(p):
    mime = mimetypes.guess_type(p)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(pathlib.Path(p).read_bytes()).decode()


def api(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))


def run(job):
    t0 = time.time()
    try:
        inp = {
            "prompt": job["prompt"],
            "input_images": [data_uri(r) for r in job["ref"].split(",")],
            "quality": "medium",
            "aspect_ratio": job.get("aspect", "1:1"),
            "background": "opaque",
            "output_format": "png",
            "number_of_images": 1,
        }
        pred = api("POST", "https://api.replicate.com/v1/models/openai/gpt-image-2/predictions", {"input": inp})
        while pred["status"] not in ("succeeded", "failed", "canceled"):
            time.sleep(3)
            pred = api("GET", pred["urls"]["get"])
        if pred["status"] != "succeeded":
            return f"FAIL {job['out']}  {str(pred.get('error'))[:200]}"
        o = pred["output"]
        url = o[0] if isinstance(o, list) else o
        out = pathlib.Path(job["out"])
        out.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, out)
        return f"OK   {job['out']}  {out.stat().st_size//1024} KB  {int(time.time()-t0)}s"
    except Exception as e:
        return f"FAIL {job['out']}  {type(e).__name__}: {str(e)[:200]}"


with ThreadPoolExecutor(max_workers=workers) as ex:
    for res in ex.map(run, jobs):
        print(res, flush=True)
print(f"done: {len(jobs)} jobs")
