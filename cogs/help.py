import discord
from discord import app_commands
from discord.ext import commands


class Help(commands.Cog, name="help"):
    def __init__(self, bot):
        self.bot = bot
        # Note: remove_command only affects prefix commands, not slash commands
        # self.bot.remove_command("help")  # Removes the built-in help command

    @app_commands.command(
        name="help", description="Krijg een lijst van alle beschikbare commando's."
    )
    async def help_command(self, interaction: discord.Interaction):
        """Displays a help menu with all available slash commands."""

        try:
            # Log that the help command was called
            self.bot.log.info(f"Help command called by {interaction.user} in {interaction.guild}")

            # Get all commands from the command tree
            commands = self.bot.tree.get_commands()
            self.bot.log.info(f"Found {len(commands)} commands in tree")

            embed = discord.Embed(
                title="📋 Help Menu",
                description="Here are all the available commands:",
                color=discord.Color.blue(),
            )

            # Check if we have any commands
            if not commands:
                embed.add_field(
                    name="No Commands Found",
                    value="No slash commands are currently registered.",
                    inline=False,
                )
            else:
                # Loop through all registered commands, filtering for slash commands only
                allowed_commands = []
                context_menus = []

                for c in commands:
                    try:
                        if await c._check_can_run(interaction):
                            if hasattr(c, "type") and c.type in [2, 3]:  # Context menu
                                context_menus.append(c)
                            elif hasattr(c, "description"):
                                allowed_commands.append(c)
                    except Exception:
                        # Commando kan niet uitgevoerd worden door deze user
                        continue

                if not allowed_commands and not context_menus:
                    embed.add_field(
                        name="Geen commando's",
                        value="Je hebt momenteel geen toegankelijke commando's.",
                        inline=False,
                    )
                else:
                    # Group commands by cog/category to avoid the 25 field limit
                    command_groups = {}
                    for c in allowed_commands:
                        # Try to get the cog name from the command
                        cog_name = getattr(c, "module", "General")
                        if cog_name.startswith("cogs."):
                            cog_name = cog_name.split(".")[-1].title()

                        if cog_name not in command_groups:
                            command_groups[cog_name] = []
                        command_groups[cog_name].append(c)

                    # If we have too many groups, combine them into a single field
                    # Discord limit is 25 fields, so we need to be conservative
                    if (
                        len(command_groups) > 15
                    ):  # Leave room for context menus and potential field splits
                        command_list = []
                        for c in allowed_commands:
                            command_list.append(
                                f"**/{c.name}** - {c.description or 'No description'}"
                            )

                        # Split into chunks to avoid hitting character limits
                        chunk_size = 20
                        for i in range(0, len(command_list), chunk_size):
                            chunk = command_list[i : i + chunk_size]
                            field_name = (
                                f"📋 Commands ({i+1}-{min(i+chunk_size, len(command_list))})"
                            )
                            embed.add_field(name=field_name, value="\n".join(chunk), inline=False)
                    else:
                        # Add commands grouped by category
                        field_count = 0
                        max_fields = 24  # Leave room for context menus

                        for cog_name, cog_commands in command_groups.items():
                            if field_count >= max_fields:
                                break

                            command_list = []
                            for c in cog_commands:
                                command_list.append(
                                    f"**/{c.name}** - {c.description or 'No description'}"
                                )

                            # Check if the field value would be too long (Discord limit is 1024 chars)
                            field_value = "\n".join(command_list)
                            if len(field_value) > 1000:  # Leave some buffer
                                # Split into multiple fields if too long
                                chunk_size = 5
                                for i in range(0, len(command_list), chunk_size):
                                    if field_count >= max_fields:
                                        break
                                    chunk = command_list[i : i + chunk_size]
                                    chunk_value = "\n".join(chunk)
                                    if len(chunk_value) <= 1000:
                                        field_name = (
                                            f"📁 {cog_name}" if i == 0 else f"📁 {cog_name} (cont.)"
                                        )
                                        embed.add_field(
                                            name=field_name, value=chunk_value, inline=False
                                        )
                                        field_count += 1
                            else:
                                embed.add_field(
                                    name=f"📁 {cog_name}", value=field_value, inline=False
                                )
                                field_count += 1

                # Add context menu info if any exist
                if context_menus:
                    context_names = [c.name for c in context_menus]
                    embed.add_field(
                        name="🖱️ Context Menu Commands",
                        value=f"Right-click commands: {', '.join(context_names)}",
                        inline=False,
                    )

            embed.set_footer(
                text="Gebruik een commando door / te typen gevolgd door de commandonaam."
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            # Fallback response if there's any error
            try:
                await interaction.response.send_message(
                    f"❌ Error loading help menu: {str(e)}", ephemeral=True
                )
            except discord.InteractionResponded:
                # If even the error response fails, try a followup
                try:
                    await interaction.followup.send(
                        f"❌ Error loading help menu: {str(e)}", ephemeral=True
                    )
                except Exception:
                    pass  # Give up if everything fails

    @app_commands.command(
        name="debug_commands", description="Debug commando om geregistreerde commando's te bekijken"
    )
    @app_commands.default_permissions(administrator=True)
    async def debug_commands(self, interaction: discord.Interaction):
        """Debug command to see what commands are registered."""
        try:
            commands = self.bot.tree.get_commands()
            cogs = list(self.bot.cogs.keys())

            embed = discord.Embed(
                title="🔧 Debug Info",
                color=discord.Color.orange(),
            )

            # Separate different types of commands
            slash_commands = []
            context_menus = []
            other_commands = []

            for cmd in commands:
                if hasattr(cmd, "type") and cmd.type in [2, 3]:  # Context menu
                    context_menus.append(f"- {cmd.name} (type: {cmd.type})")
                elif hasattr(cmd, "description"):  # Slash command
                    slash_commands.append(f"- /{cmd.name}: {cmd.description}")
                else:
                    other_commands.append(f"- {cmd.name} ({type(cmd).__name__})")

            command_info = []
            if slash_commands:
                command_info.append(
                    f"**Slash Commands ({len(slash_commands)}):**\n" + "\n".join(slash_commands[:5])
                )
                if len(slash_commands) > 5:
                    command_info.append(f"... and {len(slash_commands) - 5} more slash commands")

            if context_menus:
                command_info.append(
                    f"**Context Menus ({len(context_menus)}):**\n" + "\n".join(context_menus)
                )

            if other_commands:
                command_info.append(
                    f"**Other Commands ({len(other_commands)}):**\n" + "\n".join(other_commands)
                )

            embed.add_field(
                name="Registered Commands",
                value=(
                    f"Found {len(commands)} total commands:\n\n" + "\n\n".join(command_info)
                    if command_info
                    else "No commands found"
                ),
                inline=False,
            )

            embed.add_field(
                name="Loaded Cogs",
                value=f"Found {len(cogs)} cogs:\n" + ", ".join(cogs),
                inline=False,
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"Debug error: {str(e)}", ephemeral=True)


async def setup(bot):
    help_cog = Help(bot)
    await bot.add_cog(help_cog)
