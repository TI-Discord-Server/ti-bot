import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional

from env import (SMTP_EMAIL, SMTP_PASSWORD, SMTP_SERVER, SMTP_PORT)

def send_email(
    to_addresses: List[str],
    subject: str,
    body: str,
    html: Optional[str] = None,
    from_address: Optional[str] = None,
) -> None:
    """
    Sends an email using the configured SMTP server.

    Args:
        to_addresses (List[str]): List of recipient email addresses.
        subject (str): Email subject.
        body (str): Plain text body of the email.
        html (Optional[str]): Optional HTML version of the email body.
        from_address (Optional[str]): Sender's email address. Defaults to SMTP_EMAIL.

    Raises:
        Exception: If sending the email fails.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_address or SMTP_EMAIL
    msg["To"] = ", ".join(to_addresses)

    # Attach plain text and (optionally) HTML
    msg.attach(MIMEText(body, "plain"))
    if html:
        msg.attach(MIMEText(html, "html"))

    try:
        # Use SSL if port 465, otherwise use STARTTLS
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                server.login(SMTP_EMAIL, SMTP_PASSWORD)
                server.sendmail(msg["From"], to_addresses, msg.as_string())
        else:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_EMAIL, SMTP_PASSWORD)
                server.sendmail(msg["From"], to_addresses, msg.as_string())
    except Exception as e:
        # You can add logging here if desired
        raise Exception(f"Failed to send email: {e}")

