FROM nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip ffmpeg && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir faster-whisper==1.0.3 fastapi==0.115.0 uvicorn==0.30.6 pydantic==2.9.2
WORKDIR /app
COPY common/rtxio.py whisper/app.py /app/
ENV RTX_WORK=/tmp PYTHONUNBUFFERED=1 WHISPER_MODEL=large-v3
EXPOSE 3000
CMD ["python3", "-m", "uvicorn", "app:app", "--host", "::", "--port", "3000"]
