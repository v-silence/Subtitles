#!/bin/sh
set -e

python - <<'PY'
import os
import socket
import time

host = os.getenv('POSTGRES_HOST', 'localhost')
port = int(os.getenv('POSTGRES_PORT', '5432'))

for attempt in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            break
    except OSError:
        if attempt == 59:
            raise
        time.sleep(1)
PY

python manage.py migrate
python manage.py collectstatic --noinput
exec python manage.py runserver 0.0.0.0:${PORT:-8000}
