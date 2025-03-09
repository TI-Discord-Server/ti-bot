FROM python:3.13.2-alpine3.21 AS builder
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
ENTRYPOINT ["python", "/app/main.py"]
 
