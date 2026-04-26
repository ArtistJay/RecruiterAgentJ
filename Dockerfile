FROM python:3.11-slim

WORKDIR /app

# System deps (tesseract for OCR, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    ocrmypdf \
    curl && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Set PYTHONPATH so agent module is importable
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Create required directories
RUN mkdir -p data/candidates data/sample_jds db/chroma docs/sample_outputs

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
