FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "audio-separator[gpu]>=0.30,<1" fastapi==0.115.0 uvicorn==0.30.6 pydantic==2.9.2
WORKDIR /app
COPY common/rtxio.py uvr/app.py /app/
ENV RTX_WORK=/tmp PYTHONUNBUFFERED=1 UVR_MODEL_DIR=/models
EXPOSE 3000
CMD ["uvicorn", "app:app", "--host", "::", "--port", "3000"]
