#!/usr/bin/env python3
"""
Migration script to migrate data from old TIBot database to new database structure.

This script migrates:
1. Email hashes from old emailData collection to new oldEmails collection
2. Warns from old warnData collection to new infractions collection

Prerequisites:
1. Set up environment variables in .env file (see example.env)
2. Ensure OLD_CONNECTION_STRING points to the old database
3. Ensure new database connection details are correct
4. Install required dependencies: pip install motor pymongo python-dotenv

Usage: 
    python migrate.py              # Run full migration
    python migrate.py --test       # Test connections only
    python migrate.py --dry-run    # Show what would be migrated without doing it

Safety features:
- Tests database connections before starting
- Skips already migrated records
- Provides verification after migration
- Maintains references to old records for rollback if needed
"""

import asyncio
import sys
import urllib.parse
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient

from utils.timezone import LOCAL_TIMEZONE

# Add the DiscordTI-bot directory to the path to import env
sys.path.append("/workspace/DiscordTI-bot")

try:
    from env import (
        MONGODB_IP_ADDRESS,
        MONGODB_PASSWORD,
        MONGODB_PORT,
        MONGODB_USERNAME,
        OLD_CONNECTION_STRING,
    )
except ImportError:
    print("Error: Could not import environment variables from env.py")
    print("Make sure you're running this from the correct directory and env.py exists.")
    sys.exit(1)


class DatabaseMigrator:
    def __init__(self):
        # Setup new database connection
        mongodb_password = urllib.parse.quote_plus(MONGODB_PASSWORD)
        mongodb_username = urllib.parse.quote_plus(MONGODB_USERNAME)
        new_connection_string = f"mongodb://{mongodb_username}:{mongodb_password}@{MONGODB_IP_ADDRESS}:{MONGODB_PORT}/{MONGODB_USERNAME}?authMechanism=SCRAM-SHA-256"

        self.new_client = AsyncIOMotorClient(new_connection_string)
        self.new_db = self.new_client.bot

        # Setup old database connection
        if not OLD_CONNECTION_STRING:
            print("Error: OLD_CONNECTION_STRING not found in environment variables")
            sys.exit(1)

        self.old_client = AsyncIOMotorClient(OLD_CONNECTION_STRING)
        self.old_db = self.old_client["TIBot"]

        print("Database connections initialized")

    async def test_connections(self):
        """Test both database connections"""
        try:
            # Test new database
            await self.new_db.command("ping")
            print("✓ New database connection successful")

            # Test old database
            await self.old_db.command("ping")
            print("✓ Old database connection successful")

        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            return False
        return True

    async def migrate_email_hashes(self, dry_run=False):
        """Migrate email hashes from old emailData to new oldEmails collection"""
        print("\n=== Migrating Email Hashes ===")
        if dry_run:
            print("DRY RUN MODE - No actual changes will be made")

        try:
            # Get all email data from old database
            old_email_data = self.old_db["emailData"]
            email_records = await old_email_data.find({}).to_list(length=None)

            if not email_records:
                print("No email records found in old database")
                return

            print(f"Found {len(email_records)} email records to migrate")

            # Prepare records for new database
            old_emails_collection = self.new_db["oldEmails"]
            migrated_count = 0
            skipped_count = 0

            for record in email_records:
                try:
                    # Check if already migrated
                    existing = await old_emails_collection.find_one({"user_id": record["_id"]})
                    if existing:
                        print(f"Skipping user {record['_id']} - already migrated")
                        skipped_count += 1
                        continue

                    # Create new record structure
                    new_record = {
                        "user_id": record["_id"],  # Discord user ID
                        "email_hash": record["emailHash"],  # Original email hash
                        "migrated_at": datetime.now(LOCAL_TIMEZONE),
                    }

                    if not dry_run:
                        await old_emails_collection.insert_one(new_record)
                    migrated_count += 1
                    print(
                        f"{'[DRY RUN] Would migrate' if dry_run else 'Migrated'} email hash for user {record['_id']}"
                    )

                except Exception as e:
                    print(
                        f"Error migrating email record for user {record.get('_id', 'unknown')}: {e}"
                    )
                    continue

            print(f"Email migration completed: {migrated_count} migrated, {skipped_count} skipped")

        except Exception as e:
            print(f"Error during email migration: {e}")
            raise

    async def migrate_warns(self, dry_run=False):
        """Migrate warns from old warnData to new infractions collection"""
        print("\n=== Migrating Warns ===")
        if dry_run:
            print("DRY RUN MODE - No actual changes will be made")

        try:
            # Get all warn data from old database
            old_warn_data = self.old_db["warnData"]
            warn_records = await old_warn_data.find({}).to_list(length=None)

            if not warn_records:
                print("No warn records found in old database")
                return

            print(f"Found {len(warn_records)} warn records to migrate")

            # Prepare records for new database
            infractions_collection = self.new_db["infractions"]
            migrated_count = 0
            skipped_count = 0

            # Default guild ID (you may need to adjust this)
            DEFAULT_GUILD_ID = 771394209419624489  # mainServerID from old emailVerification.py

            for record in warn_records:
                try:
                    # Check if already migrated (using old warn ID as reference)
                    existing = await infractions_collection.find_one({"old_warn_id": record["_id"]})
                    if existing:
                        print(f"Skipping warn {record['_id']} - already migrated")
                        skipped_count += 1
                        continue

                    # Create new infraction record structure (matching moderation.py log_infraction)
                    new_record = {
                        "guild_id": DEFAULT_GUILD_ID,  # Default guild ID
                        "user_id": record["userID"],
                        "moderator_id": record.get(
                            "staffmember", 0
                        ),  # Staff member who issued the warn
                        "type": "warn",
                        "reason": record["reason"],
                        "timestamp": record["timestamp"],
                        "old_warn_id": record["_id"],  # Keep reference to old warn ID
                        "migrated_at": datetime.now(LOCAL_TIMEZONE),
                    }

                    if not dry_run:
                        await infractions_collection.insert_one(new_record)
                    migrated_count += 1
                    print(
                        f"{'[DRY RUN] Would migrate' if dry_run else 'Migrated'} warn {record['_id']} for user {record['userID']}"
                    )

                except Exception as e:
                    print(f"Error migrating warn record {record.get('_id', 'unknown')}: {e}")
                    continue

            print(f"Warns migration completed: {migrated_count} migrated, {skipped_count} skipped")

        except Exception as e:
            print(f"Error during warns migration: {e}")
            raise

    async def verify_migration(self):
        """Verify the migration was successful"""
        print("\n=== Verifying Migration ===")

        try:
            # Count records in old database
            old_email_count = await self.old_db["emailData"].count_documents({})
            old_warn_count = await self.old_db["warnData"].count_documents({})

            # Count records in new database
            new_email_count = await self.new_db["oldEmails"].count_documents({})
            new_warn_count = await self.new_db["infractions"].count_documents(
                {"type": "warn", "old_warn_id": {"$exists": True}}
            )

            print(f"Old database - Emails: {old_email_count}, Warns: {old_warn_count}")
            print(f"New database - Emails: {new_email_count}, Warns: {new_warn_count}")

            if old_email_count == new_email_count:
                print("✓ Email migration verification successful")
            else:
                print("✗ Email migration verification failed - counts don't match")

            if old_warn_count == new_warn_count:
                print("✓ Warns migration verification successful")
            else:
                print("✗ Warns migration verification failed - counts don't match")

        except Exception as e:
            print(f"Error during verification: {e}")

    async def close_connections(self):
        """Close database connections"""
        self.old_client.close()
        self.new_client.close()
        print("Database connections closed")


