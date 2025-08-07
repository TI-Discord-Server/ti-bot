import functools
import discord

# Hardcoded role IDs - these are the official role IDs
# If you don't have these specific IDs, you can set them to None and the function will use position-based checks
MODERATOR_ROLE_ID = None  # Replace with actual ID if known, e.g., 123456789012345678
ADMIN_ROLE_ID = None      # Replace with actual ID if known, e.g., 123456789012345678

# Minimum position in the role hierarchy that roles should have
# Higher number means higher in the hierarchy
MIN_MODERATOR_POSITION = 15  # Adjust based on your server's role hierarchy
MIN_ADMIN_POSITION = 20      # Adjust based on your server's role hierarchy - should be higher than moderator


def has_role(role, error_message=None):
    """
    A custom decorator that checks if a user has a specific role by ID or name.
    For roles named "Moderator" or "Admin", performs additional security checks to prevent spoofing.
    Automatically responds with an error message if the check fails.

    Parameters:
    - role: The ID or name of the role to check for
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
            user_roles = interaction.user.roles
            
            # Special handling for security-sensitive roles to prevent spoofing
            if role == "Moderator":
                for r in user_roles:
                    # If we know the exact role ID, use that as the primary check
                    if MODERATOR_ROLE_ID and r.id == MODERATOR_ROLE_ID:
                        has_required_role = True
                        break
                    
                    # Otherwise, check both name AND position in hierarchy
                    if r.name == "Moderator" and r.position >= MIN_MODERATOR_POSITION:
                        has_required_role = True
                        break
                    
                    # Also allow server administrators to pass this check
                    if r.permissions.administrator:
                        has_required_role = True
                        break
            
            elif role == "Admin":
                for r in user_roles:
                    # If we know the exact role ID, use that as the primary check
                    if ADMIN_ROLE_ID and r.id == ADMIN_ROLE_ID:
                        has_required_role = True
                        break
                    
                    # Otherwise, check both name AND position in hierarchy
                    if r.name == "Admin" and r.position >= MIN_ADMIN_POSITION:
                        has_required_role = True
                        break
                    
                    # Also allow server administrators to pass this check
                    if r.permissions.administrator:
                        has_required_role = True
                        break
            
            else:
                # For other roles, use the original logic
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