FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml /app/
COPY src /app/src
COPY tests /app/tests

RUN pip install --no-cache-dir -U pip \
 && pip install --no-cache-dir -e ".[dev]"

CMD ["bash", "-lc", "sleep infinity"]
