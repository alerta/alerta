FROM python:3.11-slim-buster


ENV ALERTA_ENDPOINT=http://localhost:8080

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    curl \
    gnupg2 \
    libldap2-dev \
    libpq-dev \
    libsasl2-dev \
    postgresql-client && \
    apt-get -y clean && \
    apt-get -y autoremove && \
    rm -rf /var/lib/apt/lists/*


RUN pip install --upgrade pip

WORKDIR /alerta

COPY . .

RUN pip install --no-cache-dir .['dev','postgres','mongodb','ci']

EXPOSE 8080
ENV FLASK_SKIP_DOTENV=1
CMD ["alertad", "run", "--host", "0.0.0.0", "--port", "8080"]
