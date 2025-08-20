# Production Deployment: Django + Celery + Redis + Postgres + Nginx + Let's Encrypt

## 1) Prerequisites on the VPS
- Point your domain's DNS A record to the VPS public IP.
- Install Docker & Docker Compose:
  ```bash
  sudo apt update && sudo apt install -y docker.io docker-compose
  sudo usermod -aG docker $USER
  newgrp docker
  ```

## 2) Clone your project & prepare env
```bash
git clone <your-repo>
cd <your-repo>
cp .env.example .env
nano .env  # set secrets and DB passwords
```

## 3) Configure Nginx
Edit `docker/nginx/nginx.conf` and replace `YOUR_DOMAIN` with your real domain.

## 4) First boot (HTTP only)
```bash
docker-compose up -d --build
```
- This starts web, worker, beat, redis, postgres, nginx.
- Ensure your site responds on http://YOUR_DOMAIN (it will redirect to https which isn't ready yet; you can visit http://<server-ip> to test health if needed).

## 5) Obtain Let's Encrypt certificates
Use webroot challenge (nginx already serves /.well-known/acme-challenge from the shared volume):
```bash
docker-compose run --rm certbot certonly --webroot       -w /var/www/certbot       -d YOUR_DOMAIN -d www.YOUR_DOMAIN       --email YOUR_EMAIL --agree-tos --no-eff-email
```

After success, reload Nginx to pick up the certs:
```bash
docker-compose exec nginx nginx -s reload
```

Now test https://YOUR_DOMAIN 🎉

## 6) Automatic renewal (cron on the VPS)
Edit the crontab:
```bash
crontab -e
```
Add this line to renew twice daily and reload nginx if changed:
```
0 3,15 * * * docker-compose -f /path/to/your/docker-compose.yml run --rm certbot renew --webroot -w /var/www/certbot && docker-compose -f /path/to/your/docker-compose.yml exec -T nginx nginx -s reload
```

## 7) Running Django commands
```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py collectstatic
```

## 8) Deploying updates
- Push changes to your repo.
- On the VPS:
  ```bash
  cd /path/to/your/project
  git pull
  docker-compose up -d --build
  # if you changed static files or models:
  docker-compose exec web python manage.py migrate
  docker-compose exec web python manage.py collectstatic
  ```

## 9) Django settings tips
- In `settings.py` use env vars:
  ```python
  import os
  SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
  DEBUG = os.getenv("DJANGO_DEBUG", "False") == "True"
  ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",")

  DATABASES = {
      "default": {
          "ENGINE": "django.db.backends.postgresql",
          "NAME": os.getenv("POSTGRES_DB"),
          "USER": os.getenv("POSTGRES_USER"),
          "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
          "HOST": os.getenv("POSTGRES_HOST", "db"),
          "PORT": os.getenv("POSTGRES_PORT", "5432"),
      }
  }
  CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
  SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
  CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS if h]
  ```

## 10) Scaling Celery
Increase workers:
```bash
docker-compose up -d --scale worker=3
```

## 11) Backups (Postgres)
Quick dump:
```bash
docker-compose exec db pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup.sql
```

## 12) Common ports
- Nginx: 80/443 (public)
- Gunicorn: 8000 (internal)
- Postgres: 5432 (internal)
- Redis: 6379 (internal)
