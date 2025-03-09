import discord

class KickUserView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)  # 60 second timeout
        self.user_id = user_id

    @discord.ui.button(label="Ja", style=discord.ButtonStyle.danger)
    async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Get the member and kick them
        member = interaction.guild.get_member(self.user_id)
        if member:
            try:
                await member.kick(reason="Email verification removed")
                await interaction.response.send_message(f"Gebruiker {member.name} is succesvol gekickt.")
            except discord.Forbidden:
                await interaction.response.send_message("Ik heb niet genoeg rechten om deze gebruiker te kicken.")
            except Exception as e:
                await interaction.response.send_message(f"Er is iets misgelopen: {e}")
        else:
            await interaction.response.send_message("Gebruiker is niet gevonden in deze server.")
        self.stop()

    @discord.ui.button(label="Nee", style=discord.ButtonStyle.secondary)
    async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("De gebruiker blijft op de server.")
        self.stop()
