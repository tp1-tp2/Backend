# For GPU production use, replace base image with:
# FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04
FROM python:3.11-slim AS builder
WORKDIR /app
# libsndfile1: Whisper audio decode. ffmpeg: Opus/MP3 -> WAV decode for the
# E5 compressed-streaming path (codec_service.py), mirrors audio-processor's Dockerfile.
RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 ffmpeg && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
# Bake the model+tokenizer into the image at BUILD time instead of downloading
# from HuggingFace Hub on every container start. The previous VOLUME-based
# cache didn't actually persist across ACA replicas (each new replica —
# including ones spun up by horizontal autoscaling, see
# docs/06-horizontal-autoscaling.md — got a fresh empty volume), so every
# scale-out event paid the full download+load cost before the replica could
# pass its healthcheck. Baking it in trades slower image builds (happens
# once) for faster container starts (happens on every scale-out — the
# time-sensitive side of that tradeoff). Only fp32 needs baking: fp16 and the
# int8 quantization device_manager.py can switch to are computed at load time
# from these same cached files, not separately downloaded.
ARG MODEL_ID=QuechuaBase/whisper-base-qxp-finetuned
ENV HF_HUB_DISABLE_IMPLICIT_TOKEN=1
RUN python -c "from transformers import WhisperTokenizer, pipeline; tok = WhisperTokenizer.from_pretrained('${MODEL_ID}', clean_up_tokenization_spaces=False); pipeline('automatic-speech-recognition', model='${MODEL_ID}', tokenizer=tok, device=-1)"
# Same weights converted to CTranslate2 for ENGINE=ctranslate2. Weights stay
# float32 on disk; int8/fp16 are applied at load time, so one conversion serves
# every precision the adaptation policy can switch to. faster-whisper needs the
# fast tokenizer file, which the model repo does not ship, so it is exported here.
RUN ct2-transformers-converter --model ${MODEL_ID} --output_dir /models/ct2 --copy_files preprocessor_config.json     && python -c "from transformers import WhisperTokenizerFast; WhisperTokenizerFast.from_pretrained('${MODEL_ID}').save_pretrained('/tmp/tok')"     && cp /tmp/tok/tokenizer.json /models/ct2/ && rm -rf /tmp/tok
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
