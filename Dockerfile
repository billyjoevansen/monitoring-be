FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create models directory
RUN mkdir -p models

EXPOSE 5000

CMD ["gunicorn", "app:create_app()", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120"]
