import logging

import discord

from .music_player.music_player import MusicPlayer

logger = logging.getLogger(__name__)


class MooseBot(discord.Client):
    def __init__(self):
        super().__init__()
        self.music_player = MusicPlayer(self)

    async def on_ready(self):
        logger.info("Logged in as %s", self.user)

    async def on_message(self, message):
        logger.info("Received message: %s", message)
        await self.music_player.received_message(message)
