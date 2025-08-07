#!/bin/bash

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 to generate a Fernet key."
    exit 1
fi

# Check if cryptography package is installed
if ! python3 -c "import cryptography.fernet" &> /dev/null; then
    echo "Installing cryptography package..."
    python3 -m pip install cryptography
fi

# Generate a Fernet key
KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

echo "Generated Fernet key:"
echo $KEY
echo
echo "Add this key to your .env file as ENCRYPTION_KEY='$KEY'"