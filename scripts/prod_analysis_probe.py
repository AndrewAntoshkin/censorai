"""Upload synthetic videos to prod and report analysis outcomes + last_error."""
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
DEBUG_SECRET = os.environ.get("DEBUG_SECRET", "censor-demo-2026")

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
CREATED: list[str] = []


def req(method, url, body=None, headers=None, timeout=120):
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


def debug_job(**payload):
    st, raw = req(
        "POST",
        f"{BASE}/api/files/debug-job",
        {"secret": DEBUG_SECRET, **payload},
        timeout=60,
    )
    if st != 200:
        return {"error": f"debug {st}: {raw[:200]}"}
    return json.loads(raw)


def gen_mp4(path: str, seconds: int, size: str = "320x180") -> int:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size={size}:rate=10",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100",
            "-t",
            str(seconds),
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            path,
        ],
        check=True,
    )
    return os.path.getsize(path)


def run_case(name: str, filename: str, seconds: int, poll_timeout: int) -> dict:
    print(f"\n=== {name} ({seconds}s) ===", flush=True)
    tmp = os.path.join(tempfile.gettempdir(), filename)
    size = gen_mp4(tmp, seconds)
    print(f"  size {size / 1024 / 1024:.1f} MB", flush=True)

    st, raw = req(
        "POST",
        f"{BASE}/api/files/presign-upload",
        {"filename": filename, "size": size, "content_type": "video/mp4"},
    )
    if st != 200:
        return {"case": name, "result": "FAIL", "stage": "presign", "detail": raw[:200].decode()}

    presign = json.loads(raw)
    with open(tmp, "rb") as f:
        body = f.read()
    t0 = time.time()
    pst, _ = req(
        presign.get("method", "PUT"),
        presign["upload_url"],
        body=body,
        headers=presign.get("headers") or {},
        timeout=600,
    )
    if not (200 <= pst < 300):
        return {"case": name, "result": "FAIL", "stage": "r2_put", "detail": str(pst)}
    print(f"  uploaded {time.time() - t0:.1f}s", flush=True)

    st, raw = req(
        "POST",
        f"{BASE}/api/files/from-blob?auto_analyze=true",
        {
            "filename": filename,
            "size": size,
            "storage_path": presign["storage_path"],
            "duration_seconds": seconds,
        },
    )
    if st not in (200, 201):
        return {"case": name, "result": "FAIL", "stage": "from_blob", "detail": raw[:300].decode()}
    fid = json.loads(raw)["id"]
    CREATED.append(fid)
    print(f"  file_id={fid}", flush=True)

    deadline = time.time() + poll_timeout
    last = None
    while time.time() < deadline:
        time.sleep(8)
        try:
            debug_job(file_id=fid, poll=True)
        except Exception:
            pass
        try:
            _, raw = req("GET", f"{BASE}/api/files/{fid}", timeout=120)
        except Exception as e:
            print(f"  poll err {e}", flush=True)
            continue
        v = json.loads(raw)
        cur = (v.get("status"), v.get("progress"))
        if cur != last:
            print(f"  status={cur[0]} progress={cur[1]}", flush=True)
            last = cur
        if v.get("status") == "analyzed":
            return {
                "case": name,
                "result": "PASS",
                "stage": "analyzed",
                "file_id": fid,
                "detail": v.get("analysis_id"),
            }
        if v.get("status") == "error":
            info = debug_job(file_id=fid)
            item = (info.get("items") or [{}])[0]
            err = item.get("last_error") or "status=error"
            pred = item.get("replicate_prediction_id")
            return {
                "case": name,
                "result": "FAIL",
                "stage": "analysis",
                "file_id": fid,
                "detail": err,
                "prediction_id": pred,
            }
    return {"case": name, "result": "TIMEOUT", "stage": "poll", "file_id": fid, "detail": str(last)}


def main():
    st, _ = req("POST", f"{BASE}/api/auth/login", {"email": EMAIL, "password": PASSWORD})
    assert st == 200, "login failed"
    print(f"[login] {EMAIL}", flush=True)

    cases = [
        ("30s tiny", "probe_30s.mp4", 30, 180),
        ("2min short", "probe_2min.mp4", 120, 420),
        ("5min medium", "probe_5min.mp4", 300, 600),
    ]
    results = []
    for args in cases:
        try:
            results.append(run_case(*args))
        except Exception as e:
            results.append({"case": args[0], "result": "FAIL", "stage": "exc", "detail": str(e)[:300]})
        r = results[-1]
        print(f"  -> {r['result']} ({r.get('stage')})", flush=True)
        if r.get("detail"):
            print(f"     {str(r['detail'])[:200]}", flush=True)

    print("\n======== SUMMARY ========", flush=True)
    for r in results:
        print(
            f"{r['result']:8} | {r['case']:12} | {r.get('stage',''):10} | "
            f"{str(r.get('detail',''))[:120]}"
        )
    print(f"PASS {sum(1 for r in results if r['result']=='PASS')}/{len(results)}", flush=True)

    print("\n[cleanup]", flush=True)
    for fid in CREATED:
        try:
            req("DELETE", f"{BASE}/api/files/{fid}", timeout=60)
            print(f"  deleted {fid}", flush=True)
        except Exception as e:
            print(f"  delete {fid}: {e}", flush=True)


if __name__ == "__main__":
    main()
