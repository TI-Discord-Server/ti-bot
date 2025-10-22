# Commands Reference

Complete reference for all bot commands, organized by category.

## Table of Contents
- [Configuration Commands](#configuration-commands)
- [Moderation Commands](#moderation-commands)
- [Modmail Commands](#modmail-commands)
- [Verification Commands](#verification-commands)
- [Confession Commands](#confession-commands)
- [Report Commands](#report-commands)
- [Utility Commands](#utility-commands)
- [Developer Commands](#developer-commands)

---

## Configuration Commands

### `/configure`
Opens the main bot configuration interface.

**Permissions**: Administrator  
**Usage**: `/configure`

**Features**:
- Server Settings: Configure basic server roles and channels
- Modmail: Set up modmail category and log channel
- Confessions: Configure confession system channels and settings
- Verification: Set verified role and verification channel
- Reports: Configure report channel and moderator role
- Job Info: Set job info channel
- Developer Management: Add/remove bot developers

**Example**:
```
/configure
```
Then select a category from the dropdown menu.

---

## Moderation Commands

All moderation commands require the `manage_messages` permission and the moderator role (ID: `860195356493742100`).

### `/kick`
Kick a member from the server.

**Parameters**:
- `member` (required): The member to kick
- `reason` (optional): Reason for the kick

**Usage**: `/kick @user [reason]`

**Example**:
```
/kick @BadUser Spamming in chat
```

### `/ban`
Ban a member from the server.

**Parameters**:
- `member` (required): The member to ban
- `reason` (optional): Reason for the ban
- `delete_message_days` (optional): Days of messages to delete (0-7)

**Usage**: `/ban @user [reason] [delete_message_days]`

**Example**:
```
/ban @Spammer Repeated spam violations delete_message_days:1
```

### `/unban`
Unban a user from the server.

**Parameters**:
- `user` (required): User ID or username#discriminator
- `reason` (optional): Reason for unban

**Usage**: `/unban <user_id|username> [reason]`

**Example**:
```
/unban 123456789012345678 Appeal accepted
/unban username#1234 Served their time
```

### `/warn`
Issue a warning to a user.

**Parameters**:
- `user` (required): The user to warn
- `reason` (optional): Reason for the warning

**Usage**: `/warn @user [reason]`

**Example**:
```
/warn @User Breaking rule #3
```

### `/warnings`
View all warnings for a user.

**Parameters**:
- `user` (required): The user to check

**Usage**: `/warnings @user`

**Example**:
```
/warnings @User
```

### `/clear_warnings`
Clear all warnings for a user.

**Parameters**:
- `user` (required): The user whose warnings to clear
- `reason` (optional): Reason for clearing

**Usage**: `/clear_warnings @user [reason]`

**Example**:
```
/clear_warnings @User Clean slate after 6 months
```

### `/timeout`
Timeout a member (temporary mute).

**Parameters**:
- `member` (required): The member to timeout
- `duration` (required): Duration (e.g., "1h", "30m", "2d")
- `reason` (optional): Reason for timeout

**Usage**: `/timeout @user <duration> [reason]`

**Example**:
```
/timeout @User 1h Cooling off period
/timeout @User 30m Minor rule violation
```

### `/untimeout`
Remove timeout from a member.

**Parameters**:
- `member` (required): The member to untimeout
- `reason` (optional): Reason for removal

**Usage**: `/untimeout @user [reason]`

**Example**:
```
/untimeout @User Timeout served
```

### `/mute`
Mute a member (removes their ability to speak).

**Parameters**:
- `member` (required): The member to mute
- `duration` (optional): Duration (e.g., "1h", "30m", "2d")
- `reason` (optional): Reason for mute

**Usage**: `/mute @user [duration] [reason]`

**Example**:
```
/mute @User 2h Excessive arguing
```

### `/unmute`
Unmute a member.

**Parameters**:
- `member` (required): The member to unmute
- `reason` (optional): Reason for unmute

**Usage**: `/unmute @user [reason]`

**Example**:
```
/unmute @User Mute period ended
```

### `/purge`
Bulk delete messages from a channel.

**Parameters**:
- `amount` (required): Number of messages to delete (1-100)

**Usage**: `/purge <amount>`

**Example**:
```
/purge 50
```

**Note**: Deletes the most recent messages including the command itself.

### `/ban_check`
Look up ban information by user ID or username.

**Parameters**:
- `user` (required): User ID or username

**Usage**: `/ban_check <user_id|username>`

**Example**:
```
/ban_check 123456789012345678
/ban_check spammer_user
```

### `/case_info`
View detailed information about a moderation case.

**Parameters**:
- `case_id` (required): The case ID to look up

**Usage**: `/case_info <case_id>`

**Example**:
```
/case_info 42
```

---

## Modmail Commands

Modmail commands require the `manage_messages` permission and moderator role, except where noted.

### `/close`
Close the current modmail ticket.

**Parameters**:
- `option` (optional): "silent" to close without notifying user
- `reason` (optional): Reason for closing

**Usage**: `/close [silent] [reason]`

**Examples**:
```
/close
/close silent Issue resolved
/close reason:User stopped responding
```

**Note**: Must be used in a modmail thread channel.

### `/reply`
Reply to a modmail ticket (visible to user).

**Parameters**:
- `message` (required): Your reply message

**Usage**: `/reply <message>`

**Example**:
```
/reply We've looked into your issue and will resolve it within 24 hours.
```

### `/areply`
Reply anonymously to a modmail ticket.

**Parameters**:
- `message` (required): Your anonymous reply

**Usage**: `/areply <message>`

**Example**:
```
/areply Thank you for your report. We're investigating this matter.
```

### `/note`
Add an internal note to a modmail thread (not visible to user).

**Parameters**:
- `message` (required): Your internal note

**Usage**: `/note <message>`

**Example**:
```
/note User has been warned before about this issue
```

### `/edit`
Edit a previously sent modmail message.

**Parameters**:
- `message_id` (required): ID of the message to edit
- `new_content` (required): New message content

**Usage**: `/edit <message_id> <new_content>`

**Example**:
```
/edit 123456789012345678 Updated response with correct information
```

### `/delete`
Delete a modmail message.

**Parameters**:
- `message_id` (required): ID of the message to delete

**Usage**: `/delete <message_id>`

**Example**:
```
/delete 123456789012345678
```

### `/contact`
Open a modmail ticket with a user.

**Parameters**:
- `user` (required): The user to contact
- `category` (optional): Ticket category

**Usage**: `/contact @user [category]`

**Example**:
```
/contact @User Follow-up on previous report
```

### `/nsfw`
Mark a modmail thread as NSFW.

**Usage**: `/nsfw`

**Example**:
```
/nsfw
```

### `/sfw`
Mark a modmail thread as SFW (remove NSFW status).

**Usage**: `/sfw`

**Example**:
```
/sfw
```

### `/modmail_history`
View modmail history for a specific channel/thread.

**Parameters**:
- `channel` (optional): The channel to check

**Usage**: `/modmail_history [channel]`

**Example**:
```
/modmail_history
/modmail_history #ticket-123
```

### `/modmail_user_history`
View all modmail tickets for a specific user.

**Parameters**:
- `user` (required): The user to look up

**Usage**: `/modmail_user_history @user`

**Example**:
```
/modmail_user_history @User
```

---

## Verification Commands

### Verification Buttons (User-facing)
Users interact with persistent buttons in the verification channel:

- **"Stuur code"**: Opens modal to input email and receive verification code
- **"Ik heb een code"**: Opens modal to submit received verification code
- **"Ik ben afgestudeerd"**: Migration option for graduated students

**Email Format**: Must be `@student.hogent.be`  
**Code**: 6-digit numeric code, expires after 10 minutes

### `/get_email`
Retrieve the email address of a verified user.

**Permissions**: Moderator (`manage_messages` + role `860195356493742100`)  
**Parameters**:
- `user` (required): The user to look up

**Usage**: `/get_email @user`

**Example**:
```
/get_email @Student
```

### `/unverify`
Remove a user's verification and kick them from the server.

**Permissions**: Moderator  
**Parameters**:
- `user` (required): The user to unverify
- `reason` (optional): Reason for unverification

**Usage**: `/unverify @user [reason]`

**Example**:
```
/unverify @FakeStudent Used fake email address
```

### `/manual_verify`
Manually verify a user without code (emergency use).

**Permissions**: Moderator  
**Parameters**:
- `user` (required): The user to verify
- `email` (required): The HOGENT student email

**Usage**: `/manual_verify @user <email>`

**Example**:
```
/manual_verify @Student naam.achternaam@student.hogent.be
```

### `/migrate_email_index`
Add email indices to old verification records (one-time migration).

**Permissions**: Administrator  
**Usage**: `/migrate_email_index`

**Example**:
```
/migrate_email_index
```

### `/cleanup_unverified`
Remove all roles from members who aren't verified.

**Permissions**: Administrator  
**Usage**: `/cleanup_unverified`

**Example**:
```
/cleanup_unverified
```

**Warning**: This is a bulk operation affecting all unverified members.

---

## Confession Commands

### Confession Button (User-facing)
Users click the confession button in the designated channel to open the submission modal.

### `/force_review`
Force the bot to process pending confessions for review.

**Permissions**: Moderator  
**Usage**: `/force_review`

**Example**:
```
/force_review
```

### `/force_post`
Force the bot to post approved confessions immediately.

**Permissions**: Moderator  
**Usage**: `/force_post`

**Example**:
```
/force_post
```

### `/confession_stats`
View confession system statistics.

**Permissions**: Moderator  
**Usage**: `/confession_stats`

**Example**:
```
/confession_stats
```

---

## Report Commands

### `/report`
Report a user or message to moderators.

**Parameters**:
- `user` (required): The user to report
- `reason` (required): Reason for the report
- `message_id` (optional): ID of the message to report

**Usage**: `/report @user <reason> [message_id]`

**Examples**:
```
/report @BadUser Spamming advertisements
/report @User Inappropriate behavior message_id:123456789012345678
```

### `/handle_report`
Mark a report as handled (moderators only).

**Permissions**: Moderator  
**Parameters**:
- `report_message_id` (required): ID of the report message

**Usage**: `/handle_report <report_message_id>`

**Example**:
```
/handle_report 123456789012345678
```

---

## Utility Commands

### `/help`
Display all available commands.

**Usage**: `/help`

**Example**:
```
/help
```

Shows a list of all commands you have permission to use.

### `/ping`
Check bot latency.

**Usage**: `/ping`

**Example**:
```
/ping
```

Returns the bot's websocket latency in milliseconds.

### `/when_exam_results`
Check when exam results will be published.

**Usage**: `/when_exam_results`

**Example**:
```
/when_exam_results
```

**Note**: Date must be configured by administrators first.

---

## Developer Commands

Developer commands require your user ID to be in the `developer_ids` list in the database.

### `!sync`
Synchronize slash commands with Discord.

**Type**: Prefix command  
**Usage**: `!sync`

**Example**:
```
!sync
```

Run this after adding or modifying commands.

### `!restart`
Restart the bot process.

**Type**: Prefix command  
**Usage**: `!restart`

**Example**:
```
!restart
```

**Note**: Requires a process manager (Docker, systemd) to actually restart the process.

### `!shutdown`
Gracefully shut down the bot.

**Type**: Prefix command  
**Usage**: `!shutdown`

**Example**:
```
!shutdown
```

---

## Context Menu Commands

Some features are accessible via right-click context menus:

### User Context Menu
Right-click a user → Apps → (available commands based on permissions)

### Message Context Menu
Right-click a message → Apps → (available commands)

**Note**: Context menu commands are automatically registered based on the cog configuration.

---

## Permission Reference

### Permission Levels

| Level | Requirements | Grants Access To |
|-------|-------------|------------------|
| **User** | Verified member | Basic commands, reports, confessions |
| **Moderator** | `manage_messages` permission + role `860195356493742100` | Moderation, modmail, verification lookup |
| **Administrator** | `administrator` permission | Configuration, cleanup commands |
| **Developer** | User ID in `developer_ids` database list | Sync, restart, shutdown, developer management |

### Common Role ID
The moderator role ID `860195356493742100` is hardcoded in several commands. Ensure this role exists in your server or modify the code to use your moderator role ID.

---

## Best Practices

### For Moderators
1. Always provide clear reasons for moderation actions
2. Use `/note` in modmail threads to document decisions
3. Review `/warnings` before taking action
4. Use `/ban_check` to verify ban status before unbanning
5. Close modmail tickets with `/close` when resolved

### For Users
1. Verify your account immediately after joining
2. Use `/report` for genuine issues only
3. Be patient when submitting confessions (they're reviewed)
4. Check `/help` to discover available commands
5. Use modmail (DM the bot) for private staff communication

### For Developers
1. Always run `!sync` after command changes
2. Test in a development server first
3. Monitor logs after deploying changes
4. Use `/configure` instead of direct database edits
5. Document new commands in this reference

---

## Command Not Found?

If a command isn't showing:
1. Run `!sync` (if you're a developer)
2. Restart your Discord client
3. Wait a few minutes (Discord caching)
4. Check you have the required permissions
5. Verify the bot is online and functioning

See [6-TROUBLESHOOTING.md](6-TROUBLESHOOTING.md) for more help.

---

## Next Steps

- [3-ARCHITECTURE.md](3-ARCHITECTURE.md) - Understand how commands work internally
- [5-CONTRIBUTING.md](5-CONTRIBUTING.md) - Add new commands
- [6-TROUBLESHOOTING.md](6-TROUBLESHOOTING.md) - Solve command issues
