import subprocess
import ffmpeg
import aubio
import numpy as np
import os
import taglib
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict
import tempfile
import logging
import threading

possible_ffmpeg_paths = ['ffmpeg', 'C:\\ffmpeg\\bin\\ffmpeg.exe']

for path in possible_ffmpeg_paths:
    if os.path.isfile(path):
        ffmpeg_path = path
        break

class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, msg + '\n')
        self.text_widget.config(state=tk.DISABLED)
        self.text_widget.see(tk.END)


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def get_metadata(file_path) -> tuple:
    try:
        with taglib.File(file_path) as f:
            artist = next(iter(f.tags.get('ARTIST', [])), None)
            title = next(iter(f.tags.get('TITLE', [])), None)
            bpm = next(iter(f.tags.get('BPM', [])), None)
            metadata = f.tags
        return artist, title, bpm, metadata
    except Exception as e:
        log_error(f"Failed to read metadata from {file_path}: {e}")
        return None, None, None, {}

def tag_music_file(file_path, metadata: Dict):
    try:
        metadata = {key.lower(): value for key, value in metadata.items()}
        with taglib.File(file_path, save_on_exit=True) as f:
            f.tags = {key.lower(): value for key, value in f.tags.items()}
            for key, value in metadata.items():
                if isinstance(value, list):
                    value = ', '.join(map(str, value))
                f.tags[key] = [value]
            f.save()
    except Exception as e:
        log_error(f"Failed to tag {file_path}: {e}")

def process_directory(directory):
    all_files = []
    skip_files = ['desktop', 'Thumbs', 'order', 'Videos - Shortcut']
    for root, dirs, files in os.walk(directory):
        for name in files:
            if name.lower().endswith(".mp3") and not any(skip_file in name for skip_file in skip_files):
                full_path = os.path.join(root, name)
                full_path = os.path.normpath(full_path)  # Normalize the path
                if ensure_local(full_path):
                    all_files.append(full_path)
                else:
                    log_error(f"File {full_path} is not available locally or cannot be accessed.")
    return all_files

def ensure_local(file_path):
    return os.path.exists(file_path) and os.access(file_path, os.R_OK)


