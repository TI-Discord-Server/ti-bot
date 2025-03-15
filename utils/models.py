import json
import logging
import os
import re
import sys
import _string

from difflib import get_close_matches
from enum import IntEnum
from logging import FileHandler, StreamHandler, Handler
from logging.handlers import RotatingFileHandler
from string import Formatter
from typing import Dict, Optional

import discord
from discord.ext import commands

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

