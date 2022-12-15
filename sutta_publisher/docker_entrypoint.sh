#!/usr/bin/env bash
set -e \
  && cd /tmp \
  && git clone https://github.com/suttacentral/publications.git \
  && cd ./publications/sutta_publisher \
  && cp -rf ./src/sutta_publisher /app \
  && pip install --no-cache-dir -r ./prod.txt \
  && find ./assets/fonts/ -type f -exec cp -f {} /usr/local/share/fonts/ \; \
  && fc-cache -fv \
  && cd /app

exec "$@"
