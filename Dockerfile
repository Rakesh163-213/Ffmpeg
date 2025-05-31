FROM python:3.10-slim

# Install system packages
RUN apt-get update && \
    apt-get install -y ffmpeg megatools && \
    apt-get clean

# Set working directory
WORKDIR /app

# Copy all project files
COPY . /app

# Make sure start.sh is executable
#RUN chmod +x /app/start.sh

# Install Python dependencies
RUN pip install --no-cache-dir flask pyrogram tgcrypto

# Run start.sh (which should start your bot or other services)
#CMD ["./start.sh"]
CMD python main.py & python app.py
