"""Reproduce the 50min 500 and capture the real error body."""
import http.cookiejar
import json
import os
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

BASE = "https://censorai.vercel.app"
EMAIL = "redaktor@5kanal.ru"
PASSWORD = "5Kanal-Redaktor-2026"
SECONDS = int(os.environ.get("SECS", "3000"))

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def req(method, url, body=None, headers=None, timeout=300):
    h = dict(headers or {})
    data = None
    if isinstance(body, (bytes, bytearray)):
        data = body
    elif body is not None:
        data = json.dumps(body).encode()
        h.setdefault("Content-Type", "application/json")
    r = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with opener.open(r, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main():
    st, raw = req("POST", f"{BASE}/api/auth/login", {"email": EMAIL, "password": PASSWORD})
    print("login", st, flush=True)

    tmp = os.path.join(tempfile.gettempdir(), "repro_long.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=10",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
        "-t", str(SECONDS), "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", tmp,
    ], check=True)
    size = os.path.getsize(tmp)
    print(f"generated {size/1024/1024:.1f} MB ({SECONDS}s)", flush=True)

    st, raw = req("POST", f"{BASE}/api/files/presign-upload",
                  {"filename": "repro_long.mp4", "size": size, "content_type": "video/mp4"})
    print("presign", st, flush=True)
    presign = json.loads(raw)

    with open(tmp, "rb") as f:
        body = f.read()
    t0 = time.time()
    pst, _ = req(presign.get("method", "PUT"), presign["upload_url"], body=body,
                 headers=presign.get("headers") or {}, timeout=600)
    print(f"r2_put {pst} in {time.time()-t0:.1f}s", flush=True)

    # register WITHOUT auto-analyze (fast)
    st, raw = req("POST", f"{BASE}/api/files/from-blob",
                  {"filename": "repro_long.mp4", "size": size,
                   "storage_path": presign["storage_path"], "duration_seconds": SECONDS})
    print("from-blob(register)", st, raw[:200], flush=True)
    fid = json.loads(raw)["id"]
    print("id", fid, flush=True)

    # kick off analysis explicitly and capture the error body
    st, raw = req("POST", f"{BASE}/api/files/{fid}/analyze", timeout=300)
    print("analyze", st, flush=True)
    print("ANALYZE BODY:", raw.decode(errors="replace")[:1500], flush=True)

    # poll a bit
    for _ in range(10):
        time.sleep(6)
        _, raw = req("GET", f"{BASE}/api/files/{fid}", timeout=120)
        v = json.loads(raw)
        print("poll", v.get("status"), v.get("progress"), flush=True)
        if v.get("status") in ("analyzed", "error"):
            break

    req("DELETE", f"{BASE}/api/files/{fid}", timeout=60)
    print("cleaned up", fid, flush=True)


if __name__ == "__main__":
    main()
