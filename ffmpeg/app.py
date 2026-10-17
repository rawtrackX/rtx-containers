"""rtx-ffmpeg v1.0 (17.10.2026): FFmpeg als HTTP-Dienst für Salad. Port 3000, /ready, /probe, /loudness, /run."""
import json, os, re, subprocess, tempfile
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import rtxio

app = FastAPI(title="rtx-ffmpeg")
SAFE_ARG = re.compile(r"^[A-Za-z0-9_\-\.:=,/+\[\];@%]+$")

class RunReq(BaseModel):
    input_url: str
    args: list[str] = []
    output_ext: str = ".mp4"
    output_put_url: str
    content_type: str = "application/octet-stream"

class UrlReq(BaseModel):
    input_url: str

@app.get("/ready")
def ready():
    subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
    return {"ok": True}

def _clean_args(args):
    for a in args:
        if not SAFE_ARG.match(a) or "://" in a or a.startswith("/") or ".." in a:
            raise HTTPException(400, f"Argument nicht erlaubt: {a}")
    return args

@app.post("/probe")
def probe(r: UrlReq):
    src = rtxio.download(r.input_url, rtxio.ext_of(r.input_url, ".bin"))
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", src], check=True, capture_output=True, text=True)
        return json.loads(out.stdout)
    finally:
        os.remove(src)

@app.post("/loudness")
def loudness(r: UrlReq):
    src = rtxio.download(r.input_url, rtxio.ext_of(r.input_url, ".wav"))
    try:
        p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-af", "loudnorm=print_format=json", "-f", "null", "-"], capture_output=True, text=True)
        m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p.stderr, re.S)
        if not m:
            raise HTTPException(500, "Messung fehlgeschlagen")
        return json.loads(m.group(0))
    finally:
        os.remove(src)

@app.post("/run")
def run(r: RunReq):
    if not re.match(r"^\.[a-z0-9]{2,5}$", r.output_ext):
        raise HTTPException(400, "output_ext ungültig")
    src = rtxio.download(r.input_url, rtxio.ext_of(r.input_url, ".bin"))
    dst = tempfile.mktemp(suffix=r.output_ext, dir=os.environ.get("RTX_WORK", "/tmp"))
    try:
        p = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-i", src, *_clean_args(r.args), dst], capture_output=True, text=True, timeout=3600)
        if p.returncode != 0:
            raise HTTPException(500, p.stderr[-1500:])
        return {"ok": True, "output": rtxio.upload(dst, r.output_put_url, r.content_type)}
    finally:
        for f in (src, dst):
            if os.path.exists(f):
                os.remove(f)
