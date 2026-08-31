FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# SQLite database lives in /app/data; mount a volume there to persist it
# across restarts (e.g. Railway Volume, or `docker run -v ...:/app/data`).
# No VOLUME directive: Railway rejects it in Dockerfile builds.

EXPOSE 5000
CMD ["python", "app.py"]
