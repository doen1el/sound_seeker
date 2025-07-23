import logging
import os

cached_env = None

def get_cached_env(logger, force_refresh=False):
    global cached_env
    if cached_env is None or force_refresh:
        cached_env = check_and_load_env(logger, silent=True)
    return cached_env

def check_and_load_env(logger, silent=False):
    env_keys = [
        "SCENENZBS_API_KEY", "SABNZBD_API_KEY", "SABNZBD_URL", "SABNZBD_CAT",
        "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "DOWNLOAD_DIR", "CLEAN_DIR",
        "SONG_ARCHIVE_DIR", "COOKIES_PATH", "SPOTIFY_PLAYLISTS_PATH"
    ]
    
    env = {k: os.getenv(k) for k in env_keys}

    missing_vars = [k for k, v in env.items() if not v]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    playlists_path = os.path.join(env["SPOTIFY_PLAYLISTS_PATH"], 'playlists.txt')
    if not os.path.exists(playlists_path):
        raise FileNotFoundError(f"Configuration file not found: playlists.txt was expected in '{env['SPOTIFY_PLAYLISTS_PATH']}'")

    cookies_path = os.path.join(env["COOKIES_PATH"], 'yt_cookies.txt')
    if not os.path.exists(cookies_path):
        raise FileNotFoundError(f"Configuration file not found: yt_cookies.txt was expected in '{env['COOKIES_PATH']}'")
    
    dir_keys = ["DOWNLOAD_DIR", "CLEAN_DIR", "SONG_ARCHIVE_DIR", "COOKIES_PATH", "SPOTIFY_PLAYLISTS_PATH"]
    for key in dir_keys:
        if not os.path.isdir(env[key]):
            raise NotADirectoryError(f"The path specified for {key} is not a valid directory: '{env[key]}'")

    if not silent:
        logger.info("Environment variables and configuration files validated successfully.")
    return env

def setup_logger(level=logging.INFO):
    logger = logging.getLogger("SoundSeeker")
    if not logger.hasHandlers():
        logger.setLevel(level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

def load_song_archive(archive_path, logger):
    if not os.path.exists(archive_path):
        logger.info(f"Song archive not found at {archive_path}. Creating a new one.")
        os.makedirs(os.path.dirname(archive_path), exist_ok=True)
        with open(archive_path, "w") as f:
            pass
        return set()
    
    try:
        with open(archive_path, "r") as f:
            return {line.strip() for line in f if line.strip()}
    except Exception as e:
        logger.error(f"Error loading song archive: {e}")
        return set()

def save_to_song_archive(archive_path, track_id, logger):
    try:
        with open(archive_path, "a") as f:
            f.write(f"{track_id}\n")
        logger.info(f"Added '{track_id}' to song archive.")
    except Exception as e:
        logger.error(f"Error saving to song archive: {e}")
