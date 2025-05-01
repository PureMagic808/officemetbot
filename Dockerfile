FROM python:3.10-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV PYTHONUTF8=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove gcc libffi-dev libjpeg-dev zlib1g-dev
COPY . .
CMD ["python", "bot_railway.py"]
