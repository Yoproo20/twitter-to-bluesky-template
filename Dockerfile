FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py updater.py setup.py ./

# Data dir for persistent state (mounted as volume)
ENV DATA_DIR=/app/data

# Create data dir (will be overlain by volume mount)
RUN mkdir -p /app/data

CMD ["python", "-u", "main.py"]
