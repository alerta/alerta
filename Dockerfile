FROM python:3.8-alpine

RUN apk add --no-cache \
    bash \
    build-base \
    libffi-dev \
    openssl-dev \
    postgresql-dev \
    python3-dev

COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt
RUN pip install .

ENV ALERTA_SVR_CONF_FILE /app/alertad.conf
ENV ALERTA_CONF_FILE /app/alerta.conf
ENV ALERTA_ENDPOINT=http://localhost:8080

COPY docker-entrypoint.sh /
ENTRYPOINT ["/docker-entrypoint.sh"]

EXPOSE 8080

ENV FLASK_SKIP_DOTENV=1

CMD ["alertad", "run", "--host", "0.0.0.0", "--port", "8080"]
