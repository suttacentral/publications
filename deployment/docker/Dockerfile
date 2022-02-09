FROM python:3.10-slim
ENV PYTHONUNBUFFERED=1

COPY ./setup* /app/
COPY ./deployment/requirements/prod.txt /
RUN pip install -r prod.txt

COPY ./src /app/src
WORKDIR /app
RUN python setup.py develop

ENTRYPOINT ["python", "-m"]
