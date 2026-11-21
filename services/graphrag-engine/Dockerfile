FROM python:3.11-slim
WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src ./src

ENV PYTHONPATH=/app
EXPOSE 50052 8003
CMD ["python", "-m", "src.grpc_server"]