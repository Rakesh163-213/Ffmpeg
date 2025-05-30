FROM python:3.11-slim

Install FFmpeg and dependencies

RUN apt-get update && 
apt-get install -y ffmpeg && 
apt-get clean && 
rm -rf /var/lib/apt/lists/*

Set work directory

WORKDIR /app

Copy project files

COPY . /app

Install Python dependencies

RUN pip install --no-cache-dir -r requirements.txt

Set environment variable for bot token

ENV BOT_TOKEN=""

Run the bot

CMD python3 main.py & python app.py
