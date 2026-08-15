FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

# Create directories for data, logs, and backups
RUN mkdir -p data logs backups

# Run migrations and start the bot
CMD alembic upgrade head && python -m app
