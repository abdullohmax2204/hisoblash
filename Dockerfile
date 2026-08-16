FROM python:3.12-slim

WORKDIR /app

# Prevent Python from writing .pyc and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

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
CMD ["sh", "-c", "python -m alembic upgrade head && python -m app"]
