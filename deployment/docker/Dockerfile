FROM python:3.10-slim
ENV PYTHONUNBUFFERED=1

RUN apt-get update -y \
    && apt-get -y upgrade \
    && apt-get -y install pandoc pdflatex \
    && apt-get -y clean
COPY ./setup* /app/
COPY ./deployment/requirements/prod.txt /
RUN pip install -r prod.txt

COPY ./src /app/src
WORKDIR /app
RUN python setup.py develop

ENTRYPOINT ["python", "-m"]
