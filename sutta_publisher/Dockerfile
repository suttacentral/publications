FROM python:3.10-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

ENV PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

ENV PYTHONPATH=/app/

RUN apt-get update -y \
    && apt-get upgrade --no-install-recommends -y \
    && apt-get install wget xvfb unzip poppler-utils -y \
    && apt-get install xfonts-100dpi xfonts-75dpi xfonts-scalable xfonts-cyrillic -y \
    && apt-get clean -y \
    && cd /tmp \
    && wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install ./google-chrome-stable_current_amd64.deb -y \
    && wget https://chromedriver.storage.googleapis.com/99.0.4844.51/chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip \
    && mv chromedriver /usr/local/bin/


### PRODUCTION
FROM base as production
ENV RUN_ENV=production
COPY ./src /app
COPY ./prod.txt /tmp/
RUN pip install -r /tmp/prod.txt

COPY ./src /app/src
WORKDIR /app

### DEVELOPMENT
FROM production as development
ENV RUN_ENV=development
COPY ./dev.txt /tmp/
RUN pip install -r /tmp/dev.txt

COPY ./tests /app/tests
