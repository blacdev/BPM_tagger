
# BPM Tagger

This project is a BPM tagger for music files. It uses the [aubio](https://aubio.org/) library to calculate the BPM of a music file and then writes the BPM to the file's metadata.

## Dependencies

- [aubio](https://aubio.org/)
- [ffmpeg-python](https://github.com/kkroening/ffmpeg-python)
- [Pytaglib](https://github.com/supermihi/pytaglib)
- [Tkinter](https://wiki.python.org/moin/TkInter)
- [Pyinstaller](https://www.pyinstaller.org/)

## Installation

First, install ffmpeg and aubio. On Ubuntu, you can do this with the following command:

```bash
sudo apt-get install ffmpeg libaubio-dev
```

For other operating systems, you can find:

- aubio installation instructions [here](https://aubio.org/download)
  
- ffmpeg installation instructions [here](https://ffmpeg.org/download.html)

Then, install the Python dependencies:

```bash
pip install -r requirements.txt
```

## Usage

To use the BPM tagger, clone the repo:

```bash
git clone <repo-url>
cd bpm-tagger
```

Then run the following command:

```bash
python main.py
```

This will open a GUI where you can select the music file you want to tag. Once you select the file, the BPM will be calculated and written to the file's metadata.

## Build Desktop App

To build a desktop app, you can use PyInstaller. First, make sure you have PyInstaller installed:

```bash
pip install pyinstaller
```

Then run the following command:

```bash
pyinstaller --onefile --clean --windowed --name "<app-name>" main.py
```

This will create a standalone executable in the `dist` directory.
