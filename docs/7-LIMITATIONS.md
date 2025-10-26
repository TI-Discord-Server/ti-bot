# Limitations and Considerations

This document outlines known limitations, missing features, security considerations, and the project roadmap for the TI Discord Bot.

## Table of Contents
- [Known Limitations](#known-limitations)
- [Missing Features](#missing-features)
- [Security Considerations](#security-considerations)
- [Performance Constraints](#performance-constraints)
- [Technical Debt](#technical-debt)
- [Future Roadmap](#future-roadmap)

---

## Known Limitations

### Hardcoded Values

#### Moderator Role ID
**Issue**: The moderator role ID `860195356493742100` is hardcoded in multiple cogs.

**Impact**: New servers must either:
- Create a role with this exact ID (impossible)
- Manually update the ID in all files

**Affected Files**:
- `cogs/modmail.py`
- `cogs/verification.py`
- `cogs/moderation/moderation_commands.py`
- `cogs/report.py`
- Others

**Workaround**: Search codebase for `860195356493742100` and replace with your role ID.

**Future Fix**: Store role ID in database configuration instead of hardcoding.

#### Guild ID Default
**Issue**: Default guild ID is `771394209419624489` in `main.py`.

**Impact**: Commands may register to wrong guild if `DISCORD_GUILD_ID` not set.

**Workaround**: Always set `DISCORD_GUILD_ID` in `.env`.

### Email Verification Restrictions

#### Email Domain Limited
**Issue**: Only `@student.hogent.be` emails are accepted.

**Impact**: Cannot be used for other schools or organizations without code modification.

**Location**: `cogs/verification.py` line 36:
```python
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%]+@student\.hogent\.be$")
```

**Workaround**: Modify regex to accept different domains.

#### Code Expiry Fixed
**Issue**: Verification codes expire after exactly 10 minutes (600 seconds).

**Impact**: Cannot be configured per-deployment.

**Location**: `cogs/verification.py` line 38:
```python
CODE_EXPIRY = 600  # 10 minutes
```

**Workaround**: Change constant and restart bot.

#### In-Memory Code Storage
**Issue**: Pending verification codes stored in memory (`pending_codes` dict).

**Impact**: 
- Codes lost on bot restart
- Not suitable for multi-instance deployments
- Memory grows if codes aren't cleaned up

**Location**: `cogs/verification.py` line 41

**Future Fix**: Store codes in database with TTL index.

### Database Limitations

#### No Automatic Migrations
**Issue**: Database schema changes require manual intervention.

**Impact**: Updates may break if database structure changes.

**Workaround**: Document schema changes and provide migration scripts.

#### No Connection Pooling Configuration
**Issue**: Motor uses default connection pool settings.

**Impact**: May not be optimal for high-load scenarios.

**Future Fix**: Add configurable pool size in environment variables.

#### No Data Validation
**Issue**: No schema validation on document insertion.

**Impact**: Incorrect data can be stored without error.

**Future Fix**: Implement Pydantic models or MongoDB schema validation.

### Modmail Limitations

#### No Multi-Server Support
**Issue**: Thread manager doesn't isolate threads per guild.

**Impact**: Bot shouldn't be used in multiple servers simultaneously.

**Location**: `utils/thread.py`

**Future Fix**: Add guild_id to thread tracking.

#### Thread History Limited
**Issue**: No pagination for thread history commands.

**Impact**: Users with many threads may hit message limits.

**Workaround**: Manually query database for full history.

### Configuration Limitations

#### Settings in Single Document
**Issue**: All settings stored in one MongoDB document with `_id: "server_settings"`.

**Impact**: 
- No versioning
- No easy rollback
- Risk of data corruption on concurrent updates

**Future Fix**: Split into multiple documents with proper versioning.

#### No Configuration Validation
**Issue**: Invalid configuration (e.g., non-existent channel IDs) not validated on save.

**Impact**: Features break silently until tested.

**Future Fix**: Validate channel/role existence when saving configuration.

---

## Missing Features

### Not Implemented

#### Automated Testing
**Status**: No automated tests exist

**Impact**: Regressions may go unnoticed

**Suggested Implementation**:
- pytest with discord.py mocks
- Test database operations
- Test permission checks
- Test error handling

#### Rate Limiting
**Status**: No command rate limiting

**Impact**: Users can spam commands

**Suggested Implementation**:
- Cooldown decorators per user/guild
- Configurable limits in database
- Automatic cleanup of cooldown tracking

#### Audit Logging
**Status**: Limited logging of administrative actions

**Impact**: Hard to track who changed what

**Suggested Implementation**:
- Log all configuration changes
- Log all moderation actions with timestamp
- Queryable audit log via command

#### Backup System
**Status**: No automated backups

**Impact**: Risk of data loss

**Suggested Implementation**:
- Scheduled MongoDB dumps
- S3/cloud storage integration
- Configurable retention policy

#### Multi-Language Support
**Status**: All text is in Dutch

**Impact**: Not usable for non-Dutch speakers

**Suggested Implementation**:
- i18n library integration
- Translation files
- Per-user language preferences

#### Web Dashboard
**Status**: No web interface for configuration

**Impact**: All configuration requires Discord commands

**Suggested Implementation**:
- Flask/FastAPI web app
- OAuth2 Discord login
- Visual configuration interface

#### Analytics
**Status**: No usage statistics or metrics

**Impact**: Can't track bot usage patterns

**Suggested Implementation**:
- Command usage tracking
- User activity metrics
- Export to Grafana/similar

#### Scheduled Messages
**Status**: No announcement scheduling

**Impact**: Manual posting required

**Suggested Implementation**:
- Schedule messages via command
- Recurring announcements
- Timezone support

---

## Security Considerations

### Encryption

#### Email Encryption
**Implementation**: Fernet symmetric encryption

**Strength**: AES-128 in CBC mode with HMAC

**Key Storage**: Environment variable (not ideal for production)

**Recommendation**: Use key management service (KMS) for production deployments

#### Email Index Hashing
**Implementation**: HMAC-SHA256 for duplicate detection

**Purpose**: Allow checking if email exists without storing plaintext

**Limitation**: Not secure against rainbow table attacks if key is compromised

### Authentication

#### Developer Access
**Method**: User IDs stored in database

**Risk**: Database compromise grants developer access

**Mitigation**: 
- Limit database access
- Use audit logging
- Implement 2FA for critical operations (future)

#### No API Authentication
**Issue**: Bot has no API endpoint, but if added, would need authentication

**Future Consideration**: JWT tokens for web dashboard

### Data Protection

#### Sensitive Data in Logs
**Risk**: Logs may contain user IDs, email info

**Mitigation**: 
- Don't log encrypted emails
- Careful with error messages
- Rotate logs frequently

#### Database Access
**Current**: Basic username/password authentication

**Recommendation for Production**:
- Use TLS for MongoDB connections (supported via `--tls` flag)
- Restrict MongoDB network access
- Use strong passwords (20+ characters)
- Enable MongoDB audit logging

#### Environment Variables
**Current**: Stored in `.env` file

**Risk**: File readable by anyone with filesystem access

**Recommendation**:
- Use secret management (Docker secrets, Kubernetes secrets)
- Restrict file permissions: `chmod 600 .env`
- Don't commit `.env` to version control

### Discord Security

#### Token Security
**Current**: Token in environment variable

**Risk**: Token compromise allows full bot control

**Mitigation**:
- Regenerate token if compromised
- Limit bot permissions to minimum required
- Monitor bot activity

#### Webhook URL
**Current**: Stored in environment variable

**Risk**: URL leak allows spam to log channel

**Mitigation**:
- Use dedicated log channel
- Restrict channel access
- Regenerate webhook if leaked

#### Permission Escalation
**Risk**: Bot can assign roles higher than its own

**Mitigation**: Bot role position determines what it can assign

**Recommendation**: Keep bot role below administrator roles

### Code Execution

#### Owner Commands Disabled
**Good**: `owner_disabled.py` contains dangerous commands (`!py` for code execution)

**Status**: Not loaded by default, but code exists

**Recommendation**: Delete file if not needed, or protect with additional authentication

### Input Validation

#### User Input Sanitized
**Status**: Basic validation exists for:
- Email format (regex)
- User ID format (int conversion)

**Missing**:
- Message length limits
- Special character filtering
- SQL injection (N/A - using MongoDB)

**Recommendation**: Add comprehensive input validation to all commands

---

## Performance Constraints

### Discord Rate Limits

#### API Rate Limits
**Limitation**: Discord imposes rate limits on API calls

**Impact**: Bulk operations may fail or slow down

**Mitigation**: 
- Bot uses default discord.py rate limiting
- Avoid bulk operations when possible

#### Message Send Limit
**Limitation**: ~5 messages per 5 seconds per channel

**Impact**: Rapid replies may be delayed

**Current Handling**: Webhook logging includes rate limiting

### Database Performance

#### No Query Optimization
**Issue**: No query explain analysis

**Impact**: Slow queries on large collections

**Recommendation**:
- Add indices on frequently queried fields
- Use projections to limit data transfer
- Monitor query performance

#### No Connection Pooling Tuning
**Issue**: Default Motor connection pool (100 connections)

**Impact**: May be overkill for small deployments

**Recommendation**: Configure based on expected load

### Memory Usage

#### Message Cache
**Setting**: `max_messages=10_000` in bot initialization

**Impact**: ~10MB-50MB memory usage for message cache

**Tradeoff**: Faster lookups vs memory usage

#### Persistent Views
**Issue**: All persistent views loaded at startup

**Impact**: Minimal for current implementation

**Future Concern**: Many complex views could increase memory

### Startup Time

#### Cog Loading
**Current**: Serial loading of all cogs

**Impact**: Slow startup with many cogs (~2-5 seconds)

**Optimization**: Parallel cog loading (future)

---

## Technical Debt

### Code Duplication

#### Permission Checks
**Issue**: Same role ID check repeated in multiple files

**Impact**: Changes require updating multiple files

**Fix**: Create centralized permission decorator

#### Embed Creation
**Issue**: Similar embed code repeated across cogs

**Impact**: Inconsistent styling

**Fix**: Create embed factory utility

### Inconsistent Error Handling

**Issue**: Some cogs use custom error classes, others don't

**Impact**: Inconsistent user experience

**Fix**: Standardize error handling across all cogs

### Legacy Code

#### `settings_old.py`
**Status**: Legacy setup command

**Replaced By**: `/configure` command

**Action**: Can be removed after migration

#### `owner_disabled.py`
**Status**: Disabled owner commands

**Action**: Remove if not needed

### Missing Documentation

#### Code Comments
**Issue**: Many functions lack docstrings

**Impact**: Hard for new contributors to understand

**Fix**: Add comprehensive docstrings

#### API Documentation
**Issue**: No API documentation for utilities

**Impact**: Developers must read code

**Fix**: Generate docs with Sphinx or similar

---

## Future Roadmap

### Short Term (Next Release)

- [ ] Move hardcoded role IDs to configuration
- [ ] Add configuration validation
- [ ] Implement command cooldowns
- [ ] Add comprehensive docstrings
- [ ] Remove legacy code (`settings_old.py`, `owner_disabled.py`)

### Medium Term (6 Months)

- [ ] Implement automated testing
- [ ] Add audit logging system
- [ ] Store verification codes in database
- [ ] Multi-server support for modmail
- [ ] Configuration versioning and rollback
- [ ] Web dashboard (basic)

### Long Term (1+ Year)

- [ ] Multi-language support
- [ ] Analytics and metrics
- [ ] Automated backups
- [ ] Advanced web dashboard
- [ ] Plugin system for custom features
- [ ] Performance monitoring and alerting

### Potential Features (Under Consideration)

- [ ] Voice channel management
- [ ] Poll system
- [ ] Server statistics
- [ ] Welcome/goodbye messages
- [ ] Auto-moderation (spam, links, etc.)
- [ ] Ticket system (alternative to modmail)
- [ ] Integration with external services (GitHub, GitLab)
- [ ] Custom command aliases

---

## Contributing to Roadmap

Have ideas for improvements? See [5-CONTRIBUTING.md](5-CONTRIBUTING.md) for how to:
- Open feature requests
- Discuss proposals
- Submit pull requests
- Vote on priorities

---

## Version Information

**Current Version**: Based on commit at time of documentation  
**Last Updated**: October 2025  
**Supported Python**: 3.13  
**Supported Discord.py**: 2.4.0

---

## Next Steps

- [2-SETUP.md](2-SETUP.md) - Deploy despite limitations
- [3-ARCHITECTURE.md](3-ARCHITECTURE.md) - Understand the system
- [5-CONTRIBUTING.md](5-CONTRIBUTING.md) - Help address limitations
- [6-TROUBLESHOOTING.md](6-TROUBLESHOOTING.md) - Work around issues
