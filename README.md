# Sound Seeker

Sound Seeker is a Python application to automate the process of building your music library from Spotify playlists. It fetches tracks from your specified playlists and attempts to download the highest quality version available from Usenet via SABnzbd. If a track cannot be found on Usenet, it falls back to using SpotDL to grab it from alternative sources like YouTube Music.

- Downloading tracks from Usenet using SABnzbd.
- Fallback to SpotDL for tracks not found on Usenet.
- Creates clean folder structures for artists and songs (e.g. `Artist/Song Title/artist-songtitle.ogg`).
- Creates `.m3u` playlist files for easy import into media servers like Navidrome.

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

3. **Create `yt_cookies.txt` File**
    You need to create a `yt_cookies.txt` file that SpotDL will use to access YouTube Music. This file should contain your YouTube cookies in the format required by SpotDL. You can export your cookies using browser extensions like [Get-cookies.txt-LOCALLY](https://github.com/kairi003/Get-cookies.txt-Locally).

    Place this file in the directory specified by the `COOKIES_PATH` environment variable in your `.env` file.

3.  **Create `playlists.txt` File**
    Create a file named `playlists.txt` in the directory specified by `SPOTIFY_PLAYLISTS_PATH`. Add your Spotify playlist URLs, one per line.

4.  **Run the Application**
    ```bash
    python main.py
    ```

### Running with Docker (Recommended)

1.  **Install Docker and Docker Compose.**
    Follow the official installation guide for your operating system.

2.  **Configure `docker-compose.yml`**
    Open the `docker-compose.yml` file and edit the following sections:
    -   **`environment`**: Replace all `xxx` placeholders with your actual API keys and secrets. If SABnzbd is running on the same machine (your host), change the `SABNZBD_URL` to `http://host.docker.internal:8080`. This special DNS name allows the container to connect to services running on your host.
    -   **`volumes`**: Replace all instances of `/your/path` with the **absolute paths** on your local machine. This connects your local folders to the folders inside the container, ensuring your data persists.
    ```

3.  **Place Configuration Files**
    Based on the example above, make sure your `playlists.txt` and `yt_cookies.txt` files are located in the local directory you mapped to `/config` (e.g., `/your/path/config`).

4.  **Build and Run the Container**
    Open a terminal in the project's root directory and run:
    ```bash
    docker-compose up --build
    ```
    The application will start inside the container.

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
-   `COOKIES_PATH`: The path to the directory containing the cookies file used by SpotDL ( `yt_cookies.txt`).
-   `SPOTIFY_PLAYLISTS_PATH`: The path to the directory where your `playlists.txt` file is located.
-   `PORT`: The port on which the web application will run (default is 5000).