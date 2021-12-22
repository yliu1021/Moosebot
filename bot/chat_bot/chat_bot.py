import asyncio
import logging
import os
import random

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


async def _get_gamers(message: discord.Message):
    channel: discord.TextChannel = message.channel
    author: discord.User = message.author
    author_uid = author.id
    if author_uid in squad_1:
        message = f"{_tag_users(squad_1 - {author_uid})} someone say valorant??"
        await channel.send(message)


async def _send_score_deduction(message: discord.Message, score_change: int):
    """
    Sends a message to deduct score
    :param message: the original message
    :param score_change: score change (should be negative)
    :return:
    """
    if score_change > 0:
        raise ValueError("Score change must be negative")
    msg = (
        "ATTENTION CITIZEN! 市民请注意! This is the Central Intelligentsia of the Banana Haven "
        f"Communist Party. () 您的 Internet 浏览器历史记录和活动引起了我们的注意。 因此，您的个人资料中的 {score_change} "
        f"( {score_change} Social Credits) 个社会积分将打折。 DO NOT DO THIS AGAIN! 不要再这样做! If you not "
        "hesitate, more Social Credits ( - Social Credits )will be subtracted from your "
        "profile, resulting in the subtraction of ration supplies. (由人民供应部重新分配 CCP) "
        "You'll also be sent into a re-education camp in the Xinjiang Uighur Autonomous Zone. "
        "如果您毫不犹豫，更多的社会信用将从您的个人资料中打折，从而导致口粮供应减少。 "
        "您还将被送到新疆维吾尔自治区的再教育营。 为党争光! Glory to Banana Haven!!!"
    )
    channel: discord.TextChannel = message.channel
    await channel.send(msg)


async def _send_score_increase(message: discord.Message, score_change: int):
    """
    Sends a message to increase score
    :param message: the original message
    :param score_change: score change (should be positive)
    :return:
    """
    if score_change < 0:
        raise ValueError("Score change must be positive")
    msgs = [
        f"中华人民共和国寄语] Great work, Citizen! Your social credit score has increased by "
        f"[{score_change}] Integers. Keep up the good work! [ 中华人民共和国寄语]",
        f"[ 中华人民共和国寄语] Great work, Citizen! Your social credit score has increased by "
        f"[{score_change}] Integers. You can now have priority transport and can now get into "
        f"prestigious colleges! Keep up the good work! [ 中华人民共和国寄语]",
    ]
    channel: discord.TextChannel = message.channel
    await channel.send(random.choice(msgs))


async def _process_score_change(message: discord.Message, net_confidence: float):
    threshold = 0.5
    if abs(net_confidence) < threshold:
        return
    if net_confidence < 0:
        net_confidence += threshold
    else:
        net_confidence -= threshold
    net_confidence /= 1 - threshold
    score_change = int(round(net_confidence * 50))
    if score_change < 0:
        await _send_score_deduction(message, score_change=score_change)
    if score_change > 0:
        await _send_score_increase(message, score_change=score_change)


class ChatBot:
    def __init__(self, client: discord.Client):
        dotenv.load_dotenv()
        self.client = client
        self.wit = wit.Wit(os.getenv("WIT_TOKEN"))

    async def receive_message(self, message: discord.Message):
        loop = asyncio.get_event_loop()
        try:
            wit_resp = await loop.run_in_executor(None, self.wit.message, message.content)
        except wit.wit.WitError:
            logger.exception("Wit error")
            return
        logger.info(f"Wit response: {wit_resp}")
        threshold = 0.6
        for intent in wit_resp["intents"]:
            if intent["confidence"] < threshold:
                continue
            intent_name = intent["name"]
            if intent_name == "get_gamers":
                await _get_gamers(message)
            if intent_name == "communist_score_change":
                net_confidence = 0
                for score in wit_resp["traits"].get("communist_score", []):
                    if score["value"] == "increase":
                        net_confidence += score["confidence"]
                    elif score["value"] == "decrease":
                        net_confidence -= score["confidence"]
                await _process_score_change(message, net_confidence)
