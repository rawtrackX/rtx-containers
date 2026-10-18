"""rtx-schnitt v1.0 (17.10.2026): automatischer Videoschnitt per Schnittplan (Ersatz für CapCut auf Salad, CEO 17.10.).
Port 3000. /ready, /run. Eingaben per https-URL, Ergebnis per PUT auf vorsignierte URL.
Schnittplan: {format: 9:16|16:9|1:1|4:5, fps, fit: crop|pad, clips:[{url,start,end}], transition:{type,duration},
 music:{url,volume}, keep_clip_audio, subtitles:[{start,end,text}] (z. B. aus rtx-whisper), texts:[{text,start,end,position,size}], loudnorm, output_put_url}"""
import shutil, subprocess, tempfile, os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import rtxio, edit

app = FastAPI(title="rtx-schnitt")

class Clip(BaseModel):
    url: str
    start: float | None = None
    end: float | None = None

class Plan(BaseModel):
    format: str = "9:16"
    fps: int = 30
    fit: str = "crop"
    clips: list[Clip]
    transition: dict | None = None
    music: dict | None = None
    keep_clip_audio: bool = True
    subtitles: list[dict] | None = None
    texts: list[dict] | None = None
    loudnorm: bool = True
    output_put_url: str

@app.get("/ready")
def ready():
    subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
    return {"ok": True, "formate": list(edit.FORMATS)}

@app.post("/run")
def run(p: Plan):
    if p.format not in edit.FORMATS or p.fit not in ("crop", "pad") or not (1 <= p.fps <= 60) or len(p.clips) > 200:
        raise HTTPException(400, "Schnittplan ungültig")
    work = tempfile.mkdtemp(dir=os.environ.get("RTX_WORK", "/tmp"))
    try:
        plan = p.model_dump()
        out = edit.build(plan, rtxio.download, work)
        return {"ok": True, "dauer_s": round(edit.duration(out), 2), "output": rtxio.upload(out, p.output_put_url, "video/mp4")}
    except (ValueError, RuntimeError) as e:
        raise HTTPException(500, str(e)[:1500])
    finally:
        shutil.rmtree(work, ignore_errors=True)


rtxio.enable_jobs(app)  # v1.1 (17.10.2026): asynchrone Aufträge /jobs/<pfad>
