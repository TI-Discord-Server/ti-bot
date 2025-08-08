FROM python:3.13.2-alpine3.21 AS builder
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# Set the entrypoint based on the TLS argument
ENTRYPOINT [ "python", "/app/main.py --tls=$TLSENABLED" ]
