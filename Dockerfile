FROM python:3.8-alpine

RUN apk add --no-cache \
    bash \
    build-base \
    libffi-dev \
    openldap-dev \
    openssl-dev \
    postgresql-dev \
    python3-dev \
    xmlsec-dev

COPY . /app
WORKDIR /app

ENV CRYPTOGRAPHY_DONT_BUILD_RUST 1
RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install -r requirements-ci.txt && \
    pip install .

ENV ALERTA_SVR_CONF_FILE /app/alertad.conf
ENV ALERTA_CONF_FILE /app/alerta.conf
ENV ALERTA_ENDPOINT=http://localhost:8080

COPY docker-entrypoint.sh /
ENTRYPOINT ["/docker-entrypoint.sh"]

EXPOSE 8080
ENV FLASK_SKIP_DOTENV=1
CMD ["alertad", "run", "--host", "0.0.0.0", "--port", "8080"]
