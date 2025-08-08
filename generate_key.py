#!/usr/bin/env python3

try:
    from cryptography.fernet import Fernet
except ImportError:
    print("Installing required package: cryptography")
    import subprocess
    subprocess.check_call(["pip", "install", "cryptography"])
    from cryptography.fernet import Fernet

# Generate a Fernet key
key = Fernet.generate_key().decode()
print(key)