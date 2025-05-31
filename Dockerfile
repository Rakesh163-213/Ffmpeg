FROM python:3.10-slim

# Install megatools via apt
RUN apt-get update && \
    apt-get install -y megatools && \
    apt-get clean
    
RUN apt-get update && \
    apt-get install -y ffmpeg
# Set working directory
WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

CMD python main.py & python app.py
