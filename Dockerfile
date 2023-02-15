FROM python:3.11-slim-buster

ARG DATABASE_TYPE=mongodb


ENV ALERTA_ENDPOINT=http://localhost:8080

RUN apt-get update && \
    apt-get install -y curl && \
    if [ ${DATABASE_TYPE} != postgres ]; then \
    apt-get -y clean && \
    apt-get -y autoremove && \
    rm -rf /var/lib/apt/lists/*; fi

RUN if [ ${DATABASE_TYPE} = postgres ]; then apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libldap2-dev \
    libpq-dev \
    postgresql-client && \
    apt-get -y clean && \
    apt-get -y autoremove && \
    rm -rf /var/lib/apt/lists/*; fi


RUN pip install --upgrade pip

WORKDIR /alerta

COPY . .

RUN pip install --no-cache-dir .['dev',"${DATABASE_TYPE}"]

EXPOSE 8080
ENV FLASK_SKIP_DOTENV=1
CMD ["alertad", "run", "--host", "0.0.0.0", "--port", "8080"]
