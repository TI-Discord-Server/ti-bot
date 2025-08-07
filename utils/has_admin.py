import functools
import discord


def has_admin(error_message=None):
    """
    A custom decorator that checks if a user has administrator permissions.
    Automatically responds with an error message if the check fails.

    Parameters:
    - error_message: Custom error message to show (defaults to a standard message)
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            if interaction.guild is None:
                await interaction.response.send_message(
                    "This command can only be used in a server.", ephemeral=True
                )
                return None

            # Check if the user has administrator permissions
            has_admin_permission = any(r.permissions.administrator for r in interaction.user.roles)

            if not has_admin_permission:
                # Use custom error message or default
                message = error_message or "You need administrator permissions to use this command."
                await interaction.response.send_message(message, ephemeral=True)
                return None

            return await func(self, interaction, *args, **kwargs)

        return wrapper

    return decorator