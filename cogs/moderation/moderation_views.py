import discord
from typing import Callable, Optional


class TimeoutFallbackView(discord.ui.View):
    """View for confirming fallback to muted role when timeout exceeds 28 days."""
    
    def __init__(self, original_user: discord.Member, target_member: discord.Member, 
                 duration: str, reason: str, mute_callback: Optional[Callable] = None):
        super().__init__(timeout=60.0)
        self.original_user = original_user
        self.target_member = target_member
        self.duration = duration
        self.reason = reason
        self.mute_callback = mute_callback
        self.responded = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the original command user to interact with the buttons."""
        if interaction.user.id != self.original_user.id:
            await interaction.response.send_message(
                "Only the person who ran the command can interact with these buttons.", 
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Yes, Use Muted Role", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_mute_fallback(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm using muted role as fallback."""
        if self.responded:
            return
        self.responded = True
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        # Update the message to show it's being processed
        embed = discord.Embed(
            title="Processing...",
            description=f"Using muted role for {self.target_member.mention} for {self.duration}...",
            color=discord.Color.yellow()
        )
        await interaction.response.edit_message(embed=embed, view=self)
        
        # Execute the mute callback with scheduled unmute
        if self.mute_callback:
            await self.mute_callback(interaction, self.target_member, self.reason, self.duration, scheduled=True)

    @discord.ui.button(label="No, Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_fallback(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the fallback operation."""
        if self.responded:
            return
        self.responded = True
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        embed = discord.Embed(
            title="Cancelled",
            description=f"The timeout operation for {self.target_member.mention} has been cancelled.",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        """Handle view timeout."""
        if not self.responded:
            # Disable all buttons
            for item in self.children:
                item.disabled = True


class OverwriteConfirmationView(discord.ui.View):
    """View for confirming overwrite of existing timeout/mute."""
    
    def __init__(self, original_user: discord.Member, target_member: discord.Member, 
                 action_type: str, new_duration: str = None, reason: str = None, 
                 timeout_callback: Optional[Callable] = None, mute_callback: Optional[Callable] = None):
        super().__init__(timeout=60.0)
        self.original_user = original_user
        self.target_member = target_member
        self.action_type = action_type
        self.new_duration = new_duration
        self.reason = reason
        self.timeout_callback = timeout_callback
        self.mute_callback = mute_callback
        self.responded = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the original command user to interact with the buttons."""
        if interaction.user.id != self.original_user.id:
            await interaction.response.send_message(
                "Only the person who ran the command can interact with these buttons.", 
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Yes, Overwrite", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm_overwrite(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm overwriting the existing timeout/mute."""
        if self.responded:
            return
        self.responded = True
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        # Update the message to show it's being processed
        embed = discord.Embed(
            title="Processing...",
            description=f"Overwriting existing {self.action_type} for {self.target_member.mention}...",
            color=discord.Color.yellow()
        )
        await interaction.response.edit_message(embed=embed, view=self)
        
        # Execute the appropriate callback
        if self.action_type == "timeout" and self.timeout_callback:
            await self.timeout_callback(interaction, self.target_member, self.new_duration, self.reason, overwrite=True)
        elif self.action_type == "mute" and self.mute_callback:
            await self.mute_callback(interaction, self.target_member, self.reason, overwrite=True)

    @discord.ui.button(label="No, Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_overwrite(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the overwrite operation."""
        if self.responded:
            return
        self.responded = True
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        embed = discord.Embed(
            title="Cancelled",
            description=f"The {self.action_type} operation for {self.target_member.mention} has been cancelled.",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        """Handle view timeout."""
        if not self.responded:
            # Disable all buttons
            for item in self.children:
                item.disabled = True