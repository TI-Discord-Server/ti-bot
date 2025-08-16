# TIBot Database Migration

This directory contains the migration script to migrate data from the old TIBot database structure to the new database structure.

## Files

- `migrate.py` - Main migration script
- `MIGRATION_README.md` - This documentation file

## What gets migrated

1. **Email Hashes**: From old `emailData` collection to new `oldEmails` collection
2. **Warns**: From old `warnData` collection to new `infractions` collection

## Prerequisites

1. **Environment Setup**: Ensure you have a `.env` file in the DiscordTI-bot directory with:
   ```
   MONGODB_IP_ADDRESS=your_new_db_host
   MONGODB_PASSWORD=your_new_db_password
   MONGODB_PORT=27017
   MONGODB_USERNAME=your_new_db_username
   OLD_CONNECTION_STRING=mongodb://old_username:old_password@old_host:old_port/old_database
   
   # Regular email settings (for normal verification)
   SMTP_EMAIL=your-custom-domain@example.com
   SMTP_PASSWORD=your_smtp_password
   SMTP_SERVER=smtp.example.com
   SMTP_PORT=587
   
   # Migration email settings (for bounce checking - use Gmail for best compatibility)
   MIGRATION_SMTP_EMAIL=your-gmail@gmail.com
   MIGRATION_SMTP_PASSWORD=your_gmail_app_password
   MIGRATION_SMTP_SERVER=smtp.gmail.com
   MIGRATION_SMTP_PORT=587
   MIGRATION_IMAP_SERVER=imap.gmail.com
   MIGRATION_IMAP_PORT=993
   ```

2. **Email Configuration**: 
   - **Regular SMTP**: Used for sending verification codes to students
   - **Migration SMTP/IMAP**: Used for bounce checking during migration (Gmail recommended for security compatibility)
   - For Gmail accounts, enable 2FA and create an "App Password" for MIGRATION_SMTP_PASSWORD

3. **Dependencies**: Install required Python packages:
   ```bash
   pip install motor pymongo python-dotenv cryptography
   ```

4. **Database Access**: Ensure you have:
   - Read access to the old database
   - Write access to the new database

## Usage

### Test Email Configuration
```bash
python test_email_config.py
```
This will test both regular and migration email configurations to ensure they're working properly.

### Test Database Connections
```bash
python migrate.py --test
```

### Dry Run (See what would be migrated)
```bash
python migrate.py --dry-run
```

### Full Migration
```bash
python migrate.py
```

### Help
```bash
python migrate.py --help
```

## Safety Features

- **Connection Testing**: Tests both database connections before starting
- **Duplicate Prevention**: Skips records that have already been migrated
- **Verification**: Counts records before and after migration to verify success
- **Rollback Support**: Maintains references to old records for potential rollback
- **Error Handling**: Continues migration even if individual records fail

## Migration Details

### Email Hashes Migration
- **Source**: `TIBot.emailData` collection
- **Target**: `bot.oldEmails` collection
- **Structure**: 
  ```json
  {
    "user_id": 123456789,
    "email_hash": "sha256_hash_of_email",
    "migrated_at": "2025-01-10T12:00:00Z"
  }
  ```

### Warns Migration
- **Source**: `TIBot.warnData` collection  
- **Target**: `bot.infractions` collection
- **Structure**:
  ```json
  {
    "guild_id": 771394209419624489,
    "user_id": 123456789,
    "moderator_id": 987654321,
    "type": "warn",
    "reason": "Reason for warn",
    "timestamp": "2025-01-10T12:00:00Z",
    "old_warn_id": "original_warn_id",
    "migrated_at": "2025-01-10T12:00:00Z"
  }
  ```

## Post-Migration Steps

1. **Test Verification**: Ensure the updated verification system works with migrated data
2. **Monitor Logs**: Watch for any issues with the new system
3. **Backup**: Keep backups of both old and new databases
4. **Update Documentation**: Update any documentation referencing the old database structure

## Troubleshooting

### Connection Issues
- Verify database credentials in `.env` file
- Check network connectivity to both databases
- Ensure databases are running and accessible

### Migration Failures
- Check database permissions (read on old, write on new)
- Review error messages for specific issues
- Use `--dry-run` to identify problems before actual migration

### Verification Failures
- Compare record counts manually if verification fails
- Check for any data corruption or connection issues during migration
- Re-run migration (it will skip already migrated records)

## Support

If you encounter issues:
1. Check the error messages in the console output
2. Verify your environment configuration
3. Test database connections with `--test` flag
4. Use `--dry-run` to identify issues without making changes