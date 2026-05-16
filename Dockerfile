FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=1 \
    DJANGO_ALLOWED_HOSTS=* \
    SQLITE_DATABASE_PATH=/data/db.sqlite3 \
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

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data/media /data/model-cache

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
