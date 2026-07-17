FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    clamav \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./src/requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY ./src/*.py .

ENV DATABASE_DIRECTORY=/var/lib/clamav

CMD ["python3", "main.py", "--action", "scan"]