"""RTX Container gemeinsame E/A (v1.1, 17.10.2026: + enable_jobs). Eingaben nur per URL (z. B. vorsignierte Wasabi-GET-URL),
Ausgaben per HTTP PUT auf vorsignierte URLs. Keine Zugangsdaten im Image."""
import hashlib, os, tempfile, urllib.request, urllib.parse

MAX_BYTES = int(os.environ.get("RTX_MAX_INPUT_BYTES", str(4 * 1024 ** 3)))

def _check_url(url: str) -> str:
    u = urllib.parse.urlparse(url)
    if u.scheme != "https":
        raise ValueError("nur https-URLs erlaubt")
    return url

def download(url: str, suffix: str = "") -> str:
    _check_url(url)
    fd, path = tempfile.mkstemp(suffix=suffix, dir=os.environ.get("RTX_WORK", "/tmp"))
    n = 0
    with urllib.request.urlopen(url, timeout=600) as r, os.fdopen(fd, "wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            n += len(b)
            if n > MAX_BYTES:
                raise ValueError("Eingabe zu groß")
            f.write(b)
    return path

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def upload(path: str, put_url: str, content_type: str = "application/octet-stream") -> dict:
    _check_url(put_url)
    size = os.path.getsize(path)
    sha = sha256_file(path)
    with open(path, "rb") as f:
        req = urllib.request.Request(put_url, data=f, method="PUT", headers={"Content-Type": content_type, "Content-Length": str(size)})
        with urllib.request.urlopen(req, timeout=600) as r:
            status = r.status
    return {"bytes": size, "sha256": sha, "http": status}

def ext_of(url: str, default: str) -> str:
    p = urllib.parse.urlparse(url).path
    e = os.path.splitext(p)[1].lower()
    return e if e and len(e) <= 6 else default


# v1.1 (17.10.2026): asynchrone Aufträge – Salad-Gateway bricht Anfragen nach 100 s ab.
# POST /jobs/<pfad> (gleicher Body wie POST /<pfad>) -> 202 {"job_id"}; GET /jobs/<id> -> {"status": QUEUED|RUNNING|DONE|FAILED, "result"|"error"}.
# Ein Auftrag zur Zeit (GPU), weitere warten. Speicher nur im Prozess: Neustart -> 404, die Steuerung meldet dann FAILED.
def enable_jobs(app, allowed=("/run", "/probe", "/loudness")):
    import inspect, threading, time, uuid
    from fastapi import HTTPException, Request
    from fastapi.responses import JSONResponse
    from fastapi.routing import APIRoute
    jobs, lock, gpu = {}, threading.Lock(), threading.Semaphore(1)

    def _route(path):
        for r in app.routes:
            if isinstance(r, APIRoute) and r.path == path and "POST" in r.methods:
                return r
        return None

    def _work(jid, fn, req):
        with gpu:
            jobs[jid].update(status="RUNNING", started=time.time())
            try:
                res = fn(req)
                jobs[jid].update(status="DONE", result=res)
            except HTTPException as e:
                jobs[jid].update(status="FAILED", error={"http": e.status_code, "detail": str(e.detail)[-1500:]})
            except Exception as e:
                jobs[jid].update(status="FAILED", error={"http": 500, "detail": (type(e).__name__ + ": " + str(e))[-1500:]})
            jobs[jid]["finished"] = time.time()

    @app.post("/jobs/{name}", status_code=202)
    async def submit(name: str, request: Request):
        path = "/" + name
        r = _route(path)
        if path not in allowed or r is None:
            raise HTTPException(404, "unbekannter Pfad")
        params = list(inspect.signature(r.endpoint).parameters.values())
        model = params[0].annotation if params else None
        try:
            req = model(**(await request.json())) if model is not None else None
        except Exception as e:
            raise HTTPException(422, str(e)[:1500])
        jid = uuid.uuid4().hex
        with lock:
            if len(jobs) > 200:
                for k in sorted(jobs, key=lambda k: jobs[k]["created"])[:100]:
                    if jobs[k]["status"] in ("DONE", "FAILED"):
                        jobs.pop(k, None)
            jobs[jid] = {"status": "QUEUED", "path": path, "created": time.time()}
        threading.Thread(target=_work, args=(jid, r.endpoint, req), daemon=True).start()
        return JSONResponse({"job_id": jid, "status": "QUEUED"}, status_code=202)

    @app.get("/jobs/{jid}")
    def status(jid: str):
        j = jobs.get(jid)
        if j is None:
            raise HTTPException(404, "Auftrag unbekannt (Neustart?)")
        return {"job_id": jid, **j}