async def main():
    """Main migration function"""
    print("=== TIBot Database Migration Script ===")
    print("This script will migrate data from the old database to the new database structure.")
    print()

    # Parse command line arguments
    test_mode = False
    dry_run = False

    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            print("Running in test mode - only testing database connections")
            test_mode = True
        elif sys.argv[1] == "--dry-run":
            print("Running in dry-run mode - showing what would be migrated without making changes")
            dry_run = True
        elif sys.argv[1] in ["--help", "-h"]:
            print(__doc__)
            return

    if not test_mode and not dry_run:
        # Confirm before proceeding with actual migration
        response = input("Do you want to proceed with the migration? (y/N): ")
        if response.lower() not in ["y", "yes"]:
            print("Migration cancelled.")
            return

    migrator = DatabaseMigrator()

    try:
        # Test connections
        if not await migrator.test_connections():
            print("Migration aborted due to connection issues.")
            return

        if test_mode:
            print("✓ Connection test completed successfully!")
            return

        # Perform migrations
        await migrator.migrate_email_hashes(dry_run=dry_run)
        await migrator.migrate_warns(dry_run=dry_run)

        # Verify migration (only if not dry run)
        if not dry_run:
            await migrator.verify_migration()

        print("\n=== Migration Complete ===")
        print("Migration has been completed successfully!")
        print("Next steps:")
        print("1. Update the verification script to use the oldEmails collection")
        print("2. Test the new verification system")
        print("3. Monitor for any issues")

    except Exception as e:
        print(f"\nMigration failed with error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await migrator.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
