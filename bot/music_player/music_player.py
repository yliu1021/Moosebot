import asyncio
import logging
import os.path
import random
import typing
from collections import deque
import urllib.parse
import urllib.request
import re

import discord
import youtube_dl

from bot import analytics
from bot.music_player import Song

logger = logging.getLogger(__name__)

_ytdl = youtube_dl.YoutubeDL({"format": "bestaudio"})
_FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}
_song_log_fields = [
    "id", "title", "duration", "view_count", "like_count", "track", "artist", "album", "creator"
]


def _format_song(song: Song) -> str:
    return f"**{song.title}**\n<https://www.youtube.com/watch?v={song.video_id}>"


class MusicPlayer:
    def __init__(self, client: discord.Client):
        self.client = client
        self.text_channel: typing.Optional[discord.TextChannel] = None
        self.voice_client: typing.Optional[discord.VoiceClient] = None
        self.song_queue: deque[Song] = deque()
        self.current_song: typing.Optional[Song] = None
        self.song_playback_task: typing.Optional[asyncio.Task] = None
        self.analytics_table = analytics.get_table("music_player")

    async def received_message(self, message: discord.Message):
        if not isinstance(message.channel, discord.TextChannel):
            return
        self.text_channel = message.channel
        cmd, *args = message.content.split(" ")
        fn = {
            "!play": (self.play, "!play <song name>: adds a song to queue"),
            "!resume": (self.resume, "resumes playback"),
            "!pause": (self.pause, "pauses playback"),
            "!stop": (self.stop, "stops playback and clears queue"),
            "!skip": (self.skip, "skips the current song"),
            "!shuffle": (self.shuffle, "shuffles the queue"),
            "!next": (
                self.queue_next,
                "!next <song name>: adds a song to the front of the queue",
            ),
            "!queue": (self.show_queue, "shows the queue"),
            "!song": (self.now_playing, "shows the current song playing"),
            "!leave": (self.leave, "leaves the server"),
        }
        if cmd == "!help":
            with self.text_channel.typing():
                await self.text_channel.send("**Moosebot Music Commands**")
                await self.text_channel.send(
                    "\n".join([f"**{key}** - *{val[1]}*" for key, val in fn.items()])
                )
            return
        if cmd not in fn:
            return
        if not message.author.voice:
            await self.text_channel.send("You need to be in a voice channel")
            return
        guild_voice_client: typing.Optional[
            discord.VoiceClient
        ] = message.guild.voice_client
        if not guild_voice_client:
            await message.author.voice.channel.connect()
            self.song_playback_task = asyncio.Task(self._music_playback_task())
        elif guild_voice_client.channel != message.author.voice.channel:
            await self.text_channel.send("You're not in the same voice channel")
            return
        self.voice_client = message.guild.voice_client
        await fn[cmd][0](" ".join(args), message.author)

    async def play(self, query: str, requester: discord.User):
        """
        Automatically queues up the next song and starts the music task if it hasn't started yet
        :param query: The song to queue up
        :param requester: Discord user that made the request
        :return:
        """
        if len(query) == 0:
            await self.text_channel.send("!play <song name>")
            return
        song = await self._get_song(query, requester)
        if song is None:
            await self.text_channel.send("Song not found")
            return
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

    async def queue_next(self, query: str, requester: discord.User):
        """
        Adds a new song at the front of the queue (not at the end)
        :param query: the song to play next
        :param requester: Discord user that made the request
        :return:
        """
        song = await self._get_song(query, requester)
        logger.info("Adding song %s to front of queue", song)
        self.song_queue.appendleft(song)
        await self.text_channel.send(f"Playing next\n{_format_song(song)}")

    async def show_queue(self, *args):
        """
        Shows the current queue
        :param args:
        :return:
        """
        with self.text_channel.typing():
            await self.text_channel.send(f"Queue: {len(self.song_queue)} songs")
            for song in self.song_queue:
                await self.text_channel.send(_format_song(song))

    async def now_playing(self, *args):
        """
        Shows the current song
        :return:
        """
        if self.current_song:
            await self.text_channel.send(
                f"Now playing: {_format_song(self.current_song)}"
            )
        else:
            await self.text_channel.send("Nothing playing")

    async def leave(self, *args):
        """
        Leaves the current channel
        :return:
        """
        await self.voice_client.disconnect()

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
            else:
                logger.info("Song finished")
            loop.call_soon_threadsafe(song_finished.set)
            self.current_song = None

        self.voice_client.play(
            discord.FFmpegPCMAudio(
                song.url, executable=os.path.join("bin", "ffmpeg"), **_FFMPEG_OPTIONS
            ),
            after=song_finished_cb,
        )
        await song_finished.wait()

    async def _get_song(
            self, query: str, requester: discord.User
    ) -> typing.Optional[Song]:
        query = urllib.parse.quote(query)
        html = urllib.request.urlopen(
            "https://www.youtube.com/results?search_query=" + query
        )
        video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
        if len(video_ids) == 0:
            return None
        video_id = video_ids[0]
        data = _ytdl.extract_info(video_id, download=False)
        if "entries" in data:
            video_data = data["entries"][0]
        else:
            video_data = data
        log_data = {}
        for log_field in _song_log_fields:
            log_data[log_field] = video_data.get(log_field)
        log_data["discord_requester"] = f"{requester.name}#{requester.discriminator}"
        self.analytics_table.log(log_data)
        return Song(
            url=video_data["url"], video_id=video_data["id"], title=video_data["title"]
        )
