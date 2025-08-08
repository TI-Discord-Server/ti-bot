FROM python:3.13.2-alpine3.21 AS builder
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# Define build argument for TLS (default is disabled)
ARG ENABLE_TLS=false

# Set the entrypoint based on the TLS argument
ENTRYPOINT [ "sh", "-c", "if [ \"$ENABLE_TLS\" = \"true\" ]; then python /app/main.py --tls; else python /app/main.py; fi" ]
