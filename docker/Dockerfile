FROM python:3.7

COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt
RUN pip install .

ENTRYPOINT ["alertad"]
