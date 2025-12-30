# Dockerfile — copies ONNX model files into image and installs runtime deps
FROM python:3.10-slim

# Prevent Python from writing .pyc files & flush stdout immediately
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install OS dependencies needed for building some wheels and for onnxruntime
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    libpq-dev \
    libgomp1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create app dir
WORKDIR /app

# Copy dependency file first so pip install can be cached
COPY requirements.txt /app/

# Install Python deps
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY . /app/

# Ensure the ONNX model dir exists in the image (optional double-check)
# Make sure your repo contains the "onnx_model" folder with:
#   onnx_model/model.onnx
#   onnx_model/tokenizer.json
#   onnx_model/vocab.txt   (if used)
# If your folder has a different name, update the path below or set ENV MODEL_DIR.
ENV MODEL_DIR=/app/onnx_model

# Expose port used by Gunicorn/Flask
EXPOSE 8000

# Use Gunicorn to serve the app (adjust workers as needed)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "backend:app", "--workers", "2", "--timeout", "60"]
