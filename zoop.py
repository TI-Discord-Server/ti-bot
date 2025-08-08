import os
import smtplib
import imaplib
import email
import time
import re
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def send_test_email(smtp_server, smtp_email, smtp_password, recipient: str, test_id: str) -> bool:
    """Send a minimal test email with unique identifier"""
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_email
        msg['To'] = recipient
        msg['Subject'] = f'Email verification test - {test_id}'
        msg['Message-ID'] = f'<{test_id}@verification.test>'

        body = f"""This is an automated email verification test.

If you received this by mistake, please ignore it.
Test ID: {test_id}

This test helps verify email deliverability without requiring any action from you."""

        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(smtp_server, 587) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.send_message(msg)

        print(f"✓ Test email sent to {recipient} (ID: {test_id})")
        return True

    except Exception as e:
        print(f"✗ Failed to send to {recipient}: {e}")
        return False


def _looks_like_dsn(msg) -> bool:
    """Check if message looks like a delivery status notification"""
    rp = (msg.get('Return-Path') or "").strip()
    ctype = (msg.get_content_type() or "").lower()
    ctype_full = (msg.get('Content-Type') or "").lower()

    # RFC-compliant DSN markers
    if rp == "<>" and ctype == "multipart/report" and "report-type=delivery-status" in ctype_full:
        return True

    # Heuristic fallback for non-compliant DSNs
    subj = (msg.get('Subject') or "").lower()
    bounce_hints = ["undeliverable", "delivery status notification", "mail delivery failed",
                    "message not delivered", "delivery failure", "undelivered mail returned to sender"]
    if any(h in subj for h in bounce_hints):
        return True

    if (msg.get('Auto-Submitted') or "").lower().startswith("auto-"):
        return True

    return False


def _extract_dsn_status(msg):
    """Extract DSN status information from message/delivery-status part"""
    if not msg.is_multipart():
        return None

    for part in msg.walk():
        if part.get_content_type() == "message/delivery-status":
            try:
                payload = part.get_payload()
                blocks = payload if isinstance(payload, list) else [part]

                for blk in blocks:
                    text = blk.as_string()
                    action = re.search(r'(?im)^Action:\s*([^\r\n]+)', text)
                    status = re.search(r'(?im)^Status:\s*([0-9]\.[0-9]\.[0-9])', text)
                    diag = re.search(r'(?im)^Diagnostic-Code:\s*([^\r\n]+)', text)
                    recip = re.search(r'(?im)^Final-Recipient:\s*rfc822;\s*([^\r\n\s]+)', text)

                    if action or status or diag or recip:
                        return {
                            "action": (action.group(1).strip().lower() if action else None),
                            "status": (status.group(1).strip() if status else None),
                            "diagnostic": (diag.group(1).strip() if diag else None),
                            "final_recipient": (recip.group(1).strip() if recip else None),
                        }
            except Exception:
                pass
    return None


def _message_matches_test(msg, test_id_to_email: dict):
    """Match received message to one of our sent tests"""
    subject = msg.get('Subject', '')

    # Get body text
    body_text = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body_text += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                except Exception:
                    pass
    else:
        try:
            body_text = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except Exception:
            pass

    text = (subject + "\n" + body_text)

    # Match via test_id token
    for test_id, email_addr in test_id_to_email.items():
        if test_id in text:
            return (email_addr, test_id)

    # If DSN, try to pull Final-Recipient
    dsn = _extract_dsn_status(msg)
    if dsn and dsn.get("final_recipient"):
        for test_id, email_addr in test_id_to_email.items():
            if dsn["final_recipient"].lower() == email_addr.lower():
                return (email_addr, test_id)

    # Heuristic: look for any of the emails in message
    for test_id, email_addr in test_id_to_email.items():
        if email_addr.lower() in text.lower():
            return (email_addr, test_id)

    return None


