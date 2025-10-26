# Troubleshooting Guide

Common issues, solutions, and debugging tips for the TI Discord Bot.

## Table of Contents
- [Bot Issues](#bot-issues)
- [Command Issues](#command-issues)
- [Database Issues](#database-issues)
- [Email Verification Issues](#email-verification-issues)
- [Modmail Issues](#modmail-issues)
- [Permission Issues](#permission-issues)
- [Deployment Issues](#deployment-issues)
- [Debugging Tips](#debugging-tips)
- [FAQ](#faq)

---

## Bot Issues

### Bot Won't Start

#### Symptom
Bot doesn't come online, process exits immediately.

#### Possible Causes & Solutions

**1. Missing or Invalid BOT_TOKEN**
```bash
# Check .env file
cat .env | grep BOT_TOKEN

# Ensure token is wrapped in quotes and valid
BOT_TOKEN='YOUR_ACTUAL_TOKEN_HERE'
```

**2. Database Connection Failed**
```bash
# Test MongoDB connection
docker compose ps  # Check if mongo is running

# Check MongoDB logs
docker compose logs mongo

# Verify credentials in .env
MONGODB_USERNAME=bot
MONGODB_PASSWORD=yourpassword123!
```

**3. Missing Environment Variables**
```bash
# Check required variables
python3 -c "from env import *; print('All env vars loaded')"

# If error, check which variable is missing
```

**4. Python Version Mismatch**
```bash
# Verify Python version
python3 --version  # Should be 3.13

# Install correct version or update Dockerfile
```

**5. Missing Dependencies**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or rebuild Docker image
docker compose build webapp
```

### Bot Crashes Randomly

#### Symptom
Bot goes offline unexpectedly.

#### Solutions

**Check Logs**:
```bash
# Docker
docker compose logs webapp -f

# Local
cat bot.log | tail -100
```

**Common Crash Causes**:
- Unhandled exceptions in event handlers
- MongoDB connection lost
- Discord API timeout
- Memory issues (check container limits)

**Fixes**:
```bash
# Increase Docker memory limit in docker-compose.yml
resources:
  limits:
    memory: 512M

# Enable automatic restart
restart: unless-stopped
```

### Bot Online But Unresponsive

#### Symptom
Bot appears online but doesn't respond to commands.

#### Solutions

**1. Commands Not Synced**
```
!sync
```

**2. Intents Not Enabled**
- Go to Discord Developer Portal
- Enable required Privileged Gateway Intents
- Restart bot

**3. Bot Stuck in Loop**
Check logs for repeated error messages:
```bash
docker compose logs webapp | grep ERROR
```

---

## Command Issues

### Commands Not Showing

#### Symptom
Slash commands don't appear in Discord autocomplete.

#### Solutions

**1. Run Sync Command**
```
!sync
```
Wait 5-10 minutes for Discord to update.

**2. Restart Discord Client**
```
Ctrl+R (Windows/Linux)
Cmd+R (Mac)
```

**3. Check Bot Permissions**
- Bot needs `applications.commands` scope
- Verify in Server Settings → Integrations

**4. Check Guild ID**
```python
# In .env, verify DISCORD_GUILD_ID matches your server
DISCORD_GUILD_ID=771394209419624489
```

**5. Clear Discord Cache**
- Close Discord
- Delete cache folder:
  - Windows: `%AppData%\Discord\Cache`
  - Mac: `~/Library/Application Support/Discord/Cache`
  - Linux: `~/.config/discord/Cache`
- Restart Discord

### Command Returns "Application Did Not Respond"

#### Symptom
Command appears to run but times out after 3 seconds.

#### Causes & Solutions

**1. Missing `interaction.response`**
```python
# Bad - no response
@app_commands.command()
async def slow_command(self, interaction: discord.Interaction):
    await slow_operation()  # Takes > 3 seconds

# Good - defer first
@app_commands.command()
async def slow_command(self, interaction: discord.Interaction):
    await interaction.response.defer()  # Or defer(ephemeral=True)
    await slow_operation()
    await interaction.followup.send("Done!")
```

**2. Exception Before Response**
Check logs for errors thrown before `interaction.response.send_message()`.

**3. Database Timeout**
```python
# Add timeout to database queries
await self.bot.db.collection.find_one({"_id": id}, timeout=5000)
```

### Command Permission Denied

#### Symptom
"You don't have permission to use this command"

#### Solutions

**1. Check Required Permissions**
```python
# Look for decorators in code
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.checks.has_role(860195356493742100)
```

**2. Verify Role ID**
The hardcoded moderator role ID is `860195356493742100`. Either:
- Create a role with this ID (not possible)
- Modify code to use your role ID

**3. Check Bot Role Hierarchy**
Bot's role must be higher than roles it manages.

---

## Database Issues

### Connection Refused

#### Symptom
```
pymongo.errors.ServerSelectionTimeoutError: connection refused
```

#### Solutions

**1. MongoDB Not Running**
```bash
docker compose up mongo -d
docker compose ps  # Verify mongo is "Up"
```

**2. Wrong Host/Port**
```bash
# Docker: use 'mongo'
MONGODB_IP_ADDRESS='mongo'

# Local: use 'localhost'
MONGODB_IP_ADDRESS='localhost'
```

**3. Firewall Blocking Port**
```bash
# Check if port 27017 is open
netstat -an | grep 27017

# Allow in firewall
sudo ufw allow 27017
```

### Authentication Failed

#### Symptom
```
pymongo.errors.OperationFailure: Authentication failed
```

#### Solutions

**1. Wrong Credentials**
```bash
# Verify .env matches MongoDB user
MONGODB_USERNAME=bot
MONGODB_PASSWORD=yourpassword123!
```

**2. User Doesn't Exist**
```javascript
// Connect to MongoDB and create user
use bot
db.createUser({
  user: "bot",
  pwd: "yourpassword123!",
  roles: [{ role: "readWrite", db: "bot" }]
})
```

**3. Wrong Database**
```bash
# Ensure MONGODB_DB matches the database where user was created
MONGODB_DB=bot
```

### Database Queries Hanging

#### Symptom
Bot freezes when querying database.

#### Solutions

**1. Add Timeout**
```python
result = await self.bot.db.collection.find_one({"_id": id}, timeout=5000)
```

**2. Check Indices**
```javascript
// Create index on frequently queried fields
db.verifications.createIndex({"user_id": 1})
db.warnings.createIndex({"user_id": 1})
```

**3. Limit Query Results**
```python
# Bad - fetches everything
all_docs = await self.bot.db.collection.find({}).to_list(length=None)

# Good - limit results
docs = await self.bot.db.collection.find({}).to_list(length=100)
```

---

## Email Verification Issues

### Email Not Sending

#### Symptom
Users don't receive verification codes.

#### Solutions

**1. Test Email Configuration**
```bash
python3 test_email_config.py
```

**2. Check SMTP Credentials**
```bash
# For Gmail, use app password, not regular password
SMTP_PASSWORD='your_app_password_here'  # NOT your Gmail password
```

**3. Generate Gmail App Password**
- Enable 2FA on Google account
- Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
- Create app password for "Mail"
- Use that password in `.env`

**4. Check SMTP Server/Port**
```bash
# Gmail
SMTP_SERVER='smtp.gmail.com'
SMTP_PORT=587  # STARTTLS

# Or
SMTP_PORT=465  # SSL
```

**5. Test SMTP Manually**
```python
import smtplib
smtp = smtplib.SMTP('smtp.gmail.com', 587)
smtp.starttls()
smtp.login('your_email@gmail.com', 'your_app_password')
smtp.quit()
print("Success!")
```

### Email Arrives in Spam

#### Solutions
- Use a verified email domain
- Add SPF/DKIM records to domain
- Ask users to check spam folder
- Users should mark as "Not Spam"

### "Email Already Registered" Error

#### Symptom
User gets error even though they haven't verified before.

#### Causes & Solutions

**1. Email Actually Registered**
```python
# Check database
await bot.db.verifications.find_one({"email_index": hashed_email})
```

**2. Previous Verification Attempt**
User may have verified on another account. Use `/get_email` to check.

**3. Migration Issue**
Old verification data without `email_index`. Run:
```
/migrate_email_index
```

### Code Expired Error

#### Symptom
"Your verification code has expired"

#### Solutions
- Codes expire after 10 minutes (defined as `CODE_EXPIRY = 600`)
- User should request a new code
- Check system time is correct (affects timestamp comparison)

---

## Modmail Issues

### Modmail Doesn't Create Thread

#### Symptom
User DMs bot but no thread is created.

#### Solutions

**1. Check Configuration**
```
/configure → Modmail → Set category and log channel
```

**2. Verify Category Exists**
Category ID in database must match existing category in Discord.

**3. Check Bot Permissions**
Bot needs:
- Manage Channels
- Send Messages
- Manage Threads

**4. Check Logs**
```bash
docker compose logs webapp | grep -i modmail
```

### Can't Close Thread

#### Symptom
`/close` command fails or says "not a ticket channel"

#### Solutions

**1. Verify in Modmail Thread**
Command must be used in thread created by bot.

**2. Check Database**
```python
# Verify thread exists in database
await bot.db.threads.find_one({"channel_id": thread_id})
```

**3. Thread Sync Issue**
Thread may exist in Discord but not in database. Use `/contact` to manually create thread reference.

---

## Permission Issues

### "Missing Permissions" Error

#### Symptom
Commands fail with permission errors.

#### Solutions

**1. Bot Role Position**
- Bot's role must be above roles it manages
- Server Settings → Roles → Drag bot role higher

**2. Channel Permissions**
- Check channel-specific permissions
- Bot needs relevant permissions in that channel

**3. Required Discord Permissions**
Ensure bot has in Server Settings → Bot:
- Manage Roles
- Manage Channels
- Kick Members
- Ban Members
- Manage Messages
- Read Messages
- Send Messages
- Manage Threads
- Read Message History

**4. Moderator Role Hardcoded**
If role ID `860195356493742100` doesn't exist:
- Create role (can't set exact ID)
- Modify code to use your role ID
- Update in all cogs that reference it

### Developer Commands Don't Work

#### Symptom
`!sync`, `!restart`, `!shutdown` don't respond or say "permission denied"

#### Solutions

**1. Add Yourself to Developers**
```javascript
// In MongoDB
use bot
db.settings.updateOne(
  { _id: "server_settings" },
  { $set: { developer_ids: [YOUR_USER_ID] } },
  { upsert: true }
)
```

**2. Get Your User ID**
- Enable Developer Mode in Discord settings
- Right-click your profile → Copy ID

**3. Restart Bot**
After adding yourself, restart bot to reload developer IDs.

---

## Deployment Issues

### Docker Build Fails

#### Symptom
`docker build` or `docker compose build` fails

#### Solutions

**1. Check Dockerfile Syntax**
```bash
docker build -t tibot-v3 . --no-cache
```

**2. Network Issues**
```bash
# Try different base image mirror
# Or use --network=host
docker build --network=host -t tibot-v3 .
```

**3. Disk Space**
```bash
# Check disk space
df -h

# Clean Docker cache
docker system prune -a
```

### Container Keeps Restarting

#### Symptom
`docker compose ps` shows container constantly restarting

#### Solutions

**1. Check Logs**
```bash
docker compose logs webapp -f
```

**2. Remove Restart Policy Temporarily**
```yaml
# In docker-compose.yml, comment out:
# restart: unless-stopped
```

**3. Run Interactively**
```bash
docker compose run --rm webapp python3 main.py
```

---

## Debugging Tips

### Enable Debug Logging

**In code**:
```python
# In main.py, change log level
self.bot.log.setLevel(logging.DEBUG)
```

**Check specific logger**:
```python
discord_log = logging.getLogger("discord")
discord_log.setLevel(logging.DEBUG)
```

### Inspect Database

```bash
# Connect to MongoDB
docker exec -it mongo mongosh -u bot -p yourpassword123! --authenticationDatabase bot bot

# Or use MongoDB Compass GUI
mongodb://bot:yourpassword123!@localhost:27017/bot
```

**Useful queries**:
```javascript
// Check settings
db.settings.findOne({_id: "server_settings"})

// Check verifications
db.verifications.find({}).limit(10)

// Check warnings
db.warnings.find({user_id: 123456789}).toArray()

// Count documents
db.threads.countDocuments({open: true})
```

### Test Commands in Python

```python
# In Python shell with bot running
import discord
from discord.ext import commands

# Your testing code here
```

### Check Bot Permissions

```python
# In a command
perms = interaction.guild.me.guild_permissions
print(f"Manage roles: {perms.manage_roles}")
print(f"Kick members: {perms.kick_members}")
print(f"Ban members: {perms.ban_members}")
```

### Monitor Webhook Logs

If `WEBHOOK_URL` is set, check the Discord channel for real-time logs.

---

## FAQ

### Q: Why aren't my commands showing up?
**A**: Run `!sync`, wait 5-10 minutes, restart Discord client.

### Q: How do I add a developer?
**A**: Insert your user ID into `developer_ids` array in database settings document.

### Q: Can I change the moderator role?
**A**: Yes, but you must update the hardcoded role ID `860195356493742100` in multiple cog files. Search codebase for this ID.

### Q: Email verification isn't working. Why?
**A**: Run `python3 test_email_config.py` to diagnose. Most common issue is not using Gmail app password.

### Q: How do I migrate old verification data?
**A**: Set `OLD_CONNECTION_STRING` in `.env` and users can use "Ik ben afgestudeerd" button. Then run `/migrate_email_index`.

### Q: Bot is slow. How to improve performance?
**A**: 
- Add database indices
- Use `defer()` for slow commands
- Increase Docker resources
- Check MongoDB connection pool settings

### Q: How do I reset the database?
**A**: 
```javascript
// ⚠️ WARNING: Deletes all data
use bot
db.dropDatabase()
```

### Q: Where are logs stored?
**A**: 
- File: `bot.log` (rotated at 1MB)
- Console: stdout/stderr
- Discord: Webhook channel (if configured)

### Q: Can I run multiple bots with same database?
**A**: Not recommended. Each bot instance should have its own database.

### Q: How do I backup the database?
**A**:
```bash
# Backup
docker exec mongo mongodump --username bot --password yourpassword123! --authenticationDatabase bot --db bot --out /backup

# Restore
docker exec mongo mongorestore --username bot --password yourpassword123! --authenticationDatabase bot /backup/bot
```

---

## Getting Further Help

### Still Stuck?

1. **Check Logs First**: Most issues are logged
2. **Review Architecture**: See [3-ARCHITECTURE.md](3-ARCHITECTURE.md)
3. **Check Code**: Search codebase for error messages
4. **Open an Issue**: Provide logs and steps to reproduce

### Providing Debug Info

When asking for help, include:
- Bot version (git commit hash)
- Python version
- Docker version (if using Docker)
- Full error message from logs
- Steps to reproduce
- What you've already tried

### Useful Log Commands

```bash
# Last 100 lines
docker compose logs webapp --tail 100

# Follow logs in real-time
docker compose logs webapp -f

# Logs from specific time
docker compose logs webapp --since 2024-01-01T00:00:00

# Search logs
docker compose logs webapp | grep ERROR
```

---

## Next Steps

- [2-SETUP.md](2-SETUP.md) - Review setup steps
- [3-ARCHITECTURE.md](3-ARCHITECTURE.md) - Understand the system
- [5-CONTRIBUTING.md](5-CONTRIBUTING.md) - Fix bugs or add features
