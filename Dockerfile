# 🏗 Stage 1: Build dependencies and compile Python files
FROM python:3.13.2-alpine3.21 AS builder

# ENV PYTHONUNBUFFERED=1 \
#     PYTHONFAULTHANDLER=1 \
#     PIP_NO_CACHE_DIR=1 \
#     PIP_DISABLE_PIP_VERSION_CHECK=1 \
#     PIP_DEFAULT_TIMEOUT=100

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
# # Install necessary build dependencies
# RUN apk add --no-cache --virtual .build-deps \
#     gcc musl-dev python3-dev libffi-dev openssl-dev 

# # Copy dependencies first for better caching
# COPY requirements.txt .
# # Install dependencies
# RUN pip install --no-cache-dir --upgrade pip \
#     && pip install --no-cache-dir -r requirements.txt

# # Copy application source code
# COPY . .

# # Compile Python files to bytecode
# RUN python -m compileall /app

# # ---------------------------🏗 Stage 2: Minimal runtime environment-------------------------------------------------------
# FROM python:3.13.2-alpine3.21 AS runtime

# WORKDIR /app

# # Copy only required runtime dependencies from builder stage
# COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
# COPY --from=builder /usr/local/bin /usr/local/bin

# # 🏗 -----------------------Stage 3: Final lightweight application layer-------------------------------------------------------
# FROM python:3.13.2-alpine3.21 AS final
# WORKDIR /app

# # Install dependencies again in the final layer to ensure they're present
# COPY --from=builder /app/requirements.txt /app/requirements.txt
# RUN pip install --no-cache-dir --upgrade pip \
#     && pip install --no-cache-dir -r requirements.txt

# # Create non-root user for security
# RUN addgroup -S appgroup && adduser -S appuser -G appgroup
# USER appuser

# # Copy only the compiled `.pyc` files from builder stage to final image
# COPY --from=builder /app/__pycache__ /app/__pycache__

# # Copy the .env file into the container (if you use it for environment variables)
# COPY --from=builder /app/env.py /app/env.py

# Use optimized compiled files for execution
ENTRYPOINT ["python", "/app/main.py"]
