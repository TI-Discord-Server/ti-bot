FROM python:3.12.3-alpine3.19

RUN apk add git

COPY . /src
WORKDIR /src

RUN pip install -r /src/requirements.txt

