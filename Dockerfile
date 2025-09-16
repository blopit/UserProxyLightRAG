# Production Dockerfile for LightRAG with Scope Support
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Rust (required for some dependencies)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Create app directory
WORKDIR /app

# Copy requirements and source code
COPY pyproject.toml .
COPY setup.py .
COPY lightrag/ ./lightrag/

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel

# Install the package and its dependencies
RUN pip install --no-cache-dir -e .
RUN pip install --no-cache-dir -e .[api]

# Install optional dependencies for full functionality
RUN pip install --no-cache-dir nano-vectordb networkx openai ollama tiktoken pypdf2 python-docx python-pptx openpyxl

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/config

# Set up configuration
ENV WORKING_DIR=/app/data \
    LOG_DIR=/app/logs \
    CONFIG_DIR=/app/config

# Scope system configuration
ENV SCOPE_ENABLE_INHERITANCE=true \
    SCOPE_VALIDATION_STRICT=true \
    SCOPE_MIGRATION_BATCH_SIZE=1000 \
    SCOPE_CACHE_SIZE=10000 \
    SCOPE_CACHE_TTL=3600

# API configuration
ENV API_HOST=0.0.0.0 \
    API_PORT=9621 \
    API_WORKERS=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9621/health || exit 1

# Expose port
EXPOSE 9621

# Switch to non-root user for security
RUN useradd --create-home --shell /bin/bash lightrag && \
    chown -R lightrag:lightrag /app
USER lightrag

# Start the application
CMD ["python", "-m", "lightrag.api.lightrag_server", "--host", "0.0.0.0", "--port", "9621"]

# Labels for metadata
LABEL org.opencontainers.image.title="LightRAG with Scope Support" \
      org.opencontainers.image.description="Enhanced LightRAG with hierarchical scope-based data partitioning" \
      org.opencontainers.image.version="1.4.9" \
      org.opencontainers.image.vendor="LightRAG Community" \
      org.opencontainers.image.url="https://github.com/HKUDS/LightRAG" \
      org.opencontainers.image.documentation="https://github.com/HKUDS/LightRAG/blob/main/README.md" \
      scope.support="true" \
      scope.version="1.0.0"