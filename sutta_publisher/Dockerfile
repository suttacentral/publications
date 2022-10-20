FROM python:3.10-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

ENV PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

ENV PYTHONPATH=/app/

RUN apt-get update -y \
    && apt-get upgrade --no-install-recommends -y \
    && apt-get install perl wget fontconfig libmagickwand-dev -y \
    && apt-get clean -y \
    && cd /tmp \
    && wget -q https://mirror.ctan.org/systems/texlive/tlnet/install-tl-unx.tar.gz \
    && zcat install-tl-unx.tar.gz | tar xf - \
    && cd install-tl-* \
    && perl ./install-tl --no-interaction \
    && cd .. \
    && rm install-tl-unx.tar.gz \
    && rm -r install-tl-*

COPY ./assets/fonts/ /tmp/fonts
RUN cp -Rf /tmp/fonts/Gentium/ /usr/local/share/fonts/ && \
    cp -Rf /tmp/fonts/neranjara/ /usr/local/share/fonts/ && \
    cp -Rf /tmp/fonts/Noto_Serif_TC/fonts/otf/ /usr/local/share/fonts/ && \
    cp -Rf /tmp/fonts/sclogo/ /usr/local/share/fonts/ && \
    fc-cache -fv && \
    rm -Rf /tmp/fonts

ENV PATH=/usr/local/texlive/2022/bin/x86_64-linux:$PATH

RUN tlmgr install luatextra fontspec

COPY ./policy.xml /etc/ImageMagick-6

### PRODUCTION
FROM base as production
ENV RUN_ENV=production

COPY ./src /app
COPY ./prod.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/prod.txt
WORKDIR /app

### DEVELOPMENT
FROM production as development
ENV RUN_ENV=development
COPY ./dev.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/dev.txt

COPY ./tests /app/tests