def check_bounces_improved(imap_host: str, username: str, password: str,
                           test_ids: dict, wait_minutes: int = 15) -> dict:
    """Check for bounces using improved DSN parsing"""
    results = {email_addr: "no_bounce_yet" for email_addr in test_ids.values()}
    deadline = time.time() + wait_minutes * 60
    poll_interval = 30  # seconds

    def classify_from_dsn(dsn_info):
        action = (dsn_info.get("action") or "").lower()
        status = (dsn_info.get("status") or "")
        if action == "failed" or status.startswith("5."):
            return "bounced"
        if action == "delayed" or status.startswith("4."):
            return "delayed"
        if action in ("delivered", "relayed", "expanded"):
            return "delivered"
        return "unknown"

    print(f"Monitoring for bounces for {wait_minutes} minutes...")

    while time.time() < deadline and any(v == "no_bounce_yet" for v in results.values()):
        try:
            with imaplib.IMAP4_SSL(imap_host) as imap:
                imap.login(username, password)
                imap.select("INBOX")

                # Search recent messages
                since_str = time.strftime("%d-%b-%Y", time.gmtime(time.time() - 86400))
                typ, data = imap.search(None, 'SINCE', since_str)

                if typ == 'OK' and data[0]:
                    for num in data[0].split():
                        typ2, msgdata = imap.fetch(num, '(RFC822)')
                        if typ2 != 'OK' or not msgdata or not msgdata[0]:
                            continue

                        msg = email.message_from_bytes(msgdata[0][1])

                        if not _looks_like_dsn(msg):
                            continue

                        match = _message_matches_test(msg, test_ids)
                        if not match:
                            continue

                        email_addr, matched_test_id = match
                        if results[email_addr] != "no_bounce_yet":
                            continue

                        # Parse DSN status
                        dsn_info = _extract_dsn_status(msg)
                        if dsn_info:
                            results[email_addr] = classify_from_dsn(dsn_info)
                            print(
                                f"DSN found for {email_addr}: {results[email_addr]} (Action: {dsn_info.get('action')}, Status: {dsn_info.get('status')})")
                        else:
                            # Fallback text analysis
                            all_text = (msg.get('Subject', '') + " " + str(msg)).lower()
                            if "5.1.1" in all_text or "user unknown" in all_text or "recipient not found" in all_text:
                                results[email_addr] = "bounced"
                                print(f"Bounce detected for {email_addr} (text analysis)")
                            elif "4." in all_text or "temporar" in all_text:
                                results[email_addr] = "delayed"
                                print(f"Delay detected for {email_addr}")
                            else:
                                results[email_addr] = "unknown"
                                print(f"Unknown DSN for {email_addr}")

                imap.logout()
        except Exception as e:
            print(f"Error checking bounces: {e}")

        # Show progress
        remaining = sum(1 for v in results.values() if v == "no_bounce_yet")
        if remaining > 0:
            print(f"Still waiting for {remaining} responses... (checking again in {poll_interval}s)")

        time.sleep(poll_interval)

    return results


def main():
    # Your test email list
    emails_to_test = [
        "jaak.daemen@student.hogent.be",  # Known valid
        "dqmkfdqsklm@student.hogent.be",  # Likely invalid
        "invalid.email@fakeeeeeeee-domain.zzzz"  # Definitely invalid
    ]

    # Get credentials from environment
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_email = os.getenv('SMTP_EMAIL')
    smtp_password = os.getenv('SMTP_PASSWORD')

    if not all([smtp_server, smtp_email, smtp_password]):
        print("❌ Missing required environment variables: SMTP_SERVER, SMTP_EMAIL, SMTP_PASSWORD")
        return

    # Determine IMAP server (adjust if needed)
    if 'gmail' in smtp_server.lower():
        imap_host = "imap.gmail.com"
    elif 'outlook' in smtp_server.lower() or 'office365' in smtp_server.lower():
        imap_host = "outlook.office365.com"
    else:
        imap_host = smtp_server.replace('smtp', 'imap')

    print(f"Using SMTP: {smtp_server}")
    print(f"Using IMAP: {imap_host}")
    print(f"Testing {len(emails_to_test)} email addresses...\n")

    # Send test emails
    test_ids = {}
    successful_sends = []

    for email_addr in emails_to_test:
        test_id = str(uuid.uuid4())[:8]  # Short unique ID
        test_ids[test_id] = email_addr

        if send_test_email(smtp_server, smtp_email, smtp_password, email_addr, test_id):
            successful_sends.append(email_addr)
        else:
            test_ids.pop(test_id)

    if not successful_sends:
        print("❌ No emails were sent successfully")
        return

    print(f"\n✅ Successfully sent {len(successful_sends)} test emails")

    # Check for bounces with improved parsing
    results = check_bounces_improved(
        imap_host=imap_host,
        username=smtp_email,
        password=smtp_password,
        test_ids=test_ids,
        wait_minutes=15  # Wait 15 minutes for bounces
    )

    # Display results
    print("\n" + "=" * 70)
    print("FINAL RESULTS:")
    print("=" * 70)

    for email_addr in emails_to_test:
        if email_addr in [test_ids[tid] for tid in test_ids]:
            status = results.get(email_addr, "not_sent")
            if status == "bounced":
                icon = "❌"
                explanation = "Email address does not exist"
            elif status == "delivered":
                icon = "✅"
                explanation = "Email was delivered successfully"
            elif status == "delayed":
                icon = "⏳"
                explanation = "Delivery delayed (temporary issue)"
            elif status == "no_bounce_yet":
                icon = "❓"
                explanation = "No bounce received (likely delivered or unknown)"
            else:
                icon = "❓"
                explanation = "Unknown status"
        else:
            icon = "💥"
            explanation = "Failed to send test email"
            status = "send_failed"

        print(f"{icon} {email_addr:<35} {status.upper():<15} {explanation}")


if __name__ == "__main__":
    main()
