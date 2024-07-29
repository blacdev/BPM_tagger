"""
A simple job to extract the tempo of a song using Mixxx DJ software.
Then we get the bpm, key from mixxx's database.

The mixxx database is a sqlite database located at:
"C:/Users/{username}/AppData/Local/Mixxx/mixxxdb.sqlite"

The tables we are interested in is "Library" and "Track".

The "Library" table contains:
- id
- key
- bpm
- artist
- title
- album
- genre
- comment

 Algorithm to extract to use:

- from track_locations' Table, fetch first 20 rows
- for each row, pick location column
- split the location column text to get the song title from the path and split by "/" to get the artist name
- use song title and artist name  to find the song in Library table
- if song is found and response instance is a list or tuple
  Loop:
    - loop through the list to see if all are the same
  Tuple:
    - if tuple:
- get the bpm and key from the response
- use the location column data(file path) to extract the metadata of the song
- update metadata of the song with the bpm and key
- save the metadata back to the file.
"""


import argparse
import os
import platform
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from typing import Generator, Dict
from sqlalchemy import create_engine, Integer, String, Column, ForeignKey, Float
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base, relationship
from contextlib import contextmanager
import taglib
import threading

# Global variable to manage thread termination
terminate_thread = False

def get_db_engine(url: str) -> Engine:
    return create_engine(url, connect_args={"check_same_thread": False})

def is_wsl() -> bool:
    return 'microsoft' in platform.uname().release.lower()

def process_path(path: str) -> str:
    if is_wsl():
        path = path.replace("\\", "/").replace("C:", "/mnt/c")
    return path if os.path.isfile(path) else None

@contextmanager
def get_db() -> Generator[Session, None, None]:
    database: Session = SessionLocal()
    try:
        yield database
    finally:
        database.close()

Base = declarative_base()

class Track_Locations(Base):
    __tablename__ = "track_locations"
    id = Column(Integer, primary_key=True)
    location = Column(String, unique=True)
    filename = Column(String)
    directory = Column(String)

    library = relationship("Library", back_populates="track_locations")

class Library(Base):
    __tablename__ = "library"
    id = Column(Integer, primary_key=True)
    artist = Column(String)
    album = Column(String)
    genre = Column(String)
    title = Column(String)
    year = Column(String)
    location = Column(Integer, ForeignKey("track_locations.id"))
    key = Column(String)
    bpm = Column(Float)

    track_locations = relationship("Track_Locations", back_populates="library")

def get_metadata(file_path: str) -> tuple:
    try:
        with taglib.File(file_path) as f:
            artist = next(iter(f.tags.get('ARTIST', [])), None)
            title = next(iter(f.tags.get('TITLE', [])), None)
            album = next(iter(f.tags.get('ALBUMARTIST', [])), None)
            bpm = next(iter(f.tags.get('BPM', [])), None)
            key = next(iter(f.tags.get('KEY', [])), None)
            metadata = f.tags

        return artist, title, bpm, key, metadata
    except Exception as e:
        return None, None, None, None, {}

def tag_music_file(file_path: str, metadata: Dict) -> None:
    try:
        with taglib.File(file_path, save_on_exit=True) as f:
            for key, value in metadata.items():
                f.tags[key] = value
            f.save()
    except Exception as e:
        print("Error tagging file:", e)

def main(database_path: str, progress_var: tk.DoubleVar = None, progress_label: tk.Label = None):
    global terminate_thread
    terminate_thread = False

    processed_path = process_path(database_path)
    if not processed_path:
        if progress_label:
            progress_label.config(text="Invalid database path.")
        return

    db_engine = get_db_engine(f"sqlite:///{processed_path}")
    global SessionLocal
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    with get_db() as db:
        count = 0
        total = db.query(Library).count()
        offset = 0
        limit = 20

        while count < total and not terminate_thread:
            data = db.query(Library).limit(limit).offset(offset).all()
            for i in data:
                file_path = process_path(i.track_locations.location)
                if not file_path:
                    continue

                _, _, _, _, metadata = get_metadata(file_path)
                if metadata:
                    metadata["BPM"] = [str(round(float(i.bpm), 2))]
                    metadata["KEY"] = [i.key]
                    metadata["ARTIST"] = [i.artist]
                    metadata["TITLE"] = [i.title]
                    metadata["ALBUMARTIST"] = [i.artist]
                    metadata['GENRE'] = [i.genre]
                    metadata['ALBUM'] = [i.album]
                    metadata['YEAR'] = [i.year]
                    tag_music_file(file_path, metadata)
            offset += limit
            count = offset
            if progress_var:
                progress_var.set((count / total) * 100)
                progress_label.config(text=f"Processing... {count} of {total}")

        if progress_label:
            progress_label.config(text="Done" if not terminate_thread else "Process terminated")

def choose_directory():
    root = tk.Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory(title="Select Mixxx Database Directory")
    if folder_path:
        db_path = os.path.join(folder_path, "mixxxdb.sqlite")
        return db_path
    return None

def run_with_gui():
    def start_processing():
        db_path = choose_directory()
        if db_path:
            progress_var.set(0)
            progress_label.config(text="Starting...")
            threading.Thread(target=main, args=(db_path, progress_var, progress_label)).start()

    def stop_processing():
        global terminate_thread
        terminate_thread = True

    root = tk.Tk()
    root.title("Mixxx Database Processor")

    frame = ttk.Frame(root, padding=10)
    frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(frame, variable=progress_var, maximum=100)
    progress_bar.grid(row=0, column=0, pady=10, padx=10, sticky=(tk.W, tk.E))

    progress_label = tk.Label(frame, text="Select the Mixxx database directory to start")
    progress_label.grid(row=1, column=0, pady=5, padx=10, sticky=(tk.W, tk.E))

    start_button = ttk.Button(frame, text="Choose Directory and Start", command=start_processing)
    start_button.grid(row=2, column=0, pady=10, padx=10)

    stop_button = ttk.Button(frame, text="Stop", command=stop_processing)
    stop_button.grid(row=3, column=0, pady=10, padx=10)

    root.mainloop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Mixxx DB path.")
    parser.add_argument("database_path", type=str, nargs='?', help="The path to the Mixxx DB file")
    args = parser.parse_args()

    if args.database_path:
        main(args.database_path)
    else:
        run_with_gui()
