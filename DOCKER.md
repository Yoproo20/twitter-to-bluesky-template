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

**Option A: Build locally**
```bash
docker compose up -d --build
```

**Option B: Pre-built Docker Hub image**

[View on Docker Hub](https://hub.docker.com/r/theypstudio/twitter-to-bluesky-mirror)
```bash
docker pull theypstudio/twitter-to-bluesky-mirror:main
```
*(If you are using Docker Compose, please replace `build: .` with `image: theypstudio/twitter-to-bluesky-mirror:main` in your `docker-compose.yml` file before starting the bot).*

### 3. View logs

```bash
docker compose logs -f
```

## Updating

To update your container to the latest version:

**If you built locally (Option A):**
```bash
git pull
docker compose up -d --build
```

**If you use the Docker Hub image (Option B):**
```bash
docker pull theypstudio/twitter-to-bluesky-mirror:main
docker compose up -d
```
*make sure to run the compose inside the directory of which you started in*

## Run on Boot

The `docker-compose.yml` uses `restart: unless-stopped`. When your server boots:

1. Docker daemon starts (have to be enabled by your OS)
2. The container automatically starts

No extra setup needed. To ensure Docker starts on boot:

```bash
sudo systemctl enable docker # for Linux users, check your OS documentation for Windows/MacOS
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
