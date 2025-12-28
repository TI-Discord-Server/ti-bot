# Contributing Guide

Thank you for your interest in contributing to the TI Discord Bot! This guide will help you set up your development environment and follow project conventions.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Branch Workflow](#branch-workflow)
- [Adding Features](#adding-features)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Code Review](#code-review)

---

## Getting Started

### Prerequisites

- Python 3.13
- Git
- Discord bot token (for testing)
- MongoDB instance
- Familiarity with discord.py

### Skills Needed

- **Python**: Async/await, decorators, classes
- **Discord.py**: Cogs, commands, views, modals
- **MongoDB**: Basic queries (find, update, insert)
- **Git**: Branching, committing, pull requests

---

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub/GitLab first
git clone https://github.com/YOUR_USERNAME/ti-bot.git
cd ti-bot
```

### 2. Install Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 3. Set Up Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install
```

This automatically runs Black and Ruff on every commit to ensure code quality.

### 4. Configure Environment

```bash
# Copy example environment file
cp example.env .env

# Edit .env with your development credentials
# Use a separate test Discord server and bot token
```

### 5. Set Up Test Server

Create a test Discord server with:

- Bot added with necessary permissions
- Test channels for each feature
- Moderator role (update hardcoded ID `860195356493742100` or create role with this ID)
- Test users for verification testing

### 6. Initialize Database

```bash
# Start MongoDB (if using Docker)
docker compose up mongo -d

# Create bot user (see 2-SETUP.md)
```

### 7. Add Yourself as Developer

```javascript
// Connect to MongoDB and run:
use bot
db.settings.updateOne(
  { _id: "server_settings" },
  { $set: { developer_ids: [YOUR_USER_ID] } },
  { upsert: true }
)
```

### 8. Run the Bot

```bash
python3 main.py
```

### 9. Sync Commands

In your test server:

```
!sync
```

---

## Code Style

### Python Style Guide

We use **Black** for formatting and **Ruff** for linting.

#### Black Configuration

- Line length: 100 characters
- Target version: Python 3.11+

#### Ruff Rules

- E: pycodestyle errors
- F: pyflakes
- I: import sorting
- Ignore E501 (line length - handled by Black)

### Running Linters Manually

```bash
# Check with Ruff
ruff check .

# Auto-fix with Ruff
ruff check --fix .

# Format with Black
black .

# Run all pre-commit checks
pre-commit run --all-files
```

### Code Conventions

#### Imports

```python
# Standard library
import asyncio
import datetime
from typing import Optional

# Third-party
import discord
from discord import app_commands
from discord.ext import commands

# Local
from utils.checks import developer
from utils.errors import UnknownUser
```

#### Async Functions

Always use `async`/`await` for I/O operations:

```python
# Good
async def get_user_data(user_id: int):
    return await bot.db.users.find_one({"user_id": user_id})

# Bad - don't block
def get_user_data(user_id: int):
    return bot.db.users.find_one({"user_id": user_id}).to_list(length=1)
```

#### Type Hints

Use type hints for function parameters and returns:

```python
async def ban_user(
    self,
    interaction: discord.Interaction,
    user: discord.User,
    reason: Optional[str] = None
) -> None:
    ...
```

#### Error Handling

```python
try:
    await risky_operation()
except discord.HTTPException as e:
    self.bot.log.error(f"HTTP error: {e}")
    await interaction.followup.send("An error occurred.", ephemeral=True)
except Exception as e:
    self.bot.log.error(f"Unexpected error: {e}", exc_info=True)
    raise
```

#### Logging

```python
# Use bot's logger
self.bot.log.info(f"User {user.id} verified successfully")
self.bot.log.warning(f"Failed to send email to {email}")
self.bot.log.error(f"Database error: {e}", exc_info=True)
```

#### Database Queries

```python
# Find one document
settings = await self.bot.db.settings.find_one({"_id": "server_settings"}) or {}

# Update document
await self.bot.db.verifications.update_one(
    {"user_id": user.id},
    {"$set": {"email_encrypted": encrypted_email}},
    upsert=True
)

# Find multiple
warnings = await self.bot.db.warnings.find({"user_id": user.id}).to_list(length=None)
```

---

## Branch Workflow

### Branch Structure

- `main`: Stable production code (protected)
- `staging` (or `dev`): Development branch
- Feature branches: Created from `staging`

### Creating a Branch

```bash
# Update staging branch
git checkout staging
git pull origin staging

# Create feature branch
git checkout -b feature/your-feature-name
# or for bug fixes
git checkout -b fix/bug-description
```

### Branch Naming Conventions

- `feature/feature-name`: New features
- `fix/bug-description`: Bug fixes
- `refactor/what-refactored`: Code refactoring
- `docs/what-documented`: Documentation updates

Examples:

- `feature/exam-schedule-command`
- `fix/verification-email-encoding`
- `refactor/modmail-thread-handling`
- `docs/command-reference-update`

### Committing Changes

#### Commit Message Format

```
type(scope): short description

Longer explanation if needed.

Fixes #123
```

**Types**:

- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring
- `docs`: Documentation
- `style`: Formatting (no code change)
- `test`: Adding tests
- `chore`: Maintenance

**Examples**:

```
feat(confessions): add anonymous confession posting

fix(verification): handle email encoding for special characters

refactor(modmail): simplify thread creation logic

docs(commands): update moderation command examples
```

---

## Adding Features

### Adding a New Cog

#### 1. Create Cog File

```python
# cogs/my_feature.py
import discord
from discord import app_commands
from discord.ext import commands

class MyFeature(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @app_commands.command(name="mycommand", description="Does something cool")
    async def my_command(self, interaction: discord.Interaction):
        await interaction.response.send_message("It works!")

    # Event listener example
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        self.bot.log.info(f"{member} joined the server")

async def setup(bot):
    await bot.add_cog(MyFeature(bot))
```

#### 2. Test the Cog

```bash
# Restart bot or reload cog
# In Discord:
!sync
```

#### 3. Add Configuration (if needed)

If your feature needs settings, add a section in `configure.py`:

```python
discord.SelectOption(
    label="My Feature",
    value="my_feature",
    description="Configure my feature",
    emoji="🎯",
)
```

### Adding a New Command

#### Basic Command

```python
@app_commands.command(name="greet", description="Greet a user")
@app_commands.describe(user="The user to greet")
async def greet(self, interaction: discord.Interaction, user: discord.User):
    await interaction.response.send_message(f"Hello, {user.mention}!")
```

#### Command with Permissions

```python
@app_commands.command(name="admin_only", description="Admin-only command")
@is_admin()
async def admin_command(self, interaction: discord.Interaction):
    await interaction.response.send_message("You're an admin!", ephemeral=True)
```

#### Command with Custom Check

```python
from utils.checks import developer

@app_commands.command(name="dev_tool", description="Developer tool")
@developer()
async def dev_tool(self, interaction: discord.Interaction):
    await interaction.response.send_message("Developer access granted!")
```

### Adding a Persistent View

#### 1. Create View

```python
class MyPersistentView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Click Me", custom_id="my_button", style=discord.ButtonStyle.primary)
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Button clicked!", ephemeral=True)
```

#### 2. Register in `utils/persistent_views.py`

```python
async def setup_views(bot):
    bot.add_view(MyPersistentView(bot))
    # ... other views
```

### Adding Database Collections

If you need a new collection:

```python
# In your cog
async def save_data(self, user_id: int, data: dict):
    await self.bot.db.my_collection.update_one(
        {"user_id": user_id},
        {"$set": data},
        upsert=True
    )

async def get_data(self, user_id: int):
    return await self.bot.db.my_collection.find_one({"user_id": user_id})
```

**Document your schema**:

```python
# Collection: my_collection
# Schema:
# {
#   "_id": ObjectId,
#   "user_id": int,
#   "created_at": datetime,
#   "data": dict
# }
```

---

## Testing

### Manual Testing

#### Test Checklist for New Commands

- [ ] Command appears in `/help`
- [ ] Command responds correctly
- [ ] Permission checks work
- [ ] Error messages are user-friendly
- [ ] Database operations succeed
- [ ] Logs are written correctly
- [ ] Works in DMs (if applicable)
- [ ] Works in threads (if applicable)

#### Test Checklist for Views/Modals

- [ ] Buttons/selects appear correctly
- [ ] Callbacks execute successfully
- [ ] Ephemeral responses work
- [ ] Timeout handling works
- [ ] Persistent views survive bot restart

### Email Testing

```bash
# Test email configuration
python3 test_email_config.py
```

### Database Testing

Test database operations in a Python shell:

```python
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def test():
    client = AsyncIOMotorClient("mongodb://bot:password@localhost:27017/bot")
    db = client.bot

    # Test insert
    await db.test_collection.insert_one({"test": "data"})

    # Test find
    doc = await db.test_collection.find_one({"test": "data"})
    print(doc)

    # Cleanup
    await db.test_collection.delete_one({"test": "data"})

asyncio.run(test())
```

### Automated Testing

**Note**: The project does not currently have automated tests. Setting up pytest with discord.py mocks would be a valuable contribution!

Potential test areas:

- Permission checks
- Database operations
- Email sending
- Encryption/decryption
- Time parsing
- Error handling

---

## Pull Request Process

### Before Submitting

1. **Test locally**: Verify all changes work in your test server
2. **Run linters**: Ensure pre-commit hooks pass
3. **Update documentation**: Modify relevant docs if needed
4. **Commit cleanly**: Squash messy commits if needed

### Creating a Pull Request

1. **Push your branch**:

```bash
git push origin feature/your-feature-name
```

2. **Open PR to `staging` branch** (not `main`!)

3. **Fill out PR template** with:
   - **What changed**: List of changes
   - **Why**: Reason for the changes
   - **How to test**: Steps to test the changes
   - **Screenshots**: If UI changes
   - **Related issues**: Link to issue numbers

### PR Title Format

```
[Type] Brief description
```

Examples:

- `[Feature] Add exam schedule command`
- `[Fix] Resolve verification email encoding issue`
- `[Refactor] Simplify modmail thread logic`
- `[Docs] Update command reference`

### PR Description Template

```markdown
## Changes

- Added X feature
- Fixed Y bug
- Refactored Z component

## Why

Explain the motivation for these changes.

## Testing

1. Run `/newcommand`
2. Verify X happens
3. Check logs for Y

## Screenshots

(if applicable)

## Related Issues

Fixes #123
Closes #456
```

---

## Code Review

### Review Process

1. Maintainer reviews code
2. Automated checks run (pre-commit CI)
3. Changes requested or approved
4. Maintainer merges to `staging`
5. After testing, maintainer merges to `main`

### What Reviewers Look For

- Code quality and style
- Security concerns
- Performance issues
- Breaking changes
- Documentation completeness
- Test coverage

### Responding to Reviews

- Address all comments
- Explain decisions
- Update code as requested
- Don't take feedback personally
- Ask questions if unclear

---

## Development Best Practices

### Security

- Never commit `.env` files
- Never log sensitive data (emails, tokens)
- Always encrypt sensitive data in database
- Validate user input
- Use permissions checks on all commands

### Performance

- Use async operations for I/O
- Avoid blocking operations
- Use database indices
- Limit message history caching
- Don't spam Discord API

### Error Handling

- Catch specific exceptions
- Log errors with context
- Provide user-friendly messages
- Don't expose internal errors to users

### Database

- Always use `upsert` for settings
- Use `find_one() or {}` to avoid None checks
- Index frequently queried fields
- Use projections to limit data transfer

### Discord Best Practices

- Use ephemeral responses for sensitive data
- Defer long operations
- Don't edit/delete messages excessively
- Respect rate limits
- Use embeds for rich formatting

---

## Getting Help

### Resources

- [discord.py Documentation](https://discordpy.readthedocs.io/)
- [Discord Developer Portal](https://discord.com/developers/docs)
- [MongoDB Documentation](https://docs.mongodb.com/)
- [3-ARCHITECTURE.md](3-ARCHITECTURE.md) - Bot architecture

### Contact

- Open an issue for bugs
- Discuss in Discord server (if applicable)
- Tag maintainers in PR comments

---

## Recognition

Contributors will be:

- Listed in commit history
- Mentioned in release notes
- Credited for significant features

Thank you for contributing to making the TI Discord Bot better!

---

## Next Steps

- [3-ARCHITECTURE.md](3-ARCHITECTURE.md) - Understand the codebase
- [4-COMMANDS_REFERENCE.md](4-COMMANDS_REFERENCE.md) - See existing commands
- [6-TROUBLESHOOTING.md](6-TROUBLESHOOTING.md) - Debug issues
