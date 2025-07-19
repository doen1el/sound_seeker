import os
import shutil
import glob
import time
import subprocess

def convert_flac_to_ogg(src_file, dst_file, logger, bitrate="320k"):
    try:
        cmd = ["ffmpeg", "-y", "-i", src_file, "-c:a", "libvorbis", "-b:a", bitrate, dst_file]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"Converting {src_file} to {dst_file} completed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg conversion error: {e.stderr}")
        raise

def move_and_rename_downloaded_file(nzb_title, artist, title, ext, download_dir, clean_dir, logger):
    src_folder = os.path.join(download_dir, nzb_title)
    artist_dir = os.path.join(clean_dir, artist)
    song_dir = os.path.join(artist_dir, title)
    os.makedirs(song_dir, exist_ok=True)
    
    try:
        for file in os.listdir(src_folder):
            if file.lower().endswith(f".{ext}"):
                src_file = os.path.join(src_folder, file)
                final_filename_base = f"{artist} - {title}"
                
                if ext == "flac":
                    temp_dst_file = os.path.join(song_dir, f"{final_filename_base}.flac")
                    final_dst_file = os.path.join(song_dir, f"{final_filename_base}.ogg")
                    shutil.move(src_file, temp_dst_file)
                    logger.info(f"Moved: {src_file} -> {temp_dst_file}")
                    convert_flac_to_ogg(temp_dst_file, final_dst_file, logger)
                    os.remove(temp_dst_file)
                    logger.info(f"Removed original flac file: {temp_dst_file}")
                else:
                    final_dst_file = os.path.join(song_dir, f"{final_filename_base}.{ext}")
                    shutil.move(src_file, final_dst_file)
                    logger.info(f"Moved and renamed: {src_file} -> {final_dst_file}")
                
                shutil.rmtree(src_folder)
                logger.info(f"SABnzbd-Folder deleted: {src_folder}")
                return
    except Exception as e:
        logger.error(f"Error while removing/deleting '{nzb_title}': {e}")

def wait_for_download_folder(nzb_title, download_dir, logger, exts=("flac", "mp3"), timeout=60, poll_interval=2):
    src_folder = os.path.join(download_dir, nzb_title)
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(src_folder):
            for ext in exts:
                if glob.glob(os.path.join(src_folder, f"*.{ext}")):
                    logger.info(f"Found matching audio file in {src_folder} with extension {ext}.")
                    return ext
        time.sleep(poll_interval)
    logger.warning(f"Timeout: No matching audio file found in {src_folder} after {timeout} seconds.")
    return None

def create_and_add_to_m3u(playlist_name, artist, title, clean_dir, logger):
    try:
        m3u_file = os.path.join(clean_dir, f"{playlist_name}.m3u")
        track_path = os.path.join(artist, title, f"{artist} - {title}.ogg")
        with open(m3u_file, "a", encoding="utf-8") as f:
            f.write(f"{track_path}\n")
        logger.info(f"'{artist} - {title}' added to {m3u_file}.")
    except Exception as e:
        logger.error(f"Error while adding to M3U file: {e}")

def remove_empty_folders(clean_dir, logger):
    if not os.path.isdir(clean_dir):
        logger.warning(f"{clean_dir} not found or is not a directory.")
        return
    for root, dirs, files in os.walk(clean_dir, topdown=False):
        for name in dirs:
            dir_path = os.path.join(root, name)
            if not os.listdir(dir_path):
                try:
                    os.rmdir(dir_path)
                    logger.info(f"Removed folder: {dir_path}")
                except OSError as e:
                    logger.error(f"Error while removing {dir_path}: {e}")
