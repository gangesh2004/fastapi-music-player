import datetime
import os
from typing import Dict, List

import eyed3  # type: ignore
from fastapi import FastAPI, HTTPException, status, UploadFile, File, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi_utils.tasks import repeat_every
from motor.motor_asyncio import AsyncIOMotorClient  # MongoDB client
from bson import ObjectId
import shutil

# Import models and helper functions
from app.models import (
    Song,
    SongUpdate,
    Playlist,
    Liked,
    PlaylistBase,
    PlaylistReadWithSongs,
    SongRead,
    SongReadWithLike,
)

# Backend initialization
app = FastAPI()
def get_last_modify(file_path: str) -> datetime.datetime:
    """
    Get the last modification time of a file.
    
    Args:
    file_path (str): The path to the file.
    
    Returns:
    datetime.datetime: The last modification time of the file.
    """
    return datetime.datetime.fromtimestamp(os.path.getmtime(file_path))

# Define the folder paths
music_folder_url = "../songs"  # folder containing all songs
cover_folder_url = "../covers"  # folder containing all songs
  # Replace with the actual path to your cover folder

# MongoDB connection
MONGO_DETAILS = "mongodb+srv://gangeshk:iUK8GV65TygL3BHC@cluster0.ohd32.mongodb.net/"  # Replace with your MongoDB URI
client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.music_database  # Specify your database name
songs_collection = database.get_collection("songs")
playlists_collection = database.get_collection("playlists")
liked_collection = database.get_collection("liked")

async def get_song_by_id(song_id: str):
    return await songs_collection.find_one({"_id": ObjectId(song_id)})

async def create_song(song_data: Dict):
    result = await songs_collection.insert_one(song_data)
    return await get_song_by_id(result.inserted_id)

async def update_song(song_id: str, update_data: Dict):
    await songs_collection.update_one({"_id": ObjectId(song_id)}, {"$set": update_data})
    return await get_song_by_id(song_id)

async def delete_song(song_id: str):
    await songs_collection.delete_one({"_id": ObjectId(song_id)})

async def get_playlist_by_id(playlist_id: str):
    return await playlists_collection.find_one({"_id": ObjectId(playlist_id)})

async def create_playlist(playlist_data: Dict):
    result = await playlists_collection.insert_one(playlist_data)
    return await get_playlist_by_id(result.inserted_id)

async def update_playlist(playlist_id: str, update_data: Dict):
    await playlists_collection.update_one({"_id": ObjectId(playlist_id)}, {"$set": update_data})
    return await get_playlist_by_id(playlist_id)

async def delete_playlist(playlist_id: str):
    await playlists_collection.delete_one({"_id": ObjectId(playlist_id)})

async def get_all_songs():
    return await songs_collection.find().to_list(None)

async def get_all_playlists():
    return await playlists_collection.find().to_list(None)


@app.get("/songs/{song_id}/stream", response_class=StreamingResponse)
async def stream_song(song_id: str) -> StreamingResponse:
    song = await get_song_by_id(song_id)
    if not song:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")

    def iterfile():
        with open(song["url"], mode="rb") as file_like:
            yield from file_like

    return StreamingResponse(iterfile(), media_type="audio/mp3")
@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    max_upload_size = 10 * 1024 * 1024  # 10 MB limit
    if request.headers.get("content-length"):
        content_length = int(request.headers.get("content-length"))
        if content_length > max_upload_size:
            raise HTTPException(status_code=413, detail="Upload size exceeds the limit")
    return await call_next(request)

@app.post("/songs/upload")
async def upload_song(file: UploadFile = File(...)):
    # Define the path where the file will be saved
    songs_dir = "../songs"
    file_location = os.path.join(songs_dir, file.filename)
    
    # Create the directory if it doesn't exist
    os.makedirs(songs_dir, exist_ok=True)

    with open(file_location, "wb") as buffer:
        buffer.write(await file.read())

    return {"info": f"file '{file.filename}' saved at '{file_location}'"}

# @app.post("/songs/upload", response_model=SongRead)
# async def upload_song(file: UploadFile = File(...)) -> SongRead:
#     # Save the uploaded file to the music folder
#     file_location = os.path.join(music_folder_url, file.filename)
#     with open(file_location, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)

#     # Load the song metadata using eyed3
#     audiofile = eyed3.load(file_location)
#     if not audiofile or not audiofile.tag:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is not a valid MP3 file")

#     song_title = audiofile.tag.title
#     song_artist = audiofile.tag.artist

#     # Check if the song already exists in the database
#     existing_song = await songs_collection.find_one({"title": song_title, "artist": song_artist})
#     if existing_song:
#         raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Song already exists")

