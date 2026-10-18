"""rtx-whisper v1.0 (17.10.2026): Transkription mit faster-whisper (GPU, sonst CPU int8). Port 3000, /ready, /run."""
import os, threading
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import rtxio

app = FastAPI(title="rtx-whisper")
MODEL_NAME = os.environ.get("WHISPER_MODEL", "large-v3")
_model = None
_err = None

def _load():
    global _model, _err
    try:
        from faster_whisper import WhisperModel
        try:
            _model = WhisperModel(MODEL_NAME, device="cuda", compute_type="float16")
        except Exception:
            _model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
    except Exception as e:  # pragma: no cover
        _err = str(e)

threading.Thread(target=_load, daemon=True).start()

class RunReq(BaseModel):
    audio_url: str
    language: str | None = None
    word_timestamps: bool = False
    vad_filter: bool = True

@app.get("/ready")
def ready():
    if _model is None:
        raise HTTPException(503, _err or "Modell lädt")
    return {"ok": True, "model": MODEL_NAME}

@app.post("/run")
def run(r: RunReq):
    if _model is None:
        raise HTTPException(503, "Modell lädt")
    src = rtxio.download(r.audio_url, rtxio.ext_of(r.audio_url, ".wav"))
    try:
        segs, info = _model.transcribe(src, language=r.language, word_timestamps=r.word_timestamps, vad_filter=r.vad_filter)
        out = []
        for s in segs:
            d = {"start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip()}
            if r.word_timestamps and s.words:
                d["words"] = [{"start": round(w.start, 3), "end": round(w.end, 3), "word": w.word} for w in s.words]
            out.append(d)
        return {"ok": True, "language": info.language, "duration": info.duration, "text": " ".join(x["text"] for x in out), "segments": out, "input_sha256": rtxio.sha256_file(src)}
    finally:
        os.remove(src)


rtxio.enable_jobs(app)  # v1.1 (17.10.2026): asynchrone Aufträge /jobs/<pfad>
