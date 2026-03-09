FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY services /app/services
COPY config /app/config

RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app

CMD ["uvicorn", "services.control_api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
