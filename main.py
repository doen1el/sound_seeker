import logging
from sound_seeker.core import SoundSeeker
from sound_seeker.utils import setup_logger

if __name__ == "__main__":
    logger = setup_logger(level=logging.INFO)
    try:
        downloader = SoundSeeker(logger=logger)
        downloader.remove_empty_folders()
        downloader.download_each_playlist()
        logger.info("SoundSeeker successfully completed all tasks.")
    except Exception as e:
        logger.critical(f"Critical error in SoundSeeker: {e}")