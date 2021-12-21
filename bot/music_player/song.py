from dataclasses import dataclass


@dataclass(frozen=True)
class Song:
    url: str  # URL to stream from
    video_id: str  # YouTube video id
    title: str  # what the user searched to get this song
