"""
Utility for managing persistent views that survive bot restarts.
"""
import discord
from discord.ext import commands
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class PersistentViewManager:
    """Manages persistent views that need to survive bot restarts."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.collection = bot.db.persistent_views
    
    async def store_view_message(self, 
                                view_type: str, 
                                channel_id: int, 
                                message_id: int, 
                                guild_id: int,
                                additional_data: Dict[str, Any] = None):
        """
        Store information about a message containing a persistent view.
        
        Args:
            view_type: Type of view (e.g., 'role_selector', 'verification', 'channel_menu', etc.)
            channel_id: ID of the channel containing the message
            message_id: ID of the message containing the view
            guild_id: ID of the guild
            additional_data: Any additional data needed to recreate the view
        """
        document = {
            "_id": f"{view_type}_{guild_id}_{channel_id}_{message_id}",
            "view_type": view_type,
            "channel_id": channel_id,
            "message_id": message_id,
            "guild_id": guild_id,
            "additional_data": additional_data or {}
        }
        
        try:
            await self.collection.replace_one(
                {"_id": document["_id"]}, 
                document, 
                upsert=True
            )
            logger.info(f"Stored persistent view: {view_type} in channel {channel_id}, message {message_id}")
        except Exception as e:
            logger.error(f"Failed to store persistent view {view_type}: {e}")
    
    async def get_view_messages(self, view_type: str = None, guild_id: int = None) -> List[Dict[str, Any]]:
        """
        Get stored view messages.
        
        Args:
            view_type: Filter by view type (optional)
            guild_id: Filter by guild ID (optional)
            
        Returns:
            List of view message documents
        """
        query = {}
        if view_type:
            query["view_type"] = view_type
        if guild_id:
            query["guild_id"] = guild_id
            
        try:
            cursor = self.collection.find(query)
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Failed to get view messages: {e}")
            return []
    
    async def remove_view_message(self, channel_id: int, message_id: int):
        """Remove a stored view message (e.g., when message is deleted)."""
        try:
            result = await self.collection.delete_many({
                "channel_id": channel_id,
                "message_id": message_id
            })
            if result.deleted_count > 0:
                logger.info(f"Removed {result.deleted_count} persistent view(s) for message {message_id}")
        except Exception as e:
            logger.error(f"Failed to remove persistent view for message {message_id}: {e}")
    
    async def restore_views(self):
        """Restore all persistent views on bot startup."""
        logger.info("Starting persistent view restoration...")
        
        try:
            # Check if collection exists and has documents
            try:
                count = await self.collection.count_documents({})
                if count == 0:
                    logger.info("No persistent views found to restore (first run or empty collection)")
                    return
            except Exception as e:
                logger.info(f"Persistent views collection doesn't exist yet or is inaccessible: {e}")
                return
            
            view_messages = await self.get_view_messages()
            if not view_messages:
                logger.info("No persistent views found to restore")
                return
                
            restored_count = 0
            failed_count = 0
            
            for view_data in view_messages:
                try:
                    success = await self._restore_single_view(view_data)
                    if success:
                        restored_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    logger.error(f"Failed to restore view {view_data.get('_id', 'unknown')}: {e}")
                    failed_count += 1
            
            logger.info(f"Persistent view restoration complete: {restored_count} restored, {failed_count} failed")
            
        except Exception as e:
            logger.error(f"Failed to restore persistent views: {e}")
            # Don't re-raise the exception to prevent bot startup failure
    
    async def _restore_single_view(self, view_data: Dict[str, Any]) -> bool:
        """Restore a single persistent view."""
        view_type = view_data["view_type"]
        channel_id = view_data["channel_id"]
        message_id = view_data["message_id"]
        guild_id = view_data["guild_id"]
        additional_data = view_data.get("additional_data", {})
        
        # Get the channel and message
        channel = self.bot.get_channel(channel_id)
        if not channel:
            logger.warning(f"Channel {channel_id} not found for view {view_type}")
            return False
        
        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            logger.warning(f"Message {message_id} not found for view {view_type}, removing from database")
            await self.remove_view_message(channel_id, message_id)
            return False
        except discord.Forbidden:
            logger.warning(f"No permission to access message {message_id} for view {view_type}")
            return False
        
        # Create and add the appropriate view
        view = await self._create_view(view_type, guild_id, additional_data)
        if view:
            self.bot.add_view(view, message_id=message_id)
            logger.debug(f"Restored {view_type} view for message {message_id}")
            return True
        else:
            logger.warning(f"Failed to create view of type {view_type}")
            return False
    
    async def _create_view(self, view_type: str, guild_id: int, additional_data: Dict[str, Any]) -> Optional[discord.ui.View]:
        """Create a view instance based on the view type."""
        try:
            if view_type == "verification":
                from cogs.verification import VerificationView
                return VerificationView(self.bot)
            
            elif view_type == "role_selector":
                role_selector_cog = self.bot.get_cog("RoleSelector")
                if role_selector_cog:
                    from cogs.role_selector import RoleSelectorView
                    view = RoleSelectorView(role_selector_cog)
                    # Refresh the view with current categories
                    try:
                        categories = await role_selector_cog.get_categories()
                        await view.refresh(categories)
                    except Exception as e:
                        logger.error(f"Failed to refresh role selector view with categories: {e}")
                        # Return the view anyway, it will work with empty categories
                    return view
            
            elif view_type == "channel_menu":
                from cogs.channel_menu import YearSelectView
                return YearSelectView(self.bot)
            
            elif view_type == "confession":
                from cogs.confessions.confession_view import ConfessionView
                return ConfessionView(self.bot)
            
            elif view_type == "rules":
                from cogs.confessions.rules_modal import RulesView
                return RulesView(self.bot)
            
            elif view_type == "unban_request":
                unban_cog = self.bot.get_cog("UnbanRequest")
                if unban_cog and hasattr(unban_cog, 'unban_view'):
                    return unban_cog.unban_view
            
            else:
                logger.warning(f"Unknown view type: {view_type}")
                return None
                
        except ImportError as e:
            logger.error(f"Failed to import view class for {view_type}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create view {view_type}: {e}")
            return None