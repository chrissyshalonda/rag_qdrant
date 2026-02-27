FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Docling and other libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

CMD ["python", "scripts/init_db.py"]
