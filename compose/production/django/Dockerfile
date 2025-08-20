FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends         build-essential libpq-dev netcat-openbsd curl         && rm -rf /var/lib/apt/lists/*

# Create app dir
WORKDIR /app

# Python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy project
COPY . .

# Add entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONDONTWRITEBYTECODE=1         PYTHONUNBUFFERED=1

ENTRYPOINT ["/entrypoint.sh"]
