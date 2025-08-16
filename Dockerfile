FROM python:3.13.2-alpine3.21 AS builder
# set time to Belgium CEST for correct logging times
RUN apk add --no-cache tzdata \
    && cp /usr/share/zoneinfo/Europe/Brussels /etc/localtime \
    && echo "Europe/Brussels" > /etc/timezone

ENV TZ=Europe/Brussels
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# Set the entrypoint based on the TLS argument  
ENTRYPOINT ["/bin/sh", "-c", "python /app/main.py --tls=${TLS_ENABLED}"]
