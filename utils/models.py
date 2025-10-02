import _string
from string import Formatter


class DummyMessage:
    """
    A class mimicking the original :class:discord.Message
    where all functions that require an actual message to exist
    is replaced with a dummy function
    """

    def __init__(self, message):
        if message:
            message.attachments = []
        self._message = message

    def __getattr__(self, name: str):
        return getattr(self._message, name)

    def __bool__(self):
        return bool(self._message)

    async def delete(self, *, delay=None):
        return

    async def edit(self, **fields):
        return

    async def add_reaction(self, emoji):
        return

    async def remove_reaction(self, emoji):
        return

    async def clear_reaction(self, emoji):
        return

    async def clear_reactions(self):
        return

    async def pin(self, *, reason=None):
        return

    async def unpin(self, *, reason=None):
        return

    async def publish(self):
        return

    async def ack(self):
        return


class SafeFormatter(Formatter):
    def get_field(self, field_name, args, kwargs):
        first, rest = _string.formatter_field_name_split(field_name)

        try:
            obj = self.get_value(first, args, kwargs)
        except (IndexError, KeyError):
            return "<Invalid>", first

        # loop through the rest of the field_name, doing
        #  getattr or getitem as needed
        # stops when reaches the depth of 2 or starts with _.
        try:
            for n, (is_attr, i) in enumerate(rest):
                if n >= 2:
                    break
                if is_attr:
                    if str(i).startswith("_"):
                        break
                    obj = getattr(obj, i)
                else:
                    obj = obj[i]
            else:
                return obj, first
        except (IndexError, KeyError):
            pass
        return "<Invalid>", first
