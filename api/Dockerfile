# ffmpeg is required: MediaRecorder produces webm/opus, which libsndfile cannot read.
FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg libsndfile1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU torch only - no CUDA on the target box, and the CUDA wheel is ~2 GB larger.
COPY requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
      -r requirements.txt

COPY tilawah ./tilawah

# Model weights (~1.3 GB in bfloat16) download on first request and live in the
# HF cache. Mount it as a volume or every redeploy re-downloads.
ENV HF_HOME=/cache/huggingface
VOLUME ["/cache/huggingface"]

EXPOSE 8000
# One worker on purpose: each would load its own copy of the model.
CMD ["uvicorn", "tilawah.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
