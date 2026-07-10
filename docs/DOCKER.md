# Docker Deployment Guide

This guide covers Docker deployment for Receipt Manager.

## Quick Start

`docker-compose.yml` requires `AUTH_PASSWORD` and `SECRET_KEY` to be set — the
container refuses to start with the shipped defaults, and Compose itself will
error out if these aren't provided. Create a `.env` file next to
`docker-compose.yml`:

```bash
cd platforms/docker
cat > .env <<EOF
AUTH_PASSWORD=choose-a-strong-password
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
EOF
docker-compose up -d
```

Access at: <http://localhost:8765> (the port is published to the host's
loopback interface only — see [Authentication](#authentication) below).

## Building from Source

### Using Docker Compose

```bash
cd platforms/docker
docker-compose build
docker-compose up -d
```

### Using Docker Directly

```bash
# Build
docker build -f platforms/docker/Dockerfile -t receipts-manager .

# Run
docker run -d \
  -p 8765:8765 \
  -v receipt-data:/app/data \
  -v receipt-storage:/app/storage \
  --name receipts-manager \
  receipts-manager
```

## Configuration

### Authentication

The app is unauthenticated over HTTP by default. `docker-compose.yml` enables
authentication and requires these to be set (via `.env` or `-e`):

```yaml
environment:
  - AUTH_ENABLED=true          # default in docker-compose.yml
  - AUTH_USERNAME=admin        # optional, defaults to "admin"
  - AUTH_PASSWORD=...          # required — no default is accepted
  - SECRET_KEY=...             # required — signs session cookies, must be long/random
```

The app will refuse to start if `AUTH_PASSWORD`/`SECRET_KEY` are left at their
insecure defaults. Only publish the port beyond `127.0.0.1` (i.e. to your LAN
or the internet) once authentication is configured.

### Environment Variables

Edit `docker-compose.yml` or pass via `-e` flag:

```yaml
environment:
  - PORT=8765
  - HOST=0.0.0.0               # interface the server binds to *inside* the container
  - OCR_LANGUAGE=eng+nld+ell+lav
  - DEBUG=false
  - LOG_LEVEL=INFO
```

### Volumes

**Data persistence:**

- `receipt-data`: Database and backups
- `receipt-storage`: Uploaded receipt files

**Bind mounts** (alternative to volumes):

```yaml
volumes:
  - ./data:/app/data
  - ./storage:/app/storage
```

## Management

### Start/Stop

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart
```

### Logs

```bash
# View logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100
```

### Update

```bash
# Pull latest code
git pull

# Rebuild
docker-compose build

# Restart
docker-compose up -d
```

## Backup

### Backup Volumes

```bash
# Backup data
docker run --rm \
  -v receipt-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/receipt-data-backup.tar.gz -C /data .

# Backup storage
docker run --rm \
  -v receipt-storage:/storage \
  -v $(pwd):/backup \
  alpine tar czf /backup/receipt-storage-backup.tar.gz -C /storage .
```

### Restore Volumes

```bash
# Restore data
docker run --rm \
  -v receipt-data:/data \
  -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/receipt-data-backup.tar.gz"

# Restore storage
docker run --rm \
  -v receipt-storage:/storage \
  -v $(pwd):/backup \
  alpine sh -c "cd /storage && tar xzf /backup/receipt-storage-backup.tar.gz"
```

## Production Deployment

### Using Docker Compose (Recommended)

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  receipts-manager:
    image: receipts-manager:latest
    container_name: receipts-manager
    restart: always
    ports:
      - "127.0.0.1:8765:8765"  # Only localhost
    volumes:
      - /var/lib/receipts/data:/app/data
      - /var/lib/receipts/storage:/app/storage
    environment:
      - DEBUG=false
      - LOG_LEVEL=WARNING
      - AUTH_ENABLED=true
      - AUTH_PASSWORD=${AUTH_PASSWORD:?set a strong password}
      - SECRET_KEY=${SECRET_KEY:?set a long random value}
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Run:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Behind Reverse Proxy

**Nginx:**

```nginx
server {
    listen 80;
    server_name receipts.yourdomain.com;

    location / {
        proxy_pass http://localhost:8765;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Traefik:**

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.receipts.rule=Host(`receipts.yourdomain.com`)"
  - "traefik.http.services.receipts.loadbalancer.server.port=8765"
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs

# Check if port is in use
lsof -i :8765

# Remove and recreate
docker-compose down
docker-compose up -d
```

### Permission issues

```bash
# Fix volume permissions
docker-compose exec receipts-manager chown -R 1000:1000 /app/data /app/storage
```

### OCR not working

Tesseract is included in the Docker image. If OCR fails:

```bash
# Check Tesseract installation
docker-compose exec receipts-manager tesseract --version

# Check language packs
docker-compose exec receipts-manager tesseract --list-langs
```

## Security

### Best Practices

1. **Don't expose port publicly** - Use reverse proxy
2. **Use volumes** - Don't use bind mounts in production
3. **Regular backups** - Automate volume backups
4. **Update regularly** - Keep the image up to date
5. **Resource limits** - Set memory/CPU limits

### Resource Limits

```yaml
services:
  receipts-manager:
    # ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## Advanced

### Multi-architecture Build

```bash
docker buildx create --use
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t receipts-manager:latest \
  -f platforms/docker/Dockerfile \
  .
```

### Custom Tesseract Languages

Modify `Dockerfile`:

```dockerfile
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-deu \
    tesseract-ocr-fra \
    # Add more languages...
```

---

For more information, see the [main README](../README.md).
