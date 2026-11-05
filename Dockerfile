FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Direct wheel - already compiled, no CMake, no gcc
RUN pip install --no-cache-dir https://github.com/abetlen/llama-cpp-python/releases/download/v0.3.8/llama_cpp_python-0.3.8-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
COPY app.py .
CMD uvicorn app:app --host 0.0.0.0 --port $PORT
