# Setup Guide

This guide covers installation, configuration, and deployment of the TI Discord Bot.

## Prerequisites

### Required Software
- **Python 3.13** (for local development)
- **Docker & Docker Compose** (for containerized deployment)
- **MongoDB 3.8+** (or use Docker image)
- **Git** (for cloning the repository)

### Required Credentials
- Discord bot token from [Discord Developer Portal](https://discord.com/developers/applications)
- SMTP/IMAP email credentials (Gmail recommended for verification)
- MongoDB credentials

### Discord Bot Setup
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Navigate to "Bot" section and create a bot
4. Enable the following **Privileged Gateway Intents**:
   - Server Members Intent
   - Message Content Intent
   - Presence Intent
5. Copy the bot token for later use
6. Upload custom emojis in the Developer Portal to avoid permission issues

## Installation Methods

### Method 1: Docker Deployment (Recommended)

#### Step 1: Clone Repository
```bash
git clone https://github.com/TI-Discord-Server/ti-bot.git
cd ti-bot
```

#### Step 2: Configure Environment Variables
```bash
# Copy the example environment file
cp example.env .env

# Edit .env with your favorite editor
nano .env
```

See [Environment Variables](#environment-variables) section below for details.

#### Step 3: Generate Encryption Keys
```bash
# Generate Fernet encryption key
python3 generate_key.py

# Copy the output key to your .env file as ENCRYPTION_KEY
```

The `EMAIL_INDEX_KEY` should be a 32-character random string (for email indexing).

#### Step 4: Start MongoDB
```bash
docker compose up mongo -d
```

#### Step 5: Create MongoDB User
Connect to MongoDB using a GUI tool or CLI with:
```
mongodb://root:yourpassword123!@localhost:27017/
```

Run these commands:
```javascript
use bot

db.createUser({
  user: "bot",
  pwd: "yourpassword123!",
  roles: [
    { role: "readWrite", db: "bot" }
  ]
})
```

Use this password as `MONGODB_PASSWORD` in your `.env` file.

#### Step 6: Build Bot Image
```bash
# Standard build (without TLS)
docker build -t tibot-v3 .

# Build with TLS enabled
docker build -t tibot-v3 -e TLS_ENABLED=true .
```

#### Step 7: Start Bot
```bash
docker compose up webapp -d
```

#### Step 8: Verify Bot is Running
```bash
# Check logs
docker compose logs webapp -f

# Check if bot is online in Discord
```

### Method 2: Local Development

#### Step 1: Clone Repository
```bash
git clone https://github.com/TI-Discord-Server/ti-bot.git
cd ti-bot
```

#### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

#### Step 3: Configure Environment
```bash
cp example.env .env
# Edit .env with your credentials
```

#### Step 4: Generate Encryption Keys
```bash
python3 generate_key.py
# Add generated key to .env as ENCRYPTION_KEY
```

#### Step 5: Start MongoDB (Local or Docker)
If using Docker:
```bash
docker compose up mongo -d
```

Create the bot user as described in Docker method Step 5.

#### Step 6: Run the Bot
```bash
# Without TLS
python3 main.py

# With TLS enabled
python3 main.py --tls
python3 main.py --tls=true

# Explicitly disable TLS
python3 main.py --tls=false
```

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `BOT_TOKEN` | Discord bot token | `'XXX'` |
| `MONGODB_IP_ADDRESS` | MongoDB host address | `'mongo'` (Docker) or `'localhost'` |
| `MONGODB_PORT` | MongoDB port | `27017` |
| `MONGODB_USERNAME` | MongoDB username | `'bot'` |
| `MONGODB_PASSWORD` | MongoDB password | `'yourpassword123!'` |
| `MONGODB_DB` | MongoDB database name | `'bot'` |
| `WEBHOOK_URL` | Discord webhook URL for logging | `'https://discord.com/api/webhooks/...'` |
| `SMTP_EMAIL` | Email address for sending verification codes | `'toegepasteinformaticadiscord@gmail.com'` |
| `SMTP_PASSWORD` | SMTP app-specific password | `'password'` |
| `SMTP_SERVER` | SMTP server address | `'smtp.gmail.com'` |
| `SMTP_PORT` | SMTP port | `587` (STARTTLS) or `465` (SSL) |
| `IMAP_SERVER` | IMAP server for receiving emails | `'imap.gmail.com'` |
| `IMAP_PORT` | IMAP port | `993` |
| `ENCRYPTION_KEY` | Fernet encryption key | Generate with `generate_key.py` |
| `EMAIL_INDEX_KEY` | 32-character key for email indexing | Any 32-character string |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_GUILD_ID` | Specific guild ID for testing | `771394209419624489` |
| `POD_UID` | Pod UID for logging (first 5 chars used) | None |
| `OLD_CONNECTION_STRING` | MongoDB URI for migrating old data | None |
| `MIGRATION_SMTP_*` | Separate Gmail credentials for bounce checking | Uses main SMTP if not set |
| `MIGRATION_IMAP_*` | Separate Gmail IMAP for bounce checking | Uses main IMAP if not set |

### Gmail App Password Setup

For SMTP/IMAP to work with Gmail:

1. Enable 2-Factor Authentication on your Google account
2. Go to [Google Account > Security > App passwords](https://myaccount.google.com/apppasswords)
3. Generate an app password for "Mail"
4. Use this app password (not your regular password) in `SMTP_PASSWORD`

## TLS Configuration

The bot supports optional TLS connections to MongoDB:

### Command Line
```bash
# Enable TLS
python3 main.py --tls
python3 main.py --tls=true
python3 main.py --tls=yes

# Disable TLS
python3 main.py --tls=false
python3 main.py --tls=no
```

### Docker Compose
Edit `docker-compose.yml`:
```yaml
webapp:
  environment:
    TLS_ENABLED: true  # or false
```

### Build Time
```bash
docker build -t tibot-v3 -e TLS_ENABLED=true .
```

## Initial Bot Configuration

After the bot is running and online in your Discord server:

### 1. Set Up Developer Access
The bot uses database-stored developer IDs. To add the first developer:

1. Get your Discord user ID (enable Developer Mode in Discord settings, right-click your profile)
2. Manually insert into MongoDB:
```javascript
use bot
db.settings.updateOne(
  { _id: "server_settings" },
  { $set: { developer_ids: [YOUR_USER_ID] } },
  { upsert: true }
)
```

### 2. Sync Commands
Once you're a developer, run:
```
!sync
```
This registers all slash commands with Discord.

### 3. Configure Bot Features
Use `/configure` command to set up:
- Server settings (roles, channels)
- Modmail system
- Confession system
- Verification settings
- Reports system
- Job info system

See [4-COMMANDS_REFERENCE.md](4-COMMANDS_REFERENCE.md) for detailed command usage.

## Testing the Installation

### Basic Tests
1. **Ping test**: Use `/ping` - bot should respond with latency
2. **Help command**: Use `/help` - should show all available commands
3. **Database connection**: Check logs for MongoDB connection success
4. **Verification test**: Try the verification flow in a test channel

### Email Verification Test
```bash
# Run the test script
python3 test_email_config.py
```

This verifies SMTP/IMAP configuration is correct.

## Migration from Old System

If migrating from a previous bot version:

### Step 1: Configure Old Connection
Add to `.env`:
```env
OLD_CONNECTION_STRING='mongodb://username:password@host:port/database'
```

### Step 2: Run Migration
The migration is handled automatically through the verification system. Graduated students can use the "Ik ben afgestudeerd" button in the verification interface.

### Step 3: Migrate Email Indices
Run this command as an administrator:
```
/migrate_email_index
```

This adds email indices to old verification records for duplicate checking.

## Troubleshooting Setup Issues

### Bot doesn't start
- Check logs: `docker compose logs webapp -f`
- Verify `.env` file is complete
- Ensure MongoDB is running and accessible

### Commands not showing
- Run `!sync` to register commands
- Restart Discord client
- Wait a few minutes (Discord caching)

### Email verification fails
- Run `python3 test_email_config.py`
- Verify Gmail app password is correct
- Check SMTP/IMAP ports are not blocked by firewall

### Database connection errors
- Verify MongoDB user exists with correct password
- Check `MONGODB_IP_ADDRESS` matches your setup
- For Docker: use `'mongo'`, for local: use `'localhost'`

For more issues, see [6-TROUBLESHOOTING.md](6-TROUBLESHOOTING.md).

## Next Steps

- [3-ARCHITECTURE.md](3-ARCHITECTURE.md) - Understand the bot's structure
- [4-COMMANDS_REFERENCE.md](4-COMMANDS_REFERENCE.md) - Learn all available commands
- [5-CONTRIBUTING.md](5-CONTRIBUTING.md) - Start contributing to development
