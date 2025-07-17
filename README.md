# SoundSeeker

SoundSeeker is an automated music downloader for Spotify playlists.  
It searches for tracks on Usenet (SceneNZBs) and, if not found, downloads them from YouTube.  
All tracks are organized in folders by artist and title.

## Features

- Download all tracks from one or more Spotify playlists
- Prefers lossless/high-quality Usenet sources (FLAC/MP3)
- Falls back to YouTube (yt-dlp) if not available on Usenet
- Converts FLAC to MP3 automatically
- Organizes files as: `clean/Artist/Title/Artist - Title.mp3`
- Creates `.m3u` playlists for each Spotify playlist
- Keeps a log of downloaded tracks to avoid duplicates

## Requirements

- Python 3.8+
- [ffmpeg](https://ffmpeg.org/) (must be installed and in your PATH)
- Usenet access (with SceneNZBs API key)
- Spotify API credentials
- YouTube account cookies for yt-dlp (to avoid download restrictions) made with a browser extension like [Get cookies.txt](https://github.com/kairi003/Get-cookies.txt-LOCALLY/)

## Installation

1. **Clone this repository:**

    ```sh
    git clone <your-repo-url>
    cd sound_seeker
    ```

2. **Install Python dependencies:**

    ```sh
    pip install -r requirements.txt
    ```

3. **Install ffmpeg (if not already installed):**

    - **macOS:**  
      `brew install ffmpeg`
    - **Ubuntu:**  
      `sudo apt install ffmpeg`
    - **Windows:**  
      Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.

4. **Set up your `.env` file:**

    Copy the provided `.env` example and fill in your credentials and paths.

    ```
    SCENENZBS_API_KEY=your_scenenzbs_api_key
    SABNZBD_API_KEY=your_sabnzbd_api_key
    SABNZBD_URL=http://127.0.0.1:8080
    SABNZBD_CAT=music
    SPOTIFY_CLIENT_ID=your_spotify_client_id
    SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
    DOWNLOAD_DIR=/absolute/path/to/downloads/music
    CLEAN_DIR=/absolute/path/to/downloads/music/clean
    SONG_ARCHIVE_DIR=/absolute/path/to/downloads
    COOKIES_PATH=/absolute/path/to/your/cookies
    SPOTIFY_PLAYLISTS_PATH=/absolute/path/to/your/project
    ```

5. **Add your Spotify playlists:**

    - Create a file named `playlists.txt` in the folder specified by `SPOTIFY_PLAYLISTS_PATH`.
    - Add one Spotify playlist URL per line.

6. **Export YouTube cookies for yt-dlp:**

    - Use a browser extension like [Get cookies.txt](https://github.com/kairi003/Get-cookies.txt-LOCALLY/) to export your YouTube cookies.
    - Save the file as `yt_cookies.txt` in the folder specified by `COOKIES_PATH`.

## Usage

Run the main script:

```sh
python sound_seeker.py
```

The script will:

- Read all playlist URLs from `playlists.txt`
- Download each track (Usenet first, YouTube as fallback)
- Organize files in `CLEAN_DIR` as `Artist/Title/Artist - Title.mp3`
- Update `.m3u` playlists and the song archive log

## Notes

- Usenet downloads require a working SABnzbd instance and API key.
- YouTube downloads may require cookies to bypass restrictions.
- The script avoids duplicate downloads by keeping a log of track IDs.

## Troubleshooting

- **ffmpeg not found:**  
  Make sure `ffmpeg` is installed and available in your system PATH.
- **Spotify API errors:**  
  Double-check your client ID/secret and that your credentials are valid.
- **Usenet not finding tracks:**  
  Some tracks may not be available on SceneNZBs; YouTube fallback will be used.
- **YouTube download errors:**  
  Try updating your cookies or yt-dlp.

---

**Enjoy your organized music