#     # Process artwork (optional)
#     artwork_exists = False
#     artwork_path = str(os.path.join(cover_folder_url, song_title)) + ".jpg"
#     for image in audiofile.tag.images:
#         with open(artwork_path, "wb") as image_file:
#             image_file.write(image.image_data)
#         artwork_exists = True

#     # Prepare the song data
#     new_song_data = {
#         "url": file_location,
#         "title": song_title,
#         "artist": song_artist,
#         "artwork": artwork_path if artwork_exists else None,
#         "last_modify": get_last_modify(file_location),
#         "duration": audiofile.info.time_secs,
#     }

#     # Save the song data to the database
#     new_song = await create_song(new_song_data)
#     return SongRead(**new_song)

@app.post("/songs/{song_id}/like", response_model=Dict)
async def like(song_id: str) -> dict:
    song = await get_song_by_id(song_id)
    if not song:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    new_like = {"song_id": song_id}
    await liked_collection.insert_one(new_like)
    await update_song(song_id, {"liked_bool": True})
    return {"Liked song with id: ": song_id}

@app.delete("/songs/{song_id}/unlike", response_model=Dict)
async def unlike(song_id: str) -> dict:
    liked = await liked_collection.find_one({"song_id": song_id})
    if not liked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Like entry not found")
    await liked_collection.delete_one({"_id": liked["_id"]})
    await update_song(song_id, {"liked_bool": None})
    return {"Unliked song with id: ": song_id}

@app.post("/songs/playlists", response_model=PlaylistReadWithSongs, status_code=status.HTTP_201_CREATED)
async def create_playlist(playlist: PlaylistBase) -> Playlist:
    new_playlist = playlist.dict()
    result = await playlists_collection.insert_one(new_playlist)
    created_playlist = await get_playlist_by_id(result.inserted_id)
    return created_playlist

@app.delete("/songs/delete_playlist/{playlist_id}", response_model=Dict)
async def delete_playlist(playlist_id: str) -> dict:
    playlist = await get_playlist_by_id(playlist_id)
    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")
    await delete_playlist(playlist_id)
    return {"Deleted playlist with ID: ": playlist_id}

@app.patch("/songs/add_song/{playlist_id}/{song_id}", response_model=SongReadWithLike)
async def add_song_to_playlist(song_id: str, playlist_id: str) -> Song:
    playlist = await get_playlist_by_id(playlist_id)
    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")
    song = await get_song_by_id(song_id)
    if not song:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    playlist["songs"].append(song_id)
    await update_playlist(playlist_id, playlist)
    return song

@app.patch("/songs/remove_song/{playlist_id}/{song_id}", response_model=Dict)
async def delete_song_from_playlist(song_id: str, playlist_id: str) -> dict:
    playlist = await get_playlist_by_id(playlist_id)
    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")
    song = await get_song_by_id(song_id)
    if not song:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    playlist["songs"].remove(song_id)
    await update_playlist(playlist_id, playlist)
    return {"Deleted Song with ID: ": song_id, "From Playlist with ID: ": playlist_id}

@app.get("/songs", response_model=List[SongReadWithLike])
async def get_all_songs() -> List[Song]:
    songs = await get_all_songs()
    return songs

@app.get("/songs/playlists", response_model=List[PlaylistReadWithSongs])
async def get_all_playlist() -> List[Playlist]:
    playlists = await get_all_playlists()
    return playlists

@repeat_every(seconds=30)
async def scan_songs():
    all_songs = await get_all_songs()
    songs_on_disk = []

    for song in os.listdir(music_folder_url):
        if song.endswith(".mp3"):
            joined_path = os.path.join(music_folder_url, song)
            audiofile = eyed3.load(joined_path)

            db_song = None
            for s in all_songs:
                if s["title"] == audiofile.tag.title and s["artist"] == audiofile.tag.artist:
                    db_song = s
                    break

            if db_song:
                songs_on_disk.append(str(db_song["_id"]))
                continue

            song_title = audiofile.tag.title
            artwork_path = str(os.path.join(cover_folder_url, song_title)) + ".jpg"
            artwork_exists = False
            for image in audiofile.tag.images:
                with open(f"../covers/{song_title}.jpg", "wb") as image_file:
                    image_file.write(image.image_data)
                artwork_exists = True

            new_song_data = {
                "url": joined_path,
                "title": song_title,
                "artist": audiofile.tag.artist,
                "artwork": artwork_path if artwork_exists else None,
                "last_modify": get_last_modify(joined_path),
                "duration": audiofile.info.time_secs,
            }
            new_song = await create_song(new_song_data)
            songs_on_disk.append(str(new_song["_id"]))

    songs_on_disk_set = set(songs_on_disk)

    for db_song in all_songs:
        if str(db_song["_id"]) not in songs_on_disk_set:
            await delete_song(str(db_song["_id"]))
