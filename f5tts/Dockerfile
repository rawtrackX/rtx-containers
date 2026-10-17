FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg git && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "f5-tts>=1.1,<2" fastapi==0.115.0 uvicorn==0.30.6 pydantic==2.9.2
WORKDIR /app
COPY common/rtxio.py f5tts/app.py /app/
ENV RTX_WORK=/tmp PYTHONUNBUFFERED=1 F5_MODEL=F5TTS_v1_Base
EXPOSE 3000
CMD ["uvicorn", "app:app", "--host", "::", "--port", "3000"]
