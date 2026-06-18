"""Quick prod e2e: upload 3 videos of different lengths and run analysis to completion."""
import http.cookiejar
import json
import os
import subprocess
import tempfile
import time
import urllib.request

BASE = os.environ.get("BASE", "https://censorai.vercel.app")
EMAIL = os.environ.get("E2E_EMAIL", "redaktor@5kanal.ru")
PASSWORD = os.environ.get("E2E_PASSWORD", "5Kanal-Redaktor-2026")

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
CREATED = []


def _req(method, url, body=None, headers=None, timeout=120):
    h = dict(headers or {})
    data = None
    if isinstance(body, (bytes, bytearray)):
        data = body
    elif body is not None:
        data = json.dumps(body).encode()
        h.setdefault("Content-Type", "application/json")
    r = urllib.request.Request(url, data=data, method=method, headers=h)
    with opener.open(r, timeout=timeout) as resp:
        return resp.status, resp.read()


def login():
    st, raw = _req("POST", f"{BASE}/api/auth/login", {"email": EMAIL, "password": PASSWORD})
    assert st == 200, f"login {st} {raw[:200]}"
    print(f"[login] OK {EMAIL}", flush=True)


def gen(path, seconds):
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=10",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
        "-t", str(seconds), "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", path,
    ], check=True)
    return os.path.getsize(path)


def run_case(name, filename, seconds, poll_timeout):
    print(f"\n=== {name} ({filename}, {seconds}s = {seconds/60:.0f}min) ===", flush=True)
    tmp = os.path.join(tempfile.gettempdir(), filename)
    size = gen(tmp, seconds)
    print(f"  generated {size/1024/1024:.1f} MB", flush=True)

    st, raw = _req("POST", f"{BASE}/api/files/presign-upload",
                   {"filename": filename, "size": size, "content_type": "video/mp4"})
    if st != 200:
        return {"case": name, "result": "FAIL", "stage": "presign", "detail": f"{st} {raw[:200]}"}
    presign = json.loads(raw)

    with open(tmp, "rb") as f:
        body = f.read()
    t0 = time.time()
    pst, _ = _req(presign.get("method", "PUT"), presign["upload_url"], body=body,
                  headers=presign.get("headers") or {}, timeout=600)
    if not (200 <= pst < 300):
        return {"case": name, "result": "FAIL", "stage": "r2_put", "detail": str(pst)}
    print(f"  uploaded in {time.time()-t0:.1f}s", flush=True)

    st, raw = _req("POST", f"{BASE}/api/files/from-blob?auto_analyze=true",
                   {"filename": filename, "size": size,
                    "storage_path": presign["storage_path"], "duration_seconds": seconds})
    if st not in (200, 201):
        return {"case": name, "result": "FAIL", "stage": "from_blob", "detail": f"{st} {raw[:300]}"}
    fid = json.loads(raw)["id"]
    CREATED.append(fid)
    print(f"  registered id={fid}", flush=True)

    deadline = time.time() + poll_timeout
    last = None
    while time.time() < deadline:
        time.sleep(6)
        try:
            _, raw = _req("GET", f"{BASE}/api/files/{fid}", timeout=120)
        except Exception as e:  # noqa: BLE001
            print(f"  poll err {str(e)[:100]}", flush=True)
            continue
        v = json.loads(raw)
        cur = (v.get("status"), v.get("progress"))
        if cur != last:
            print(f"  status={cur[0]} progress={cur[1]}", flush=True)
            last = cur
        if v.get("status") == "analyzed":
            return {"case": name, "result": "PASS", "stage": "analyzed",
                    "detail": f"analysis_id={v.get('analysis_id')}"}
        if v.get("status") == "error":
            return {"case": name, "result": "FAIL", "stage": "analysis",
                    "detail": v.get("error") or "status=error"}
    return {"case": name, "result": "TIMEOUT", "stage": "poll", "detail": str(last)}


def cleanup():
    print("\n[cleanup] deleting test files...", flush=True)
    for fid in CREATED:
        try:
            _req("DELETE", f"{BASE}/api/files/{fid}", timeout=60)
            print(f"  deleted {fid}", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"  delete {fid} failed: {str(e)[:100]}", flush=True)


def main():
    login()
    cases = [
        ("SHORT ~2min",  "e2e_2min.mp4",  120,  300),
        ("MEDIUM ~20min", "e2e_20min.mp4", 1200, 600),
        ("LONG ~50min (seg)", "e2e_50min.mp4", 3000, 1500),
    ]
    results = []
    for c in cases:
        try:
            results.append(run_case(*c))
        except Exception as e:  # noqa: BLE001
            results.append({"case": c[0], "result": "FAIL", "stage": "exc", "detail": str(e)[:300]})
        print(f"  -> {results[-1]['result']} ({results[-1]['stage']})", flush=True)

    cleanup()

    print("\n================ SUMMARY ================", flush=True)
    for r in results:
        print(f"  {r['result']:8} | {r['case']:18} | {r['stage']:10} | {r.get('detail','')}", flush=True)
    npass = sum(1 for r in results if r["result"] == "PASS")
    print(f"\n  {npass}/{len(results)} PASSED", flush=True)
    print("=========================================", flush=True)


if __name__ == "__main__":
    main()
