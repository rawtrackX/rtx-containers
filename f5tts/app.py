"""rtx-f5tts v1.0 (17.10.2026): Sprachausgabe mit F5-TTS (ersetzt XTTS, CEO). Port 3000, /ready, /run."""
import os, tempfile, threading
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import rtxio

app = FastAPI(title="rtx-f5tts")
_tts = None
_err = None

def _load():
    global _tts, _err
    try:
        from f5_tts.api import F5TTS
        _tts = F5TTS(model=os.environ.get("F5_MODEL", "F5TTS_v1_Base"))
    except Exception as e:  # pragma: no cover
        _err = str(e)

threading.Thread(target=_load, daemon=True).start()

class RunReq(BaseModel):
    ref_audio_url: str
    ref_text: str = ""
    gen_text: str
    speed: float = 1.0
    output_put_url: str

@app.get("/ready")
def ready():
    if _tts is None:
        raise HTTPException(503, _err or "Modell lädt")
    return {"ok": True}

@app.post("/run")
def run(r: RunReq):
    if _tts is None:
        raise HTTPException(503, "Modell lädt")
    if not r.gen_text.strip() or len(r.gen_text) > 20000:
        raise HTTPException(400, "gen_text leer oder zu lang")
    ref = rtxio.download(r.ref_audio_url, rtxio.ext_of(r.ref_audio_url, ".wav"))
    out = tempfile.mktemp(suffix=".wav", dir=os.environ.get("RTX_WORK", "/tmp"))
    try:
        _tts.infer(ref_file=ref, ref_text=r.ref_text, gen_text=r.gen_text, speed=r.speed, file_wave=out)
        return {"ok": True, "output": rtxio.upload(out, r.output_put_url, "audio/wav")}
    finally:
        for f in (ref, out):
            if os.path.exists(f):
                os.remove(f)


rtxio.enable_jobs(app)  # v1.1 (17.10.2026): asynchrone Aufträge /jobs/<pfad>
