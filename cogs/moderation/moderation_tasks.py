import asyncio
import datetime
import discord
from .moderation_utils import log_infraction


class ModerationTasks:
    """Handles background tasks for moderation operations."""
    
    def __init__(self, bot, scheduled_unmutes_collection, infractions_collection):
        self.bot = bot
        self.scheduled_unmutes_collection = scheduled_unmutes_collection
        self.infractions_collection = infractions_collection
        self.unmute_task = None

    def start_unmute_checker(self):
        """Start the background task to check for scheduled unmutes."""
        if self.unmute_task is None or self.unmute_task.done():
            self.unmute_task = asyncio.create_task(self.check_scheduled_unmutes())

    def stop_unmute_checker(self):
        """Stop the background task."""
        if self.unmute_task and not self.unmute_task.done():
            self.unmute_task.cancel()

    async def check_scheduled_unmutes(self):
        """Background task to check and process scheduled unmutes."""
        while True:
            try:
                current_time = datetime.datetime.utcnow()
                
                # Find all unmutes that should be processed
                expired_unmutes = await self.scheduled_unmutes_collection.find({
                    "unmute_at": {"$lte": current_time}
                }).to_list(length=None)
                
                for unmute_data in expired_unmutes:
                    try:
                        guild = self.bot.get_guild(unmute_data["guild_id"])
                        if not guild:
                            # Guild not found, remove the scheduled unmute
                            await self.scheduled_unmutes_collection.delete_one({"_id": unmute_data["_id"]})
                            continue
                        
                        member = guild.get_member(unmute_data["user_id"])
                        if not member:
                            # Member not found, remove the scheduled unmute
                            await self.scheduled_unmutes_collection.delete_one({"_id": unmute_data["_id"]})
                            continue
                        
                        # Get muted role
                        muted_role = discord.utils.get(guild.roles, name="Muted")
                        if muted_role and muted_role in member.roles:
                            # Remove muted role
                            await member.remove_roles(muted_role, reason="Scheduled unmute expired")
                            
                            # Send DM to user
                            try:
                                dm_embed = discord.Embed(
                                    title="🔓 | Je bent automatisch geunmute.",
                                    description=f"Je scheduled mute in {guild.name} is verlopen.",
                                    color=discord.Color.green(),
                                )
                                await member.send(embed=dm_embed)
                            except (discord.errors.Forbidden, discord.errors.HTTPException):
                                pass  # Couldn't send DM, but that's okay
                            
                            # Log the automatic unmute
                            try:
                                await log_infraction(
                                    self.infractions_collection,
                                    guild.id, member.id, self.bot.user.id, "auto_unmute", 
                                    f"Scheduled unmute after {unmute_data.get('original_duration', 'unknown duration')}"
                                )
                            except Exception as e:
                                self.bot.log.error(f"Failed to log auto unmute infraction: {e}")
                        
                        # Remove the scheduled unmute from database
                        await self.scheduled_unmutes_collection.delete_one({"_id": unmute_data["_id"]})
                        
                    except Exception as e:
                        self.bot.log.error(f"Error processing scheduled unmute for user {unmute_data.get('user_id')}: {e}")
                        # Don't remove from database if there was an error, try again later
                
                # Wait 60 seconds before checking again
                await asyncio.sleep(60)
                
            except Exception as e:
                self.bot.log.error(f"Error in scheduled unmute checker: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def schedule_unmute(self, guild_id: int, user_id: int, unmute_at: datetime.datetime, 
                             original_duration: str, reason: str):
        """Schedule an unmute for a specific time."""
        unmute_data = {
            "guild_id": guild_id,
            "user_id": user_id,
            "unmute_at": unmute_at,
            "original_duration": original_duration,
            "reason": reason,
            "created_at": datetime.datetime.utcnow()
        }
        
        # Remove any existing scheduled unmute for this user in this guild
        await self.scheduled_unmutes_collection.delete_many({
            "guild_id": guild_id,
            "user_id": user_id
        })
        
        # Insert the new scheduled unmute
        await self.scheduled_unmutes_collection.insert_one(unmute_data)

    async def cancel_scheduled_unmute(self, guild_id: int, user_id: int):
        """Cancel a scheduled unmute for a user."""
        result = await self.scheduled_unmutes_collection.delete_many({
            "guild_id": guild_id,
            "user_id": user_id
        })
        return result.deleted_count > 0