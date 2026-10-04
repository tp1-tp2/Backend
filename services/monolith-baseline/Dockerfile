# For GPU baseline runs, replace base image with:
# FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04
FROM python:3.11-slim AS builder
WORKDIR /app
# ffmpeg (audio conversion, ported from audio-processor) + libsndfile1 (Whisper
# audio decode, ported from asr-service) — this service needs both.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
# Before COPY . . so code changes do not redo the conversion.
# CTranslate2 copy of the same weights for ENGINE=ctranslate2 (same recipe as
# asr-service/Dockerfile, so both architectures run identical models in E3).
ARG MODEL_ID=QuechuaBase/whisper-base-qxp-finetuned
ENV HF_HUB_DISABLE_IMPLICIT_TOKEN=1
RUN ct2-transformers-converter --model ${MODEL_ID} --output_dir /models/ct2 --copy_files preprocessor_config.json     && python -c "from transformers import WhisperTokenizerFast; WhisperTokenizerFast.from_pretrained('${MODEL_ID}').save_pretrained('/tmp/tok')"     && cp /tmp/tok/tokenizer.json /models/ct2/ && rm -rf /tmp/tok
COPY . .
ENV PATH=/root/.local/bin:$PATH
VOLUME ["/root/.cache/huggingface"]
EXPOSE 8000
HEALTHCHECK --start-period=120s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
# --workers 1: the Whisper model is a module-level global loaded once, same
# constraint as asr-service. Note this as an architectural cost in E3's
# write-up: the split architecture runs non-ASR services at --workers 4;
# this monolith throttles EVERYTHING to 1 because ASR shares the process.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
