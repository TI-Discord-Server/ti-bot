# Email Configuration Summary

## Problem Solved

The migration script had a security issue where email bounce checking only worked reliably with popular email domains like Gmail. However, the bot was configured to use custom domain SMTP for regular verification emails. This created a conflict where:

1. **Normal verification emails** needed to use the custom domain for branding/security
2. **Migration bounce checking** needed to use Gmail for compatibility with email security measures

## Solution Implemented

### Separate Email Configurations

We now support two separate email configurations:

#### 1. Regular Email Configuration (for normal verification)
- `SMTP_EMAIL` - Your custom domain email
- `SMTP_PASSWORD` - Custom domain SMTP password  
- `SMTP_SERVER` - Custom domain SMTP server
- `SMTP_PORT` - Custom domain SMTP port
- `IMAP_SERVER` - Custom domain IMAP server (if needed)
- `IMAP_PORT` - Custom domain IMAP port (if needed)

#### 2. Migration Email Configuration (for bounce checking)
- `MIGRATION_SMTP_EMAIL` - Gmail address for bounce checking
- `MIGRATION_SMTP_PASSWORD` - Gmail app password
- `MIGRATION_SMTP_SERVER` - Gmail SMTP server (smtp.gmail.com)
- `MIGRATION_SMTP_PORT` - Gmail SMTP port (587)
- `MIGRATION_IMAP_SERVER` - Gmail IMAP server (imap.gmail.com)
- `MIGRATION_IMAP_PORT` - Gmail IMAP port (993)

### How It Works

1. **Normal Verification Flow**:
   - Student requests verification code
   - Bot sends email using regular SMTP configuration (custom domain)
   - Student receives branded email from your domain

2. **Migration Flow**:
   - Ex-student requests migration
   - Bot sends test email using migration SMTP configuration (Gmail)
   - Bot monitors bounces using migration IMAP configuration (Gmail)
   - Gmail's reputation ensures reliable bounce detection

### Files Modified

1. **`env.py`** - Added migration-specific environment variables
2. **`example.env`** - Added example migration email configuration
3. **`cogs/verification.py`** - Updated bounce checking to use migration credentials
4. **`MIGRATION_README.md`** - Updated documentation
5. **`test_email_config.py`** - New testing script

### Testing

Run the email configuration test:
```bash
python test_email_config.py
```

This will verify:
- ✅ Regular SMTP connection (for verification emails)
- ✅ Migration SMTP connection (for bounce checking)
- ✅ Migration IMAP connection (for bounce monitoring)

### Benefits

1. **Reliability**: Gmail credentials ensure bounce checking works consistently
2. **Branding**: Regular verification emails still use your custom domain
3. **Security**: Separate credentials reduce risk if one set is compromised
4. **Flexibility**: Can use different providers for different purposes
5. **Compatibility**: Works around email security measures that block non-popular domains

### Setup Requirements

1. **Custom Domain Email**: Configure your existing SMTP settings
2. **Gmail Account**: 
   - Enable 2-Factor Authentication
   - Generate an "App Password" for the bot
   - Use the app password as `MIGRATION_SMTP_PASSWORD`

This solution maintains the professional appearance of verification emails while ensuring reliable bounce detection for the migration system.