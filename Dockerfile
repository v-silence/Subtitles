FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=1 \
    DJANGO_ALLOWED_HOSTS=* \
    POSTGRES_DB=subtitle_service \
    POSTGRES_USER=subtitle_user \
    POSTGRES_PASSWORD=subtitle_password \
    POSTGRES_HOST=db \
    POSTGRES_PORT=5432 \
    MEDIA_ROOT=/data/media \
    LOCAL_WHISPER_MODEL=base \
    LOCAL_WHISPER_DEVICE=cpu \
    LOCAL_WHISPER_COMPUTE_TYPE=int8 \
    LOCAL_WHISPER_BEAM_SIZE=5 \
    ARGOS_AUTO_INSTALL=1 \
    HF_HOME=/data/model-cache/huggingface \
    XDG_CACHE_HOME=/data/model-cache/cache \
    XDG_DATA_HOME=/data/model-cache/share

WORKDIR /app

RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libgomp1 libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data/media /data/model-cache

EXPOSE 8000

CMD ["sh", "/app/docker-entrypoint.sh"]
