FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ripgrep && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir --force-reinstall "telethon==1.37.0"

EXPOSE 8000
CMD ["python3", "main.py"]
