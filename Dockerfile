FROM python:3.8-alpine

RUN apk add --no-cache \
    build-base \
    libffi-dev \
    openssl-dev \
    postgresql-dev \
    python3-dev

COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt
RUN pip install .

EXPOSE 8080

ENTRYPOINT ["alertad"]
CMD ["run", "--host", "0.0.0.0", "--port", "8080"]
