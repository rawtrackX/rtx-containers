FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime
ENV DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "rvc-python>=0.1.5,<1" fastapi==0.115.0 uvicorn==0.30.6 pydantic==2.9.2
WORKDIR /app
COPY common/rtxio.py rvc/app.py /app/
ENV RTX_WORK=/tmp PYTHONUNBUFFERED=1 RVC_CACHE=/models
EXPOSE 3000
ARG SALAD_JOB_QUEUE_WORKER_VERSION=0.7.0
ADD https://github.com/SaladTechnologies/salad-cloud-job-queue-worker/releases/download/v${SALAD_JOB_QUEUE_WORKER_VERSION}/salad-http-job-queue-worker_x86_64.tar.gz /tmp/w.tgz
RUN tar -C /usr/local/bin -zxpf /tmp/w.tgz && rm -f /tmp/w.tgz
COPY --chmod=755 common/run.sh /app/run.sh
CMD ["/app/run.sh", "uvicorn", "app:app", "--host", "::", "--port", "3000"]