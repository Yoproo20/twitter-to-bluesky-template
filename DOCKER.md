# Docker Deployment

Run the Twitter-to-Bluesky bot in Docker with automatic restart on server boot.

## Prerequisites

- Docker and Docker Compose on your Debian server
- A `.env` file with your credentials (see below)

## Quick Start

### 1. Create `.env` file

Copy the template and fill in your credentials:

```bash
cp .env.example .env
nano .env  # or your preferred editor
```

Required variables (see `.env.example` for full list):

- `TARGET_USER` – Twitter handle to mirror (without @)
- `TWITTER_AUTH_TOKEN` – From x.com cookies (recommended)
- `BLUESKY_USERNAME` – Your Bluesky handle
- `BLUESKY_PASSWORD` – Your Bluesky app password

### 2. Build and run

```bash
docker compose up -d --build
```

### 3. View logs

```bash
docker compose logs -f
```

## Run on Boot

The `docker-compose.yml` uses `restart: unless-stopped`. When your server boots:

1. Docker daemon starts (enabled by default on Debian)
2. The container automatically starts

No extra setup needed. To ensure Docker starts on boot:

```bash
sudo systemctl enable docker
```

## Commands

| Command | Description |
|---------|-------------|
| `docker compose up -d` | Start in background |
| `docker compose down` | Stop and remove container |
| `docker compose logs -f` | Follow logs |
| `docker compose restart` | Restart the bot |

## Data Persistence

State is stored in a Docker volume `twitter-bluesky-data`:

- `state.json` – Last tweet ID, update check time
- `session.txt` – Bluesky session
- `events.log` – Log file
- `version.txt` – Update version tracking
- `session.tw_session` – Twitter session

Data persists across container restarts and server reboots.

## Manual Setup (without Docker Compose)

```bash
# Build
docker build -t twitter-bluesky-bot .

# Run
docker run -d \
  --name twitter-bluesky-bot \
  --restart unless-stopped \
  --env-file .env \
  -e DATA_DIR=/app/data \
  -v twitter-bluesky-data:/app/data \
  twitter-bluesky-bot
```
