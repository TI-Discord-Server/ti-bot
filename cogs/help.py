import discord
from discord.app_commands import command
from discord.ext import commands


class Help(commands.Cog, name="help"):
    def __init__(self, bot):
        self.bot = bot
        # Note: remove_command only affects prefix commands, not slash commands
        # self.bot.remove_command("help")  # Removes the built-in help command

    @command(name="help", description="Get a list of all available commands.")
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
                slash_commands = []
                context_menus = []
                
                for c in commands:
                    # Check if it's a context menu command or slash command
                    if hasattr(c, 'type') and c.type in [2, 3]:  # USER or MESSAGE context menu
                        context_menus.append(c)
                    elif hasattr(c, 'description'):  # Regular slash command
                        slash_commands.append(c)
                
                # Add slash commands
                for c in slash_commands:
                    embed.add_field(
                        name=f"/{c.name}",
                        value=c.description or "No description",
                        inline=False,
                    )
                
                # Add context menu info if any exist
                if context_menus:
                    context_names = [c.name for c in context_menus]
                    embed.add_field(
                        name="🖱️ Context Menu Commands",
                        value=f"Right-click commands: {', '.join(context_names)}",
                        inline=False,
                    )

            embed.set_footer(text="Gebruik een commando door / te typen gevolgd door de commandonaam.")

            await interaction.response.send_message(
                embed=embed, ephemeral=True
            )
            
        except Exception as e:
            # Fallback response if there's any error
            try:
                await interaction.response.send_message(
                    f"❌ Error loading help menu: {str(e)}", 
                    ephemeral=True
                )
            except:
                # If even the error response fails, try a followup
                try:
                    await interaction.followup.send(
                        f"❌ Error loading help menu: {str(e)}", 
                        ephemeral=True
                    )
                except:
                    pass  # Give up if everything fails

    @command(name="debug_commands", description="Debug command to see registered commands")
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
                if hasattr(cmd, 'type') and cmd.type in [2, 3]:  # Context menu
                    context_menus.append(f"- {cmd.name} (type: {cmd.type})")
                elif hasattr(cmd, 'description'):  # Slash command
                    slash_commands.append(f"- /{cmd.name}: {cmd.description}")
                else:
                    other_commands.append(f"- {cmd.name} ({type(cmd).__name__})")
            
            command_info = []
            if slash_commands:
                command_info.append(f"**Slash Commands ({len(slash_commands)}):**\n" + "\n".join(slash_commands[:5]))
                if len(slash_commands) > 5:
                    command_info.append(f"... and {len(slash_commands) - 5} more slash commands")
            
            if context_menus:
                command_info.append(f"**Context Menus ({len(context_menus)}):**\n" + "\n".join(context_menus))
            
            if other_commands:
                command_info.append(f"**Other Commands ({len(other_commands)}):**\n" + "\n".join(other_commands))
            
            embed.add_field(
                name="Registered Commands",
                value=f"Found {len(commands)} total commands:\n\n" + "\n\n".join(command_info) if command_info else "No commands found",
                inline=False
            )
            
            embed.add_field(
                name="Loaded Cogs",
                value=f"Found {len(cogs)} cogs:\n" + ", ".join(cogs),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"Debug error: {str(e)}", ephemeral=True)


async def setup(bot):
    help_cog = Help(bot)
    await bot.add_cog(help_cog)
    bot.log.info("Help cog loaded successfully")
