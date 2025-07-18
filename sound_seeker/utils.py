import logging
import os

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
