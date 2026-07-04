FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY monitor_agent.py .

# Create data directory
RUN mkdir -p /data

# Run the agent
CMD ["python", "-u", "monitor_agent.py"]
