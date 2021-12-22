import asyncio
import logging
import os

import discord
import dotenv
import wit

logger = logging.getLogger(__name__)

squad_1 = {
    191383271500808192,  # Yuhan
    154415399503527936,  # Wei
    272197851960967170,  # Vina
    193192680962916362,  # Michael
    190256033770373131,  # Jeffrey
}


def _tag_users(users: set[int]) -> str:
    return " ".join(f"<@{uid}>" for uid in users)


class ChatBot:
    def __init__(self, client: discord.Client):
        dotenv.load_dotenv()
        self.client = client
        self.wit = wit.Wit(os.getenv("WIT_TOKEN"))

    async def receive_message(self, message: discord.Message):
        loop = asyncio.get_event_loop()
        wit_resp = await loop.run_in_executor(None, self.wit.message, message.content)
        logger.info(f"Wit response: {wit_resp}")
        for intent in wit_resp["intents"]:
            if intent["name"] == "get_gamers":
                await self.get_gamers(message)

    async def get_gamers(self, message):
        channel: discord.TextChannel = message.channel
        author: discord.User = message.author
        author_uid = author.id
        if author_uid in squad_1:
            message = f"{_tag_users(squad_1 - {author_uid})} someone say valorant??"
            await channel.send(message)
