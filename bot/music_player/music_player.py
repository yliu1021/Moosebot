import asyncio
import os.path
from collections import deque
import logging
import typing
import random

import discord
from bot.music_player import Song

from . import youtube

logger = logging.getLogger(__name__)

_FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


async def _get_song(query: str) -> Song:
    video_id = await youtube.get_youtube_video_id(query)
    song = await youtube.get_song_from_youtube_id(video_id)
    return song


def _format_song(song: Song) -> str:
    return f"**{song.title}**\nhttps://www.youtube.com/results?search_query={song.video_id}"


class MusicPlayer:
    def __init__(self, client: discord.Client):
        self.client = client
        self.text_channel: typing.Optional[discord.TextChannel] = None
        self.voice_client: typing.Optional[discord.VoiceClient] = None
        self.song_queue: deque[Song] = deque()
        self.current_song: typing.Optional[Song] = None
        self.song_playback_task: typing.Optional[asyncio.Task] = None

    async def received_message(self, message: discord.Message):
        cmd, *args = message.content.split(" ")
        fn = {
            "!play": self.play,
            "!resume": self.resume,
            "!pause": self.pause,
            "!stop": self.stop,
            "!skip": self.skip,
            "!shuffle": self.shuffle,
            "!next": self.queue_next,
            "!queue": self.show_queue,
            "!nowplaying": self.now_playing,
        }
        if cmd not in fn:
            return
        if not isinstance(message.channel, discord.TextChannel):
            return
        self.text_channel = message.channel
        if not message.author.voice:
            await self.text_channel.send("You need to be in a voice channel")
            return
        if not message.guild.voice_client:
            logging.warning("Unable to get server %s voice client", message.guild)
            await message.author.voice.channel.connect()
            self.song_playback_task = asyncio.Task(self._music_playback_task())
        self.voice_client = message.guild.voice_client
        await fn[cmd](" ".join(args))

    async def play(self, query: str):
        """
        Automatically queues up the next song and starts the music task if it hasn't started yet
        :param query: The song to queue up
        :return:
        """
        song = await _get_song(query)
        logger.info("Adding song %s to end of queue", song)
        self.song_queue.append(song)
        await self.text_channel.send(f"Added song\n{_format_song(song)}")

    async def resume(self, *args):
        """
        Resumes playback
        :return:
        """
        self.voice_client.resume()

    async def pause(self, *args):
        """
        Pauses playback but leaves queue intact
        :return:
        """
        self.voice_client.pause()

    async def stop(self, *args):
        """
        Stops playback and clears the queue
        :return:
        """
        self.song_queue.clear()
        self.voice_client.stop()

    async def skip(self, *args):
        """
        Skips the current song
        :return:
        """
        self.voice_client.stop()

    async def shuffle(self, *args):
        """
        Shuffles the songs in queue
        :return:
        """
        songs = list(self.song_queue)
        random.shuffle(songs)
        self.song_queue = deque(songs)

    async def queue_next(self, query: str):
        """
        Adds a new song at the front of the queue (not at the end)
        :param query: the song to play next
        :return:
        """
        song = await _get_song(query)
        logger.info("Adding song %s to front of queue", song)
        self.song_queue.appendleft(song)
        await self.text_channel.send(f"Playing next\n{_format_song(song)}")

    async def show_queue(self, *args):
        """
        Shows the current queue
        :param args:
        :return:
        """
        await self.text_channel.send(f"Queue: {len(self.song_queue)} songs")
        for song in self.song_queue:
            await self.text_channel.send(_format_song(song))

    async def now_playing(self, *args):
        """
        Shows the current song
        :return:
        """
        if self.current_song:
            await self.text_channel.send(f"Now playing: {_format_song(self.current_song)}")
        else:
            await self.text_channel.send("Nothing playing")

    # PRIVATE METHODS

    async def _music_playback_task(self):
        while True:
            while len(self.song_queue) == 0:
                await asyncio.sleep(0.5)
            song = self.song_queue.popleft()
            await self._play_song(song)

    async def _play_song(self, song: Song):
        song_finished = asyncio.Event()
        loop = asyncio.get_event_loop()
        self.current_song = song
        logging.info("Playing song: %s", self.current_song)

        def song_finished_cb(err):
            if err:
                logger.warning("Song finished with error: %s", err)
            loop.call_soon_threadsafe(song_finished.set)
            self.current_song = None

        self.voice_client.play(
            discord.FFmpegPCMAudio(
                song.url, executable=os.path.join("bin", "ffmpeg"), **_FFMPEG_OPTIONS
            ),
            after=song_finished_cb
        )
        await song_finished.wait()
