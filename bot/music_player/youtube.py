import urllib.parse
import urllib.request
import re

import youtube_dl

from .song import Song


ytdl = youtube_dl.YoutubeDL({"format": "bestaudio"})
FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


async def get_youtube_video_id(query: str) -> str:
    """
    Queries YouTube for a video id
    :param query: a human-made query
    :return: a video id
    """
    query = urllib.parse.quote(query)
    html = urllib.request.urlopen(
        "https://www.youtube.com/results?search_query=" + query
    )
    video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
    return video_ids


async def get_song_from_youtube_id(video_id: str) -> Song:
    data = ytdl.extract_info(video_id, download=False)
    if "entries" in data:
        video_data = data["entries"][0]
    else:
        video_data = data
    return Song(url=video_data["url"], video_id=video_data["id"], title=video_data["title"])
