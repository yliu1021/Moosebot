import asyncio
import logging
import os
import random
import re
import urllib.parse
import urllib.request
from collections import deque
from typing import Optional

import discord
import dotenv
import youtube_dl
from discord.ext import commands

logger = logging.getLogger(__name__)

client = discord.Client()
bot = commands.Bot(command_prefix="!")

ytdl = youtube_dl.YoutubeDL({"format": "bestaudio"})
FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

music_queue = deque()
music_queue_task: Optional[asyncio.Task] = None


async def play_music_queue(voice_client):
    logger.info("Starting music queue")
    lock = asyncio.Lock()
    loop = asyncio.get_event_loop()
    while True:
        while len(music_queue) == 0:
            await asyncio.sleep(0.5)
        video_id = music_queue.popleft()
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(video_id, download=False)
        )
        if "entries" in data:
            video_data = data["entries"][0]
        else:
            video_data = data
        video_url = video_data["url"]
        await lock.acquire()
        voice_client.play(
            discord.FFmpegPCMAudio(
                video_url, executable=".\\bin\\ffmpeg", **FFMPEG_OPTIONS
            ),
            after=lambda e: loop.call_soon_threadsafe(lock.release),
        )
        await lock.acquire()
        lock.release()


def get_youtube_video_id(search):
    search = urllib.parse.quote(search)
    logger.info("Searching: %s", search)
    html = urllib.request.urlopen(
        "https://www.youtube.com/results?search_query=" + search
    )
    video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
    return video_ids[0]


@bot.command(name="play")
async def play(ctx, *, search):
    await join(ctx)
    server = ctx.message.guild
    voice_client = server.voice_client
    global music_queue
    global music_queue_task
    if music_queue_task is None:
        music_queue = deque()
        music_queue_task = asyncio.create_task(play_music_queue(voice_client))
    video_id = get_youtube_video_id(search)
    await ctx.send(f"Adding to queue:\nhttps://www.youtube.com/watch?v={video_id}")
    music_queue.append(video_id)


@bot.command(name="shuffle")
async def shuffle(ctx):
    global music_queue
    video_ids = list(music_queue)
    random.shuffle(video_ids)
    music_queue = deque(video_ids)
    await ctx.send("Shuffling")


@bot.command(name="next")
async def insert_next(ctx, *, search):
    video_id = get_youtube_video_id(search)
    music_queue.appendleft(video_id)
    await ctx.send(f"Playing next:\nhttps://www.youtube.com/watch?v={video_id}")


@bot.command(name="queue")
async def queue(ctx):
    global music_queue
    video_ids = list(music_queue)
    msg = [f"https://www.youtube.com/watch?v={video_id}" for video_id in video_ids]
    await ctx.send("\n".join(msg))


@bot.command(name="join")
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send(
            "{} is not connected to a voice channel".format(ctx.message.author.name)
        )
        return
    else:
        channel = ctx.message.author.voice.channel
    voice_client = ctx.message.guild.voice_client
    if voice_client is None or not voice_client.is_connected():
        await channel.connect()


@bot.command(name="pause")
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.pause()
    else:
        await ctx.send("The bot is not playing anything at the moment.")


@bot.command(name="resume")
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        voice_client.resume()
    else:
        await ctx.send(
            "The bot was not playing anything before this. Use play_song command"
        )


@bot.command(name="stop")
async def stop(ctx):
    global music_queue
    music_queue.clear()
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
    else:
        await ctx.send("The bot is not playing anything at the moment.")


@bot.command(name="skip")
async def skip(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.stop()
    else:
        await ctx.send("The bot is not playing anything at the moment.")


@bot.command(name="leave")
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
    else:
        await ctx.send("The bot is not connected to a voice channel.")


@bot.event
async def on_ready():
    logging.info("Running")
    for guild in bot.guilds:
        logging.info("Active in %s\n\tMember count: %s", guild.name, guild.member_count)


if __name__ == "__main__":
    dotenv.load_dotenv()
    logging.basicConfig(level=logging.INFO)
    bot.run(os.getenv("DISCORD_TOKEN"))
