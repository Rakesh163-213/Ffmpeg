# Use an official Python base image
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Install system packages: ffmpeg and megatools
RUN apt-get update && \
    apt-get install -y ffmpeg megatools && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements.txt and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set the default command to run both Python scripts
CMD python main.py
