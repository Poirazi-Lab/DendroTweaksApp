# Use Python 3.11 slim base image
FROM python:3.11-slim

# Set working directory
WORKDIR /dendrotweaks

# Install system dependencies
RUN apt-get update && apt-get install -y \
    graphviz \
    graphviz-dev \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire app directory
COPY app/ ./app/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /dendrotweaks
USER appuser

# Expose Bokeh default port
EXPOSE 5006

# Default to secure localhost access
ENV BOKEH_ALLOW_WS_ORIGIN="localhost:5006,127.0.0.1:5006"

# Command to run the Bokeh server
CMD ["bokeh", "serve", "--address", "0.0.0.0", "--port", "5006", "app"]