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
   ```

2. **Dependencies**: Install required Python packages:
   ```bash
   pip install motor pymongo python-dotenv
   ```

3. **Database Access**: Ensure you have:
   - Read access to the old database
   - Write access to the new database

## Usage

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