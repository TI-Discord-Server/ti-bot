# TI Discord Bot Documentation

## Overview

The TI Discord Bot is a comprehensive moderation and management system designed for the HOGENT Applied Computer Science (Toegepaste Informatica) student Discord server. Built with Python 3.13 and discord.py, it provides student verification, moderation tools, anonymous confessions, modmail support, and various community features.

## Key Features

### Verification System
- Email-based verification for HOGENT students (`@student.hogent.be`)
- Encrypted email storage using Fernet encryption
- Migration support for graduated students
- Manual verification tools for moderators

### Moderation Suite
- Complete moderation commands: kick, ban, unban, warn, timeout, mute
- Warning system with history tracking
- Case management and logging
- Purge/bulk delete functionality
- Ban checking and lookup

### Communication Systems
- **Modmail**: Private ticket system for member-staff communication
- **Confessions**: Anonymous confession posting with approval workflow
- **Reports**: User and message reporting system
- **Job Info**: Platform for students to share job experiences

### Server Management
- Year and track-based channel access control
- Role selection interface
- Unban request system
- Configurable settings via `/configure` command
- Developer management system

### Utility Features
- Custom help command
- Exam results date announcements
- Ping/latency checker
- Webhook logging with Discord integration

## Technology Stack

- **Language**: Python 3.13
- **Discord Library**: discord.py 2.4.0
- **Database**: MongoDB with Motor (async driver)
- **Email**: SMTP/IMAP support for verification
- **Encryption**: Cryptography (Fernet) for secure data storage
- **Code Quality**: Black, Ruff, pre-commit hooks

## Documentation Structure

This documentation is split into specialized guides:

- **[2-SETUP.md](docs/2-SETUP.md)** - Installation, configuration, and deployment instructions
- **[3-ARCHITECTURE.md](docs/3-ARCHITECTURE.md)** - Code structure, cogs overview, and system design
- **[4-COMMANDS_REFERENCE.md](docs/4-COMMANDS_REFERENCE.md)** - Complete command reference with examples
- **[5-CONTRIBUTING.md](docs/5-CONTRIBUTING.md)** - Guidelines for developers and contributors
- **[6-TROUBLESHOOTING.md](docs/6-TROUBLESHOOTING.md)** - Common issues and debugging tips
- **[7-LIMITATIONS.md](docs/7-LIMITATIONS.md)** - Known limitations and security considerations

## Quick Start (TL;DR)

### Prerequisites
- Python 3.13 or Docker
- MongoDB instance
- Discord bot token
- SMTP/IMAP email credentials

### Docker Deployment (Recommended)
```bash
# 1. Copy environment template
cp example.env .env

# 2. Edit .env with your credentials
# (BOT_TOKEN, MONGODB settings, SMTP settings, etc.)

# 3. Generate encryption keys
python3 generate_key.py

# 4. Start MongoDB
docker compose up mongo -d

# 5. Create MongoDB user (see 2-SETUP.md for details)

# 6. Start bot
docker compose up webapp -d
```

### Local Development
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up .env file (copy from example.env)

# 3. Run the bot
python3 main.py
```

## Intended Audience

- **Server Administrators**: Configure and manage bot features
- **Moderators**: Use moderation tools and handle reports/tickets
- **Developers**: Contribute to bot development or deploy custom instances
- **Students**: Understand available bot features and commands

## Getting Help

- Check [6-TROUBLESHOOTING.md](6-TROUBLESHOOTING.md) for common issues
- Review [4-COMMANDS_REFERENCE.md](4-COMMANDS_REFERENCE.md) for command usage
- Contact the development team through modmail on the TI Discord server

## License

This project is maintained by the HOGENT TI Discord Server team.

---

**Next Steps**: See [2-SETUP.md](2-SETUP.md) for detailed installation instructions.
