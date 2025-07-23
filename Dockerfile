FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./main.py .
COPY ./sound_seeker ./sound_seeker
COPY ./web_app.py .
COPY ./web ./web

CMD ["python", "web_app.py"]