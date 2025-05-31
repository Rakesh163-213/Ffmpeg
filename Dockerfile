FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y megatools ffmpeg && \
    apt-get clean

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir moviepy flask pyrogram tgcrypto

CMD python main.py & python app.py
