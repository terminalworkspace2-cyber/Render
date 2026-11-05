FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt
COPY app.py .
CMD uvicorn app:app --host 0.0.0.0 --port $PORT
