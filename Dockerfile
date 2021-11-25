FROM python:3.7-slim-buster

ENV PYTHONUNBUFFERED 1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1

LABEL maintainer="Nick Satterly <nick.satterly@gmail.com>"

ARG BUILD_DATE=now
ARG VCS_REF
ARG VERSION

ENV SERVER_VERSION=${VERSION}
ENV CLIENT_VERSION=8.5.0
ENV WEBUI_VERSION=8.5.0

LABEL org.label-schema.build-date=$BUILD_DATE \
    org.label-schema.url="https://alerta.io" \
    org.label-schema.vcs-url="https://github.com/alerta/docker-alerta" \
    org.label-schema.vcs-ref=$VCS_REF \
    org.label-schema.version=$VERSION \
    org.label-schema.schema-version="1.0.0-rc.1"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    gnupg2 \
    libldap2-dev \
    libpq-dev \
    libsasl2-dev \
    postgresql-client \
    python3-dev \
    supervisor \
    xmlsec1 && \
    apt-get -y clean && \
    apt-get -y autoremove && \
    rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://nginx.org/keys/nginx_signing.key | apt-key add - && \
    echo "deb https://nginx.org/packages/debian/ buster nginx" | tee /etc/apt/sources.list.d/nginx.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    nginx && \
    apt-get -y clean && \
    apt-get -y autoremove && \
    rm -rf /var/lib/apt/lists/*

COPY requirements*.txt /app/
# hadolint ignore=DL3013
RUN pip install --no-cache-dir pip virtualenv && \
    python3 -m venv /venv && \
    /venv/bin/pip install --no-cache-dir --upgrade setuptools && \
    /venv/bin/pip install --no-cache-dir --requirement /app/requirements.txt && \
    /venv/bin/pip install --no-cache-dir --requirement /app/requirements-docker.txt
ENV PATH $PATH:/venv/bin

RUN /venv/bin/pip install alerta==${CLIENT_VERSION} 
COPY install-plugins.sh /app/install-plugins.sh
COPY plugins.txt /app/plugins.txt
RUN /app/install-plugins.sh

ENV ALERTA_SVR_CONF_FILE /app/alertad.conf
ENV ALERTA_CONF_FILE /app/alerta.conf

ADD https://github.com/alerta/alerta-webui/releases/download/v${WEBUI_VERSION}/alerta-webui.tar.gz /tmp/webui.tar.gz
RUN tar zxvf /tmp/webui.tar.gz -C /tmp && \
    mv /tmp/dist /web
COPY config.json /web/config.json

COPY wsgi.py /app/wsgi.py
COPY uwsgi.ini /app/uwsgi.ini
COPY nginx.conf /app/nginx.conf

RUN ln -sf /dev/stdout /var/log/nginx/access.log \
    && ln -sf /dev/stderr /var/log/nginx/error.log

RUN chgrp -R 0 /app /venv /web && \
    chmod -R g=u /app /venv /web && \
    useradd -u 1001 -g 0 -d /app alerta

USER 1001

ENV HEARTBEAT_SEVERITY major
ENV HK_EXPIRED_DELETE_HRS 2
ENV HK_INFO_DELETE_HRS 12

COPY docker-entrypoint.sh /usr/local/bin/
COPY supervisord.conf /app/supervisord.conf

ADD . /app
ENTRYPOINT ["docker-entrypoint.sh"]

EXPOSE 8080
CMD ["supervisord", "-c", "/app/supervisord.conf"]

# CMD ["tail","-f","/dev/null"]