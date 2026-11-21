FROM python:3.11-slim
WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY mcp_server ./mcp_server
COPY inference ./inference

ENV PYTHONPATH=/app
CMD ["python", "-m", "mcp_server.server"]