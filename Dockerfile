# Base image
FROM python:3.10-slim

# Install system dependencies for mysqlclient (required by flask-mysqldb)
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files
COPY . .

# Expose port (not strictly necessary, but good practice)
EXPOSE 5000

# Start Gunicorn using Railway’s dynamic port
CMD ["gunicorn", "-b", "0.0.0.0:$PORT", "ServerPart:app"]
