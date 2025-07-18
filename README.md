# Sound Seeker

### Requirements

- Python 3.x
- FFmpeg installed and available in your system's PATH.
- An active Usenet provider subscription.
- A running instance of SABnzbd.
- An account with the SceneNZBs indexer.
- A `yt_cookies.txt` file for SpotDL to access YouTube Music.

### How to Run

1.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Create `.env` File**
    Create a file named `.env` in the root directory and fill it with the required values. See the section below for details.

3.  **Create `playlists.txt` File**
    Create a file named `playlists.txt` in the directory specified by `SPOTIFY_PLAYLISTS_PATH`. Add your Spotify playlist URLs, one per line.

4.  **Run the Application**
    ```bash
    python main.py
    ```

### Environment Variables

Create a `.env` file in the project root with the following variables:

-   `SCENENZBS_API_KEY`: Your API key for the SceneNZBs indexer.
-   `SABNZBD_API_KEY`: Your API key for SABnzbd.
-   `SABNZBD_URL`: The full URL to your SABnzbd instance (e.g., `http://localhost:8080`).
-   `SABNZBD_CAT`: The category to use for music downloads in SABnzbd.
-   `SPOTIFY_CLIENT_ID`: Your Spotify application client ID.
-   `SPOTIFY_CLIENT_SECRET`: Your Spotify application client secret.
-   `DOWNLOAD_DIR`: The temporary folder where SABnzbd places completed downloads.
-   `CLEAN_DIR`: The final destination folder for sorted and processed music files.
-   `SONG_ARCHIVE_DIR`: The directory where the `songarchive.log` will be stored to track downloaded songs.
-   `COOKIES_PATH`: The path to the directory containing the cookies file used by SpotDL (e.g., `yt_cookies.txt`).
-   `SPOTIFY_PLAYLISTS_PATH`: The path to the directory where your `playlists.txt` file is located.