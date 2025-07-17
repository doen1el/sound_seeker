import os
import time
import glob
import shutil
import requests
import xmltodict
import spotipy
import urllib.parse
import subprocess
import logging
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp

def setup_logger(level=logging.INFO):
    logger = logging.getLogger("SoundSeeker")
    if not logger.hasHandlers():
        logger.setLevel(level)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S'))
        logger.addHandler(handler)
    return logger

class SoundSeeker:
    def __init__(self, logger=None):
        load_dotenv()
        self.logger = logger or setup_logger()
        self.env = {k: os.getenv(k) for k in [
            "SCENENZBS_API_KEY", "SABNZBD_API_KEY", "SABNZBD_CAT", "SABNZBD_URL",
            "DOWNLOAD_DIR", "CLEAN_DIR", "SONG_ARCHIVE_DIR", "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"
        ]}
        self.song_archive_path = os.path.join(self.env.get("SONG_ARCHIVE_DIR", "."), "songarchive.log")
        self.song_archive = self.load_song_archive()
        self.logger = logger or setup_logger()
        
    def download_from_youtube(self, artist, title):
        artist_dir = os.path.join(self.env["CLEAN_DIR"], artist)
        song_dir = os.path.join(artist_dir, title)
        os.makedirs(song_dir, exist_ok=True)
        outtmpl = os.path.join(song_dir, f"{artist} - {title}.%(ext)s")
        cookies_path = os.path.join(self.env.get("COOKIES_PATH", "."), "yt_cookies.txt")
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': outtmpl,
            'noplaylist': True,
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            self.logger.info(f"Downloading from YouTube: {artist} - {title} audio")
            ydl.download([f"ytsearch1:{artist} - {title} audio"])
        self.logger.info(f"Downloaded {artist} - {title} from YouTube.")

    def get_music_by_search(self, query):
        try:
            query_encoded = urllib.parse.quote(query)
            url = f"https://scenenzbs.com/api?t=search&q={query_encoded}&apikey={self.env['SCENENZBS_API_KEY']}"
            response = requests.get(url)
            response.raise_for_status()
            return xmltodict.parse(response.content)
        except Exception as e:
            self.logger.error(f"Error fetching music from SceneNZBs: {e}")
            return {}

    def send_to_sabnzbd(self, nzb_url, nzb_title):
        try:
            params = {
                "mode": "addurl",
                "name": nzb_url,
                "apikey": self.env["SABNZBD_API_KEY"],
                "cat": self.env["SABNZBD_CAT"],
                "nzbname": nzb_title
            }
            url = f"{self.env['SABNZBD_URL']}/api"
            r = requests.get(url, params=params)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            self.logger.error(f"Error sending NZB to SABnzbd: {e}")
            return {}

    def find_playlist_tracks(self, playlist_id):
        try:
            sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
                client_id=self.env["SPOTIFY_CLIENT_ID"],
                client_secret=self.env["SPOTIFY_CLIENT_SECRET"]
            ))
            playlist = sp.playlist(playlist_id=playlist_id)
            if playlist['tracks']['total'] == 0:
                self.logger.warning(f"Playlist {playlist_id} has no tracks.")
                return None, []
            self.logger.info(f"Found playlist {playlist['name']} with {playlist['tracks']['total']} tracks")
            return playlist["name"], playlist['tracks']['items']
        except Exception as e:
            self.logger.error(f"Error fetching playlist {playlist_id}: {e}")
            return None, []

    def convert_flac_to_mp3(self, src_file, dst_file, bitrate="320k"):
        try:
            cmd = [
                "ffmpeg", "-y", "-i", src_file, "-ab", bitrate, "-map_metadata", "0", dst_file
            ]
            subprocess.run(cmd, check=True)
            self.logger.info(f"Converted {src_file} -> {dst_file}")
        except Exception as e:
            self.logger.error(f"Error converting {src_file} to mp3: {e}")
            
    def delete_downloaded_file(self, nbz_title):
        src_folder = os.path.join(self.env["DOWNLOAD_DIR"], nbz_title)
        try:
            if os.path.exists(src_folder):
                shutil.rmtree(src_folder)
                self.logger.info(f"Deleted downloaded folder: {src_folder}")
            else:
                self.logger.warning(f"Folder {src_folder} does not exist.")
        except Exception as e:
            self.logger.error(f"Error deleting downloaded file: {e}")

    def move_and_rename_downloaded_file(self, nzb_title, artist, title, ext="flac"):
        src_folder = os.path.join(self.env["DOWNLOAD_DIR"], nzb_title)
        artist_dir = os.path.join(self.env["CLEAN_DIR"], artist)
        song_dir = os.path.join(artist_dir, title)
        os.makedirs(song_dir, exist_ok=True)
        moved = False
        try:
            for file in os.listdir(src_folder):
                if file.lower().endswith(f".{ext}"):
                    src_file = os.path.join(src_folder, file)
                    dst_file = os.path.join(song_dir, f"{artist} - {title}.{ext}")
                    shutil.move(src_file, dst_file)
                    self.logger.info(f"Moved and renamed: {src_file} -> {dst_file}")
                    if ext == "flac":
                        mp3_file = dst_file.replace(".flac", ".mp3")
                        self.convert_flac_to_mp3(dst_file, mp3_file)
                        os.remove(dst_file)
                        self.logger.info(f"Removed original FLAC file: {dst_file}")
                    moved = True
                    break
            if moved and not os.listdir(src_folder):
                shutil.rmtree(src_folder)
                self.logger.info(f"Deleted SABnzbd folder: {src_folder}")
        except Exception as e:
            self.logger.error(f"Error moving/renaming files: {e}")

    def wait_for_sabnzbd_job(self, nzb_title, timeout=1000, poll_interval=10):
        api_key = self.env["SABNZBD_API_KEY"]
        sab_url = self.env["SABNZBD_URL"]
        start_time = time.time()
        try:
            while time.time() - start_time < timeout:
                resp = requests.get(f"{sab_url}/api", params={
                    "mode": "history", "output": "json", "apikey": api_key
                })
                data = resp.json()
                for job in data.get("history", {}).get("slots", []):
                    if job.get("name") == nzb_title and job.get("status") == "Completed":
                        self.logger.info(f"SABnzbd job '{nzb_title}' completed.")
                        return True
                self.logger.info(f"Waiting for SABnzbd job '{nzb_title}'...")
                time.sleep(poll_interval)
            raise TimeoutError(f"SABnzbd job '{nzb_title}' did not complete in time.")
        except Exception as e:
            self.logger.error(f"Error waiting for SABnzbd job: {e}")
            return False

    def wait_for_download_folder(self, src_folder, exts=("flac", "mp3"), timeout=60, poll_interval=2):
        start_time = time.time()
        try:
            while time.time() - start_time < timeout:
                if os.path.exists(src_folder):
                    for ext in exts:
                        files = glob.glob(os.path.join(src_folder, f"*.{ext}"))
                        if files:
                            return ext
                time.sleep(poll_interval)
            raise TimeoutError(f"Folder {src_folder} with audio file not found after sabnzbd finished.")
        except Exception as e:
            self.logger.error(f"Error waiting for download folder: {e}")
            return None

    def create_and_add_to_m3u(self, playlist_name, artist, title):
        try:
            m3u_file = os.path.join(self.env["CLEAN_DIR"], f"{playlist_name}.m3u")
            track_path = os.path.join(self.env["CLEAN_DIR"], artist, title, f"{artist} - {title}.mp3")
            with open(m3u_file, "a") as f:
                f.write(f"{track_path}\n")
            self.logger.info(f"Added {artist} - {title} to {m3u_file}")
        except Exception as e:
            self.logger.error(f"Error updating m3u: {e}")

    def load_song_archive(self):
        song_archive_set = set()
        try:
            if os.path.exists(self.song_archive_path):
                with open(self.song_archive_path, "r") as f:
                    for line in f:
                        parts = line.strip().split()
                        if parts:
                            song_archive_set.add(parts[0])
            else:
                self.logger.info(f"Song archive file {self.song_archive_path} does not exist. Creating a new one.")
                os.makedirs(os.path.dirname(self.song_archive_path), exist_ok=True)
                with open(self.song_archive_path, "w") as f:
                    pass
        except Exception as e:
            self.logger.error(f"Error loading song archive: {e}")
        return song_archive_set

    def is_in_song_archive(self, track_id):
        return track_id in self.song_archive

    def save_to_song_archive(self, track_id):
        try:
            with open(self.song_archive_path, "a") as f:
                f.write(f"{track_id}\n")
            self.song_archive.add(track_id)
            self.logger.info(f"Saved {track_id} to song archive.")
        except Exception as e:
            self.logger.error(f"Error saving to song archive: {e}")

    def download_tracks(self, playlist_tracks, playlist_name):
        try:
            total = len(playlist_tracks)
            for step, item in enumerate(playlist_tracks, start=1):
                self.logger.info(f"Processing track {step}/{total} from playlist {playlist_name}")
                track = item['track']
                track_id = track['id']
                if self.is_in_song_archive(track_id):
                    self.logger.info(f"Track {track['name']} by {', '.join(artist['name'] for artist in track['artists'])} already downloaded. Skipping.")
                    continue
                artist_str = ' '.join(artist['name'] for artist in track['artists'])
                title_str = track['name']
                self.logger.info(f"Searching for {title_str} - {artist_str} on SceneNZBs")
                scenenzbs_data = self.get_music_by_search(f"{artist_str} {title_str}")
                found = False
                if scenenzbs_data.get("rss", {}).get("channel", {}).get("newznab:response", {}).get("@total") != "0":
                    items = scenenzbs_data['rss']['channel'].get('item', [])
                    if isinstance(items, dict):
                        items = [items]
                    max_attempts = 2
                    attempt = 1
                    for item in items:
                        if attempt > max_attempts:
                            break
                        nzb_url = item.get('enclosure', {}).get('@url')
                        nzb_title = f"{artist_str} - {title_str}"
                        if nzb_url:
                            self.logger.info(f"Best NZB: {nzb_title} -> {nzb_url}")
                            result = self.send_to_sabnzbd(nzb_url, nzb_title)
                            src_folder = os.path.join(self.env["DOWNLOAD_DIR"], nzb_title)
                            ext = self.wait_for_download_folder(src_folder, exts=("flac", "mp3"))
                            if ext:
                                self.logger.info(f"SABnzbd response: {result}")
                                self.save_to_song_archive(track_id)
                                self.move_and_rename_downloaded_file(nzb_title, artist_str, title_str, ext=ext)
                                self.delete_downloaded_file(nzb_title)
                                self.create_and_add_to_m3u(playlist_name, artist_str, title_str)
                                found = True
                                break
                            else:
                                self.logger.warning(f"Timeout {attempt}/{max_attempts} for {nzb_title}. Retrying next NZB...")
                                attempt += 1
                            if found:
                                break
                if not found:
                    self.logger.warning(f"No Usenet result for {title_str} - {artist_str}, trying YouTube...")
                    try:
                        self.download_from_youtube(artist_str, title_str)
                        self.save_to_song_archive(track_id)
                        self.create_and_add_to_m3u(playlist_name, artist_str, title_str)
                    except Exception as e:
                        self.logger.error(f"Error downloading from YouTube: {e}")

        except Exception as e:
            self.logger.error(f"Error downloading tracks: {e}")
            
    def load_playlists_from_file(self):
        file_path = os.path.join(os.getenv("SPOTIFY_PLAYLISTS_PATH"), 'playlists.txt')
        playlists = []
        try:
            with open(file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("https://open.spotify.com/"):
                        playlists.append(line)
        except Exception as e:
            print(f"Error loading playlists from file: {e}")
        return playlists
    
    def download_each_playlist(self):
        playlists = self.load_playlists_from_file()
        if not playlists:
            self.logger.error("No playlists found to download.")
            return

        for playlist_url in playlists:
            self.logger.info(f"Processing playlist: {playlist_url}")

            playlist_name, playlist_tracks = self.find_playlist_tracks(playlist_url)
            if not playlist_name or not playlist_tracks:
                self.logger.error(f"Failed to fetch tracks for playlist {playlist_url}")
                continue  # <-- Hier statt return
            self.download_tracks(playlist_tracks, playlist_name)

if __name__ == "__main__":
    logger = setup_logger(level=logging.INFO)
    downloader = SoundSeeker(logger=logger)
    downloader.download_each_playlist()