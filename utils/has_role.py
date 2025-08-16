import functools
import discord


def has_role(role, error_message=None):
    """
    A custom decorator that checks if a user has a specific role by ID or name.
    For role name checks, ensures the user has the highest role with that name in the server.
    Automatically responds with an error message if the check fails.

    Parameters:
    - role: The ID or name of the role to check for
    - error_message: Custom error message to show (defaults to a standard message)
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Handle both regular commands (self, interaction, ...) and context menu commands (interaction, target, ...)
            if len(args) >= 2 and hasattr(args[0], '__class__') and hasattr(args[1], 'response'):
                # Regular command: (self, interaction, ...)
                self, interaction = args[0], args[1]
                remaining_args = args[2:]
            elif len(args) >= 1 and hasattr(args[0], 'response'):
                # Context menu command: (interaction, target, ...)
                interaction = args[0]
                remaining_args = args[1:]
                self = None
            else:
                raise ValueError("Unable to determine command type from arguments")

            if interaction.guild is None:
                await interaction.response.send_message(
                    "This command can only be used in a server.", ephemeral=True
                )
                return None

            has_required_role = False
            
            # Always allow users with administrator permissions
            if any(r.permissions.administrator for r in interaction.user.roles):
                has_required_role = True
            else:
                # Check by role ID or name
                if isinstance(role, int):
                    # Check by role ID (preferred method)
                    has_required_role = any(r.id == role for r in interaction.user.roles)
                else:
                    # For role name checks, we need to find the highest role with that name in the server
                    # and check if the user has it
                    
                    # First, find all roles in the server with the given name
                    server_roles_with_name = [r for r in interaction.guild.roles if r.name == role]
                    
                    if server_roles_with_name:
                        # Sort roles by position (higher position = higher in hierarchy)
                        server_roles_with_name.sort(key=lambda r: r.position, reverse=True)
                        
                        # Get the highest role with the given name
                        highest_role = server_roles_with_name[0]
                        
                        # Check if the user has this specific role
                        has_required_role = any(r.id == highest_role.id for r in interaction.user.roles)

            if not has_required_role:
                # Use custom error message or default
                message = error_message or "You don't have permission to use this command."
                await interaction.response.send_message(message, ephemeral=True)
                # Log permission denied attempt
                if hasattr(interaction, 'command') and interaction.command:
                    command_name = interaction.command.name
                else:
                    command_name = func.__name__
                print(f"Permission denied: User {interaction.user.name} ({interaction.user.id}) tried to use {command_name} without required role '{role}'")
                return None

            # Call the original function with the correct arguments
            if self is not None:
                # Regular command: call with self, interaction, and remaining args
                return await func(self, interaction, *remaining_args, **kwargs)
            else:
                # Context menu command: call with interaction and remaining args
                return await func(interaction, *remaining_args, **kwargs)

        return wrapper

    return decorator