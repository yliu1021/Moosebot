import logging

import discord

from .chat_bot.chat_bot import ChatBot
from .music_player.music_player import MusicPlayer

logger = logging.getLogger(__name__)


class MooseBot(discord.Client):
    def __init__(self):
        super().__init__()
        self.music_player = MusicPlayer(self)
        self.chat_bot = ChatBot(self)

    async def on_ready(self):
        logger.info("Logged in as %s", self.user)

    async def on_message(self, message: discord.Message):
        logger.info("Received message: %s", message)
        if message.author == self.user:
            logger.info("Ignoring message from self")
            return
        if "bot-channel" in message.channel.name:
            await self.music_player.received_message(message)
        elif "general" in message.channel.name:
            await self.chat_bot.receive_message(message)
