# Use slim Python image for a smaller footprint
FROM python:3.9-slim

# Install build dependencies for Python packages (if needed)
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
  && rm -rf /var/lib/apt/lists/*

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Add project directory to PYTHONPATH
ENV PYTHONPATH="${PYTHONPATH}:/app"

# Upgrade pip
RUN python -m pip install --upgrade pip

# Install pip requirements
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

# Install development tools
RUN python -m pip install flake8 black pytest

# Set working directory
WORKDIR /app
COPY . /app

# Create a non-root user with an explicit UID and set permissions
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# Default command for dev container (interactive shell)
CMD ["/bin/bash"]