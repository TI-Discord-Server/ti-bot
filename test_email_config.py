#!/usr/bin/env python3
"""
Test script to verify email configuration for both normal verification and migration.

This script tests:
1. Regular SMTP credentials (for normal verification emails)
2. Migration SMTP credentials (for bounce checking)
3. Migration IMAP credentials (for bounce monitoring)

Usage: python test_email_config.py
"""

import imaplib
import smtplib
import sys

# Add the DiscordTI-bot directory to the path to import env
sys.path.append("/workspace/DiscordTI-bot")

try:
    from env import (
        MIGRATION_IMAP_PORT,
        MIGRATION_IMAP_SERVER,
        MIGRATION_SMTP_EMAIL,
        MIGRATION_SMTP_PASSWORD,
        MIGRATION_SMTP_PORT,
        MIGRATION_SMTP_SERVER,
        SMTP_EMAIL,
        SMTP_PASSWORD,
        SMTP_PORT,
        SMTP_SERVER,
    )
except ImportError as e:
    print(f"Error: Could not import environment variables from env.py: {e}")
    print("Make sure you're running this from the correct directory and env.py exists.")
    sys.exit(1)


def test_smtp_connection(email, password, server, port, connection_name):
    """Test SMTP connection"""
    print(f"\n=== Testing {connection_name} SMTP Connection ===")
    print(f"Server: {server}:{port}")
    print(f"Email: {email}")

    if not email or not password:
        print(f"❌ {connection_name} credentials not configured (email or password missing)")
        return False

    try:
        if port == 465:
            with smtplib.SMTP_SSL(server, port) as smtp_server:
                smtp_server.login(email, password)
                print(f"✅ {connection_name} SMTP connection successful (SSL)")
        else:
            with smtplib.SMTP(server, port) as smtp_server:
                smtp_server.starttls()
                smtp_server.login(email, password)
                print(f"✅ {connection_name} SMTP connection successful (STARTTLS)")
        return True
    except Exception as e:
        print(f"❌ {connection_name} SMTP connection failed: {e}")
        return False


def test_imap_connection(email, password, server, port, connection_name):
    """Test IMAP connection"""
    print(f"\n=== Testing {connection_name} IMAP Connection ===")
    print(f"Server: {server}:{port}")
    print(f"Email: {email}")

    if not email or not password:
        print(f"❌ {connection_name} credentials not configured (email or password missing)")
        return False

    try:
        with imaplib.IMAP4_SSL(server, port) as imap_server:
            imap_server.login(email, password)
            imap_server.select("INBOX")
            print(f"✅ {connection_name} IMAP connection successful")
        return True
    except Exception as e:
        print(f"❌ {connection_name} IMAP connection failed: {e}")
        return False


def main():
    """Main test function"""
    print("=== Email Configuration Test ===")
    print("This script tests both regular and migration email configurations.")
    print()

    # Test regular SMTP (for normal verification emails)
    regular_smtp_ok = test_smtp_connection(
        SMTP_EMAIL, SMTP_PASSWORD, SMTP_SERVER, SMTP_PORT, "Regular"
    )

    # Test migration SMTP (for bounce checking)
    migration_smtp_ok = test_smtp_connection(
        MIGRATION_SMTP_EMAIL,
        MIGRATION_SMTP_PASSWORD,
        MIGRATION_SMTP_SERVER,
        MIGRATION_SMTP_PORT,
        "Migration",
    )

    # Test migration IMAP (for bounce monitoring)
    migration_imap_ok = test_imap_connection(
        MIGRATION_SMTP_EMAIL,
        MIGRATION_SMTP_PASSWORD,
        MIGRATION_IMAP_SERVER,
        MIGRATION_IMAP_PORT,
        "Migration",
    )

    # Summary
    print("\n=== Test Summary ===")
    print(f"Regular SMTP (verification emails): {'✅ OK' if regular_smtp_ok else '❌ FAILED'}")
    print(f"Migration SMTP (bounce checking): {'✅ OK' if migration_smtp_ok else '❌ FAILED'}")
    print(f"Migration IMAP (bounce monitoring): {'✅ OK' if migration_imap_ok else '❌ FAILED'}")

    if regular_smtp_ok and migration_smtp_ok and migration_imap_ok:
        print("\n🎉 All email configurations are working correctly!")
        print("\nNext steps:")
        print("1. Normal verification emails will use your custom domain SMTP")
        print("2. Migration bounce checking will use Gmail for better compatibility")
        print("3. The bot is ready to handle both verification types")
    else:
        print("\n⚠️  Some email configurations failed. Please check:")
        if not regular_smtp_ok:
            print("- Regular SMTP credentials in your .env file")
        if not migration_smtp_ok:
            print("- Migration SMTP credentials in your .env file")
        if not migration_imap_ok:
            print("- Migration IMAP credentials in your .env file")
        print("- Make sure Gmail accounts have 'App Passwords' enabled if using Gmail")
        print("- Check firewall settings and network connectivity")


if __name__ == "__main__":
    main()
