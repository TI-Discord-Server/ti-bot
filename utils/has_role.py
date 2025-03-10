import functools
import discord


def has_role(role, error_message=None):
    """
    A custom decorator that checks if a user has a specific role by ID or name.
    Automatically responds with an error message if the check fails.

    Parameters:
    - role_id: The ID of the role to check for
    - role_name: The name of the role to check for (used if role_id is not provided)
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

            has_required_role = False

            if isinstance(role, int):
                # Check by role ID (preferred method)
                has_required_role = any(r.id == role for r in interaction.user.roles)
            else:
                # Check by role name (fallback)
                has_required_role = any(r.name == role for r in interaction.user.roles)

            if not has_required_role:
                # Use custom error message or default
                message = error_message or "You don't have permission to use this command."
                await interaction.response.send_message(message, ephemeral=True)
                return None

            return await func(self, interaction, *args, **kwargs)

        return wrapper

    return decorator