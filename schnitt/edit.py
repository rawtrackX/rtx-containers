"""rtx-schnitt Kern v1.0 (17.10.2026): baut aus einem Schnittplan (JSON) ein fertiges Video mit FFmpeg.
Ersatz für CapCut auf Salad (CEO 17.10.): Clips zuschneiden/aneinanderreihen, Übergänge, Musik, Untertitel, Texteinblendungen, Formate."""
import json, os, subprocess, tempfile

FORMATS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350)}
FONT = os.environ.get("RTX_FONT", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")

def _run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("ffmpeg: " + p.stderr[-1200:])
    return p

def duration(path):
    out = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path]).stdout
    return float(json.loads(out)["format"]["duration"])

def has_audio(path):
    out = _run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "json", path]).stdout
    return bool(json.loads(out).get("streams"))

def _esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%").replace(",", "\\,")

def normalize(src, dst, w, h, fps, start=None, end=None, fit="crop", keep_audio=True):
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}" if fit == "crop"
          else f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2")
    vf += f",fps={fps},setsar=1,format=yuv420p"
    cmd = ["ffmpeg", "-y", "-hide_banner"]
    if start is not None:
        cmd += ["-ss", str(start)]
    if end is not None:
        cmd += ["-to", str(end)]
    cmd += ["-i", src]
    if not (keep_audio and has_audio(src)):
        cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
        amap = ["-map", "0:v:0", "-map", "1:a:0", "-shortest"]
    else:
        amap = ["-map", "0:v:0", "-map", "0:a:0"]
    cmd += ["-vf", vf, *amap, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-ar", "48000", "-ac", "2", dst]
    _run(cmd)
    return dst

def concat(segs, dst, transition=None):
    if not transition or len(segs) < 2:
        lst = dst + ".txt"
        with open(lst, "w") as f:
            for s in segs:
                f.write(f"file '{s}'\n")
        _run(["ffmpeg", "-y", "-hide_banner", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", dst])
        os.remove(lst)
        return dst
    d = float(transition.get("duration", 0.5)); kind = transition.get("type", "fade")
    if kind not in ("fade", "fadeblack", "fadewhite", "wipeleft", "wiperight", "slideleft", "slideright", "dissolve", "circleopen"):
        raise ValueError("Übergang unbekannt")
    cmd = ["ffmpeg", "-y", "-hide_banner"]
    for s in segs:
        cmd += ["-i", s]
    fc, off, lv, la = [], 0.0, "[0:v]", "[0:a]"
    for i in range(1, len(segs)):
        off += duration(segs[i - 1]) - d
        fc.append(f"{lv}[{i}:v]xfade=transition={kind}:duration={d}:offset={off:.3f}[v{i}]")
        fc.append(f"{la}[{i}:a]acrossfade=d={d}[a{i}]")
        lv, la = f"[v{i}]", f"[a{i}]"
    cmd += ["-filter_complex", ";".join(fc), "-map", lv, "-map", la, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", dst]
    _run(cmd)
    return dst

def _ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

def finish(src, dst, w, h, subtitles=None, texts=None, music=None, keep_clip_audio=True, loudnorm=True):
    work = os.path.dirname(dst)
    vf = []
    if subtitles:
        srt = os.path.join(work, "subs.srt")
        with open(srt, "w", encoding="utf-8") as f:
            for i, s in enumerate(subtitles, 1):
                f.write(f"{i}\n{_ts(float(s['start']))} --> {_ts(float(s['end']))}\n{str(s['text']).strip()}\n\n")
        size = max(16, int(h / 28 if h > w else h / 18))
        vf.append(f"subtitles={srt}:force_style='FontName=DejaVu Sans,Bold=1,FontSize={int(size * 288 / h) if h else 18},Outline=2,Shadow=0,MarginV=60,Alignment=2'")
    for k, t in enumerate(texts or []):
        tf = os.path.join(work, f"text{k}.txt")
        with open(tf, "w", encoding="utf-8") as f:
            f.write(str(t["text"]))
        y = {"top": "h*0.08", "center": "(h-text_h)/2", "bottom": "h*0.82"}.get(t.get("position", "top"), "h*0.08")
        fs = int(t.get("size", int(w / 14)))
        en = f":enable='between(t,{float(t.get('start', 0))},{float(t.get('end', 1e9))})'"
        vf.append(f"drawtext=fontfile={FONT}:textfile={tf}:expansion=none:fontcolor=white:fontsize={fs}:borderw=4:bordercolor=black:x=(w-text_w)/2:y={y}{en}")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-i", src]
    fc = []
    vin = "[0:v]"
    if vf:
        fc.append(f"{vin}{','.join(vf)}[vo]"); vout = "[vo]"
    else:
        vout = "0:v"
    if music:
        cmd += ["-stream_loop", "-1", "-i", music["path"]]
        vol = float(music.get("volume", 0.3))
        if keep_clip_audio:
            fc.append(f"[1:a]volume={vol}[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=2[am]")
        else:
            fc.append(f"[1:a]volume={vol}[am]")
        aout = "[am]"
    else:
        aout = "0:a"
    if loudnorm:
        src_a = aout if aout.startswith("[") else "[0:a]"
        fc.append(f"{src_a}loudnorm=I=-14:TP=-1.5:LRA=11[an]"); aout = "[an]"
    if fc:
        cmd += ["-filter_complex", ";".join(fc)]
    cmd += ["-map", vout, "-map", aout, "-t", f"{duration(src):.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", dst]
    _run(cmd)
    return dst

def build(plan, fetch, workdir=None):
    """plan: siehe app.py. fetch(url, suffix) -> lokaler Pfad. Gibt Pfad der fertigen Datei zurück."""
    work = workdir or tempfile.mkdtemp(dir=os.environ.get("RTX_WORK", "/tmp"))
    os.makedirs(work, exist_ok=True)
    w, h = FORMATS.get(plan.get("format", "9:16"), FORMATS["9:16"])
    fps = int(plan.get("fps", 30)); fit = plan.get("fit", "crop")
    if not plan.get("clips"):
        raise ValueError("clips fehlt")
    segs = []
    for i, c in enumerate(plan["clips"]):
        src = c.get("path") or fetch(c["url"], ".mp4")
        segs.append(normalize(src, os.path.join(work, f"seg{i:03d}.mp4"), w, h, fps, c.get("start"), c.get("end"), fit, plan.get("keep_clip_audio", True)))
    joined = concat(segs, os.path.join(work, "joined.mp4"), plan.get("transition"))
    music = None
    if plan.get("music"):
        m = plan["music"]; music = {"path": m.get("path") or fetch(m["url"], ".mp3"), "volume": m.get("volume", 0.3)}
    return finish(joined, os.path.join(work, "final.mp4"), w, h, plan.get("subtitles"), plan.get("texts"), music, plan.get("keep_clip_audio", True), plan.get("loudnorm", True))
