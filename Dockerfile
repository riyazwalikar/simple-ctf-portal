FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# SQLite database lives here; mount a volume to persist it across restarts
VOLUME /app/data

EXPOSE 5000
CMD ["python", "app.py"]
