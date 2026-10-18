"""rtx-rvc v1.0 (17.10.2026): Stimmumwandlung mit RVC (rvc-python). Stimmmodell (.pth/.index) per URL je Auftrag, wird gecacht. Port 3000, /ready, /run."""
import hashlib, os, tempfile, threading
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import rtxio

app = FastAPI(title="rtx-rvc")
CACHE = os.environ.get("RVC_CACHE", "/models")
_lock = threading.Lock()
_rvc = None
_loaded = None

class RunReq(BaseModel):
    audio_url: str
    model_url: str
    index_url: str | None = None
    f0_up_key: int = 0
    f0_method: str = "rmvpe"
    index_rate: float = 0.5
    output_put_url: str

def _cached(url, ext):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, hashlib.sha256(url.split("?")[0].encode()).hexdigest()[:16] + ext)
    if not os.path.exists(p):
        os.replace(rtxio.download(url, ext), p)
    return p

@app.get("/ready")
def ready():
    import rvc_python  # noqa: F401
    return {"ok": True}

@app.post("/run")
def run(r: RunReq):
    global _rvc, _loaded
    if r.f0_method not in ("rmvpe", "harvest", "crepe", "pm"):
        raise HTTPException(400, "f0_method ungültig")
    from rvc_python.infer import RVCInference
    src = rtxio.download(r.audio_url, rtxio.ext_of(r.audio_url, ".wav"))
    out = tempfile.mktemp(suffix=".wav", dir=os.environ.get("RTX_WORK", "/tmp"))
    try:
        with _lock:
            if _rvc is None:
                try:
                    _rvc = RVCInference(device="cuda:0")
                except Exception:
                    _rvc = RVCInference(device="cpu")
            m = _cached(r.model_url, ".pth")
            idx = _cached(r.index_url, ".index") if r.index_url else ""
            if _loaded != (m, idx):
                _rvc.load_model(m, index_path=idx)
                _loaded = (m, idx)
            _rvc.set_params(f0up_key=r.f0_up_key, f0method=r.f0_method, index_rate=r.index_rate)
            _rvc.infer_file(src, out)
        return {"ok": True, "output": rtxio.upload(out, r.output_put_url, "audio/wav")}
    finally:
        for f in (src, out):
            if os.path.exists(f):
                os.remove(f)


rtxio.enable_jobs(app)  # v1.1 (17.10.2026): asynchrone Aufträge /jobs/<pfad>
