import base64
import hashlib
import hmac

from env import EMAIL_INDEX_KEY


def make_email_index(email: str) -> str:
    """Maak een HMAC blind index voor deterministische lookups."""
    key = EMAIL_INDEX_KEY.encode()
    h = hmac.new(key, email.lower().encode(), hashlib.sha256)
    return base64.urlsafe_b64encode(h.digest()).decode()
