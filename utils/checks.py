from discord.app_commands import check
from discord.interactions import Interaction
from ..main import DEVELOPER_IDS__THIS_WILL_GIVE_OWNER_COG_PERMS as developer_ids


def developer():
    async def predicate(ctx: Interaction):
        return ctx.user.id in developer_ids
    return check(predicate)