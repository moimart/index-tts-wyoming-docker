FROM nvidia/cuda:12.8.0-runtime-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    git-lfs \
    ffmpeg \
    libsndfile1 \
    curl \
    build-essential \
    && git lfs install \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv (the only supported installer for index-tts)
RUN pip install --no-cache-dir --break-system-packages -U uv

# Clone index-tts (skip LFS files - we don't need example WAVs)
RUN GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/index-tts/index-tts.git /app/index-tts

# Use uv sync as recommended by the project - it manages its own Python
WORKDIR /app/index-tts
RUN uv sync \
    && uv pip install wyoming

# Set up the uv-managed venv as the active Python
ENV PATH="/app/index-tts/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/index-tts/.venv"

# Copy wyoming server code
WORKDIR /app
COPY wyoming_indextts/ /app/wyoming_indextts/
COPY scripts/ /app/scripts/

# Default voice and checkpoints directories
RUN mkdir -p /app/voices /app/checkpoints

EXPOSE 10300

ENTRYPOINT ["bash", "/app/scripts/run.sh"]
