# Use Python 3.14 slim image
FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Install system dependencies for OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-nld \
    tesseract-ocr-ell \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py config.py receipt_service.py ./
COPY services/ ./services/
COPY templates/ ./templates/
COPY static/ ./static/

# Create data directories
RUN mkdir -p /app/data/database /app/data/backups /app/storage

# SECURITY: run as an unprivileged user, not root. The app only needs to read
# its code and read/write the data + storage trees.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

# Bind to all interfaces *inside the container*; publish to host loopback only
# (see docker-compose.yml). Auth should be enabled via AUTH_ENABLED=true.
ENV HOST=0.0.0.0

# Expose port
EXPOSE 8765

# Health check — use the public /health endpoint (which returns 200 even when
# authentication is enabled, unlike "/", which redirects to /login).
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python3 -c "import http.client; conn = http.client.HTTPConnection('localhost', 8765); conn.request('GET', '/health'); response = conn.getresponse(); exit(0 if response.status == 200 else 1)"

# Run the application
CMD ["python3", "app.py"]
