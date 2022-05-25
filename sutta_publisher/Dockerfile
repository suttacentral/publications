FROM python:3.10-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

ENV PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

ENV PYTHONPATH=/app/

RUN apt-get update -y \
    && apt-get upgrade --no-install-recommends -y \
    && apt-get install pandoc --no-install-recommends -y\
    && apt-get clean -y


### PRODUCTION
FROM base as production
ENV RUN_ENV=production
COPY ./src /app
COPY ./prod.txt /tmp/
RUN pip install -r /tmp/prod.txt

WORKDIR /app

### DEVELOPMENT
FROM production as development
ENV RUN_ENV=development
COPY ./dev.txt /tmp/
RUN pip install -r /tmp/dev.txt

COPY ./tests /app/tests
