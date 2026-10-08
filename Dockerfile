FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for image processing and network
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition and install
COPY python_service/requirements.txt ./python_service/requirements.txt
RUN pip install --no-cache-dir -r python_service/requirements.txt

# Copy source code
COPY . .

# Create generated media cache directory
RUN mkdir -p generated_media

EXPOSE 8000

ENV PORT=8000
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "python_service.main", "--serve"]
