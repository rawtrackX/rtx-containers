# rtx-containers

Öffentliche Container-Images der rawtrackX-Produktionslinie für SaladCloud (CEO-Entscheidung 72, 17.10.2026).
Nur Open-Source-Programme, keine Inhalte, keine Zugangsdaten. Eingaben per https-URL, Ausgaben per PUT auf vorsignierte URLs.

| Image | Programm | Endpunkte (Port 3000) |
|---|---|---|
| ghcr.io/rawtrackx/rtx-ffmpeg | FFmpeg | /ready, /probe, /loudness, /run |
| ghcr.io/rawtrackx/rtx-whisper | faster-whisper (large-v3) | /ready, /run |
| ghcr.io/rawtrackx/rtx-uvr | UVR-Modelle (python-audio-separator) | /ready, /run |
| ghcr.io/rawtrackx/rtx-f5tts | F5-TTS | /ready, /run |
| ghcr.io/rawtrackx/rtx-rvc | RVC (rvc-python) | /ready, /run |

Bild, Video und Musik laufen über das offizielle Salad-Image `ghcr.io/saladtechnologies/comfyui-api` (SDXL, Wan 2.1, ACE-Step).
Status: VORBEREITET – Bau über GitHub Actions (`.github/workflows/build.yml`).
