FROM python:3.11-slim
WORKDIR /app
# Install compiler wey llama-cpp-python need
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ cmake make && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
CMD uvicorn app:app --host 0.0.0.0 --port $PORT
