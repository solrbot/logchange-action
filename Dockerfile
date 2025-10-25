# Multi-stage build for optimal image size
FROM python:3.11-slim AS builder

WORKDIR /build

# Copy and install dependencies
COPY action/src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /action

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy action source code
COPY action/src /action/src

# Make entrypoint executable
RUN chmod +x /action/src/entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/action/src

# Run as root (required for GitHub Actions to access workspace)
ENTRYPOINT ["/action/src/entrypoint.sh"]
