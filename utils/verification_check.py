import discord

async def ensure_verified_role(bot, interaction: discord.Interaction) -> None:
    guild = interaction.guild
    settings = await bot.db.settings.find_one({"_id": "verification_settings"})
    verified_role_id = settings.get("verified_role_id")
    role = guild.get_role(verified_role_id) if verified_role_id else None

    if role and role not in interaction.user.roles:
        try:
            await interaction.user.add_roles(role)
            bot.log.debug(f"Re-assigned Verified role to {interaction.user} ({interaction.user.id})")
        except Exception as e:
            bot.log.error(f"Failed to re-assign Verified role to {interaction.user} ({interaction.user.id}): {e}", exc_info=True)
