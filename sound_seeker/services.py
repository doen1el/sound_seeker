import os
import requests
import xmltodict
import urllib.parse
import subprocess
import time
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

def get_music_by_search(query, api_key, logger):
    try:
        query_encoded = urllib.parse.quote(query)
        url = f"https://scenenzbs.com/api?t=search&q={query_encoded}&apikey={api_key}"
        response = requests.get(url)
        response.raise_for_status()
        return xmltodict.parse(response.content)
    except Exception as e:
        logger.error(f"Error fetching music by search from scenenzbs: {e}")
        return None

def send_to_sabnzbd(nzb_url, nzb_title, sab_url, api_key, cat, logger):
    try:
        params = {"mode": "addurl", "name": nzb_url, "apikey": api_key, "cat": cat, "nzbname": nzb_title}
        url = f"{sab_url}/api"
        r = requests.get(url, params=params)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error(f"Error sending NZB to SABnzbd: {e}")
        return None

def wait_for_sabnzbd_job(nzb_title, sab_url, api_key, logger, timeout=1000, poll_interval=10):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            resp = requests.get(f"{sab_url}/api", params={"mode": "history", "output": "json", "apikey": api_key})
            data = resp.json()
            for job in data.get("history", {}).get("slots", []):
                if job.get("name") == nzb_title and job.get("status") == "Completed":
                    logger.info(f"SABnzbd-Job '{nzb_title}' completed.")
                    return True
            logger.info(f"Waiting for SABnzbd job '{nzb_title}' to complete...")
            time.sleep(poll_interval)
        except Exception as e:
            logger.error(f"Error while checking SABnzbd job status: {e}")
            time.sleep(poll_interval)
    logger.error(f"Timeout: SABnzbd job '{nzb_title}' did not complete within {timeout} seconds.")
    return False

def find_playlist_tracks(playlist_id, client_id, client_secret, logger):
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))
        
        playlist_info = sp.playlist(playlist_id, fields="name,tracks.total")
        playlist_name = playlist_info['name']
        total_tracks = playlist_info['tracks']['total']

        if total_tracks == 0:
            logger.warning(f"Playlist '{playlist_name}' is empty.")
            return playlist_name, []

        logger.info(f"Fetching {total_tracks} tracks from playlist '{playlist_name}'...")

        all_tracks = []
        results = sp.playlist_tracks(playlist_id)
        all_tracks.extend(results['items'])

        while results['next']:
            results = sp.next(results)
            all_tracks.extend(results['items'])
            logger.info(f"Fetched {len(all_tracks)}/{total_tracks} tracks...")

        logger.info(f"Successfully fetched all {len(all_tracks)} tracks from '{playlist_name}'.")
        return playlist_name, all_tracks
        
    except Exception as e:
        logger.error(f"Error fetching playlist tracks: {e}")
        return None, []

def download_with_spotdl(track_id, artist, title, clean_dir, logger, audio_format="ogg"):
    try:
        artist_dir = os.path.join(clean_dir, artist)
        song_dir = os.path.join(artist_dir, title)
        os.makedirs(song_dir, exist_ok=True)
        spotify_url = f"https://open.spotify.com/track/{track_id}"
        cmd = [
            "spotdl", "download", spotify_url,
            "--output", song_dir,
            "--format", audio_format,
            "--audio", "youtube-music",
            "--overwrite", "force",
            "--cookie-file", os.path.join(os.getenv("COOKIES_PATH"), "yt_cookies.txt"),
            "--client-id", os.getenv("SPOTIFY_CLIENT_ID"),
            "--client-secret", os.getenv("SPOTIFY_CLIENT_SECRET"),
        ]
        logger.info(f"Downloading with SpotDL: {artist} - {title}.{audio_format}")
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"Successfully downloaded '{artist} - {title}.{audio_format}'")
    except subprocess.CalledProcessError as e:
        logger.error(f"SpotDL-Error: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"Common error during SpotDL download: {e}")
        raise