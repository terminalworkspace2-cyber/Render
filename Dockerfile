FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Install pre-built wheel directly - NO compile, NO gcc needed
RUN pip install --no-cache-dir llama-cpp-python==0.3.8 --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
COPY app.py .
CMD uvicorn app:app --host 0.0.0.0 --port $PORT
