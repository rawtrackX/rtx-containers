FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir fastapi==0.115.0 uvicorn==0.30.6 pydantic==2.9.2
WORKDIR /app
COPY common/rtxio.py schnitt/edit.py schnitt/app.py /app/
ENV RTX_WORK=/tmp PYTHONUNBUFFERED=1 RTX_FONT=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
EXPOSE 3000
CMD ["uvicorn", "app:app", "--host", "::", "--port", "3000"]
