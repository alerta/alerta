FROM python:3.8-slim-buster

ENV ALERTA_ENDPOINT=http://localhost:8080

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    gnupg2 \
    libldap2-dev \
    libpq-dev \
    libsasl2-dev \
    postgresql-client \
    python3-dev \
    xmlsec1 && \
    apt-get -y clean && \
    apt-get -y autoremove && \
    rm -rf /var/lib/apt/lists/*

COPY . /app
WORKDIR /app

RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install -r requirements-ci.txt && \
    pip install .

EXPOSE 8080
ENV FLASK_SKIP_DOTENV=1
CMD ["alertad", "run", "--host", "0.0.0.0", "--port", "8080"]
