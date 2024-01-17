FROM python:3.9-slim-buster

ARG BUILD_DATE
ARG BUILD_NUMBER
ARG RELEASE
ARG VERSION

LABEL org.opencontainers.image.description="Alerta API (dev)" \
      org.opencontainers.image.created=$BUILD_DATE \
      org.opencontainers.image.url="https://github.com/alerta/alerta/pkgs/container/alerta-api" \
      org.opencontainers.image.source="https://github.com/alerta/alerta" \
      org.opencontainers.image.version=$RELEASE \
      org.opencontainers.image.revision=$VERSION \
      org.opencontainers.image.licenses=Apache-2.0

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

RUN echo "BUILD_NUMBER = '$BUILD_NUMBER'" > alerta/build.py && \
    echo "BUILD_DATE = '$BUILD_DATE'"    >> alerta/build.py && \
    echo "BUILD_VCS_NUMBER = '$VERSION'" >> alerta/build.py

RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install -r requirements-ci.txt && \
    pip install .

EXPOSE 8080
ENV FLASK_SKIP_DOTENV=1
CMD ["alertad", "run", "--host", "0.0.0.0", "--port", "8080"]
