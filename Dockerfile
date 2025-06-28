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

# Set working directory
WORKDIR /app
COPY . /app

# Create a non-root user with an explicit UID and set permissions
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app

# Copy entrypoint script and make it executable (as root)
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Switch to non-root user
USER appuser

# Set entrypoint
ENTRYPOINT ["./entrypoint.sh"]