FROM python:3.10-slim

# Install megatools
RUN apt-get update && \
    apt-get install -y wget build-essential git pkg-config libssl-dev zlib1g-dev && \
    wget https://megatools.megous.com/builds/megatools-1.11.1.tar.gz && \
    tar -xvzf megatools-1.11.1.tar.gz && \
    cd megatools-1.11.1 && ./configure && make && make install && \
    cd .. && rm -rf megatools*

# Set working directory
WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

CMD python main.py & python app.py
