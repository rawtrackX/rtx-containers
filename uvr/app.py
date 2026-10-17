"""rtx-uvr v1.0 (17.10.2026): Stem-Trennung (UVR-Modelle über python-audio-separator). Port 3000, /ready, /run."""
import glob, os, shutil, tempfile
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import rtxio

app = FastAPI(title="rtx-uvr")
DEFAULT_MODEL = os.environ.get("UVR_MODEL", "model_bs_roformer_ep_317_sdr_12.9755.ckpt")
MODEL_DIR = os.environ.get("UVR_MODEL_DIR", "/models")

class RunReq(BaseModel):
    audio_url: str
    model: str | None = None
    output_format: str = "wav"
    output_put_urls: dict[str, str]  # z. B. {"vocals": "...", "instrumental": "..."}

@app.get("/ready")
def ready():
    import audio_separator  # noqa: F401
    return {"ok": True, "default_model": DEFAULT_MODEL}

@app.post("/run")
def run(r: RunReq):
    from audio_separator.separator import Separator
    if r.output_format not in ("wav", "flac", "mp3"):
        raise HTTPException(400, "output_format ungültig")
    src = rtxio.download(r.audio_url, rtxio.ext_of(r.audio_url, ".wav"))
    outdir = tempfile.mkdtemp(dir=os.environ.get("RTX_WORK", "/tmp"))
    try:
        sep = Separator(output_dir=outdir, output_format=r.output_format.upper(), model_file_dir=MODEL_DIR)
        sep.load_model(model_filename=r.model or DEFAULT_MODEL)
        files = sep.separate(src)
        res = {}
        for f in files:
            p = f if os.path.isabs(f) else os.path.join(outdir, f)
            name = os.path.basename(p).lower()
            for stem, url in r.output_put_urls.items():
                if f"({stem.lower()})" in name or f"_{stem.lower()}" in name:
                    res[stem] = rtxio.upload(p, url, "audio/" + r.output_format)
        missing = [s for s in r.output_put_urls if s not in res]
        return {"ok": not missing, "outputs": res, "missing": missing, "files": [os.path.basename(x) for x in files]}
    finally:
        os.remove(src)
        shutil.rmtree(outdir, ignore_errors=True)
