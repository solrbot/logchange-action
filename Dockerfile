# Multi-stage build for optimal image size
FROM python:3.11-slim AS builder

WORKDIR /build

# Copy and install dependencies
COPY action/src/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /action

# Create non-root user with minimal privileges
RUN groupadd -r action && useradd -r -g action action

# Copy only necessary Python packages from builder
COPY --from=builder --chown=action:action /root/.local /home/action/.local

# Copy action source code
COPY --chown=action:action action/src /action/src

# Make entrypoint executable
RUN chmod +x /action/src/entrypoint.sh

# Set Python path to include user site-packages
ENV PATH=/home/action/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/action/src

# Switch to non-root user
USER action

# Run as non-root user
ENTRYPOINT ["/action/src/entrypoint.sh"]
