from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field, HttpUrl
from bson import ObjectId
from datetime import datetime

class SongBase(BaseModel):
    url: HttpUrl
    title: str
    artist: str
    album: Optional[str] = None
    artwork: Optional[str] = None
    duration: Optional[float] = None
    last_modify: Optional[datetime] = None

class Song(SongBase):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    liked_bool: Optional[str] = None
    playlists: List[str] = []

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class PlaylistBase(BaseModel):
    name: str

class Playlist(PlaylistBase):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    songs: List[str] = []

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class LikedBase(BaseModel):
    song_id: str

class Liked(LikedBase):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class PlaylistRead(BaseModel):
    id: str
    name: str

    class Config:
        json_encoders = {ObjectId: str}

class LikedRead(BaseModel):
    id: str
    song_id: str

    class Config:
        json_encoders = {ObjectId: str}

class SongRead(SongBase):
    id: str

    class Config:
        json_encoders = {ObjectId: str}

class SongReadWithLike(SongRead):
    liked_bool: Optional[LikedRead] = None

class SongReadWithPlaylists(SongRead):
    playlists: List[PlaylistRead] = []

class PlaylistReadWithSongs(PlaylistRead):
    songs: List[SongReadWithLike] = []

class SongUpdate(BaseModel):
    url: Optional[HttpUrl] = None
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    artwork: Optional[str] = None
    duration: Optional[float] = None
