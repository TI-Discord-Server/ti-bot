#!/bin/bash

# Check if OpenSSL is installed
if ! command -v openssl &> /dev/null; then
    echo "OpenSSL is not installed. Please install OpenSSL to generate a secure key."
    exit 1
fi

# Generate a 32-byte random key and encode it in base64
# This creates a key compatible with Fernet encryption
KEY=$(openssl rand -base64 32 | tr -d '\n' | cut -c1-44)

echo "Generated Fernet key:"
echo $KEY
echo
echo "Add this key to your .env file as ENCRYPTION_KEY='$KEY'"