def convert_mp3_to_wav(mp3_path, wav_path):
    try:
        subprocess.run([ffmpeg_path,
                         "-i", mp3_path, wav_path, "-y"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        log_error(f"Failed to convert {mp3_path} to WAV: {e}")
        return False
    logger.info(f"Converted {mp3_path} to WAV")
    return True

def set_window_and_hop_sizes(sample_rate, task='beat'):
    if task == 'pitch':
        win_s = 4096 if sample_rate >= 44100 else 2048
        hop_s = win_s // 4
    elif task == 'onset':
        win_s = 1024 if sample_rate >= 44100 else 512
        hop_s = win_s // 2
    elif task == 'beat':
        win_s = 2048 if sample_rate >= 44100 else 1024
        hop_s = win_s // 2
    elif task == 'mfcc':
        win_s = 4096 if sample_rate >= 44100 else 2048
        hop_s = win_s // 4
    else:
        raise ValueError("Unknown task")
    return win_s, hop_s

def compute(file_path: str, bpm: float):
    bpm = round(bpm, 2)
    _, _, _, metadata = get_metadata(file_path)
    if metadata:
        metadata['BPM'] = str(bpm)
        tag_music_file(file_path, metadata)

def get_temp_file(extension=".wav"):
    return os.path.join(tempfile.gettempdir(), f"temp{extension}")

def has_permission(file_path):
    return os.path.exists(file_path) and os.access(file_path, os.R_OK) and os.access(file_path, os.W_OK)

def delete_temp_file(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        log_error(f"Failed to delete temporary file {path}: {e}")

def log_error(message):
    logger.error(message)

def check_dependencies():
    missing_dependencies = []
    try:
        import ffmpeg
    except ImportError:
        missing_dependencies.append('ffmpeg-python')
    try:
        import aubio
    except ImportError:
        missing_dependencies.append('aubio')
    try:
        import numpy
    except ImportError:
        missing_dependencies.append('numpy')
    try:
        import taglib
    except ImportError:
        missing_dependencies.append('pytaglib')

    if missing_dependencies:
        missing_str = ", ".join(missing_dependencies)
        messagebox.showerror("Missing Dependencies", f"The following dependencies are missing: {missing_str}")
        log_error(f"Missing dependencies: {missing_str}")
        return False
    return True

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("BPM TAGGER")

        self.label = tk.Label(root, text="Select a directory containing MP3 files:")
        self.label.pack(pady=10)

        self.browse_button = tk.Button(root, text="Browse", command=self.browse_directory)
        self.browse_button.pack(pady=10)

        self.progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=20)

        self.status_label = tk.Label(root, text="")
        self.status_label.pack(pady=10)

        # Create a frame for the Text and Scrollbar
        self.log_frame = tk.Frame(root)
        self.log_frame.pack(pady=10)

        self.log_text = tk.Text(self.log_frame, height=50, width=200)
        self.log_text.pack(side=tk.LEFT, fill=tk.Y)

        self.scrollbar = tk.Scrollbar(self.log_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Attach the scrollbar to the Text widget
        self.log_text.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.log_text.yview)

        self.log_text.insert(tk.END, "Log Output:\n")
        text_handler = TextHandler(self.log_text)
        text_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(text_handler)
        self.directory = None
        self.failed_files = []
        self.threads = []
        self.stop_events = []


    def browse_directory(self):
        self.directory = filedialog.askdirectory()
        if self.directory:
            self.status_label.config(text="Processing files...")
            stop_event = threading.Event()
            thread = threading.Thread(target=self.process_files_thread, args=(stop_event,))
            self.threads.append(thread)
            self.stop_events.append(stop_event)
            thread.start()

    def process_files_thread(self, stop_event):
        while not stop_event.is_set():
            self.process_files()
            self.root.after(0, self.update_gui_after_processing)

    def update_gui_after_processing(self):
        self.status_label.config(text="Processing complete!")
        if self.failed_files:
            messagebox.showwarning("Processing complete with errors", f"Failed to process {len(self.failed_files)} files. Check log for details.")
            self.log_text.config(state=tk.NORMAL)
            failed_files_str = "\n".join(self.failed_files)
            self.log_text.insert(tk.END, f"Failed to process the following files:\n{failed_files_str}\n")
            self.log_text.config(state=tk.DISABLED)

    def process_files(self):
        if self.directory:
            
            mp3_paths = process_directory(self.directory)
            total_files = len(mp3_paths)
            wav_path = get_temp_file()

            self.progress["maximum"] = total_files
            self.failed_files = []

            for i, mp3_path in enumerate(mp3_paths):                
                
                if not has_permission(mp3_path):
                    log_error(f"File does not exist or permission denied for file: {mp3_path}")
                    self.log_text.insert(tk.END, f"File does not exist or permission denied for file: {mp3_path}\n")
                    self.failed_files.append(mp3_path)
                    continue
                
                try:
                    logger.info('Converting mp3 to wav')
                    #  check if file can still be accessed locally
                    if not ensure_local(mp3_path):
                        logger.error(f"File {mp3_path} is not available locally or cannot be accessed.")
                        self.log_text.insert(tk.END, f"File {mp3_path} is not available locally or cannot be accessed.\n")
                        self.failed_files.append(mp3_path)
                        continue
                    #  get the audio file
                    convert_mp3_to_wav(mp3_paths[i], wav_path)
                    logger.info('Creating aubio source')
                    try:
                        s = aubio.source(wav_path)
                        sample_rate = s.samplerate
                    
                        task = 'beat'
                        win_s, hop_s = set_window_and_hop_sizes(sample_rate, task)
                    
                        logger.info('Creating aubio tempo')
                        tempo_o = aubio.tempo("default", win_s, hop_s, sample_rate)
                    
                        s = aubio.source(wav_path, sample_rate, hop_s)
                    except Exception as e:
                        logger.error(f"aubio error processing {mp3_path}: {e}")
                        self.log_text.insert(tk.END, f"aubio error processing {mp3_path}: {e}\n")
                        self.failed_files.append(mp3_path)
                        continue

                    total_frames = 0
                    beats = []
                
                    logger.info('Starting beat detection loop')
                    while True:
                        samples, read = s()
                        if tempo_o(samples):
                            this_beat = tempo_o.get_last_s()
                            beats.append(this_beat)
                        total_frames += read
                        if read < hop_s:
                            break
                
                    del s  # Delete the aubio.source object to close the file
                
                    beats = np.array(beats)
                
                    if len(beats) > 1:
                        logger.info('Calculating BPM')
                        intervals = np.diff(beats)
                        bpm = np.median(60.0 / intervals)
                        compute(mp3_path, bpm)
                    else:
                        logger.info('No beats detected')
                        self.failed_files.append('\\'.join(mp3_path.split('\\')[-2:])) 
                except ffmpeg.Error as e:
                    logger.error(f"ffmpeg error processing {mp3_path}: {e}")
                    self.log_text.insert(tk.END, f"ffmpeg error processing {mp3_path}: {e}\n")
                    self.failed_files.append('\\'.join(mp3_path.split('\\')[-2:]))

                except Exception as e:
                    logger.error(f"General error processing {mp3_path}: {e}")
                    self.log_text.insert(tk.END, f"General error processing {mp3_path}: {e}\n")
                    self.failed_files.append('\\'.join(mp3_path.split('\\')[-2:]))
                finally:
                    logger.info('Deleting temp file')
                    delete_temp_file(wav_path)

                self.progress["value"] = i + 1
                self.root.update_idletasks()
            
            self.progress["value"] = total_files
            # set stop event to stop the thread
            self.status_label.config(text="Processing complete!")
            self.stop_events[-1].set()
            if self.failed_files:
                messagebox.showwarning("Processing complete with errors", f"Failed to process {len(self.failed_files)} files. Check log for details.")
                self.log_text.config(state=tk.NORMAL)
                failed_files_str = "\n".join(self.failed_files)
                self.log_text.insert(tk.END, f"Failed to process the following files:\n{failed_files_str}\n")
                self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def on_closing(self):
        # Set all stop events
        for stop_event in self.stop_events:
            stop_event.set()

        # Wait for all threads to finish
        for thread in self.threads:
            thread.join()

        # Destroy the window
        self.root.destroy()

if __name__ == "__main__":
    if check_dependencies():
        root = tk.Tk()
        app = App(root)
        # Bind the on_closing function to the WM_DELETE_WINDOW protocol
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        root.mainloop()
    else:
        log_error("Failed to start application due to missing dependencies.")
