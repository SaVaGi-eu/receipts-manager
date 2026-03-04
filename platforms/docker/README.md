# Docker Deployment

This directory contains Docker configuration for Receipt Manager.

## Quick Start

```bash
# From repository root
cd platforms/docker
docker-compose up -d
```

Access the application at: <http://localhost:8765>

## Building

```bash
docker-compose build
```

## Managing

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f

# Restart
docker-compose restart
```

## Data Persistence

Data is stored in Docker volumes:

- `receipt-data` - Database and backups
- `receipt-storage` - Uploaded receipt files

## Environment Variables

Edit `docker-compose.yml` to customize:

- `PORT` - Application port (default: 8765)
- Add more as needed
