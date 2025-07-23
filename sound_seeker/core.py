import os
from dotenv import load_dotenv
import time
from . import utils, services, file_handler

class SoundSeeker:
    def __init__(self, logger):
        load_dotenv()
        self.logger = logger
        self.env = utils.get_cached_env(self.logger)
        self.song_archive_path = os.path.join(self.env["SONG_ARCHIVE_DIR"], "songarchive.log")
        self.song_archive = utils.load_song_archive(self.song_archive_path, self.logger)
        self.stop_event = None
        self.pause_event = None
        self.skip_event = None
        
    def check_events(self):
        if self.stop_event and self.stop_event.is_set():
            self.logger.info("Stop event detected. Terminating download.")
            return True

        if self.pause_event and self.pause_event.is_set():
            self.logger.info("Pause-Event detected. Waiting for resume...")
            while self.pause_event.is_set() and not (self.stop_event and self.stop_event.is_set()):
                if self.skip_event and self.skip_event.is_set():
                    self.logger.info("Skip event detected during pause. Will skip after resume.")
                time.sleep(0.5)
                
            if self.stop_event and self.stop_event.is_set():
                return True
                
            self.logger.info("Resuming download after pause.")
            
        if self.skip_event and self.skip_event.is_set():
            self.logger.info("Skip event detected. Moving to next track.")
            self.skip_event.clear()
            return "skip"
            
        return False

    def download_tracks(self, playlist_tracks, playlist_name):
        total = len(playlist_tracks)
        for step, item in enumerate(playlist_tracks, start=1):
            # Only for debugging purposes, uncomment to limit steps
            # if step >= 5:
            #     break
            
            check_result = self.check_events()
            if check_result is True: 
                return
            elif check_result == "skip":
                continue
        
            if not item or not item.get('track'):
                self.logger.warning(f"Skipping invalid track item in {playlist_name} at step {step}.")
                continue

            track = item['track']
            track_id = track['id']
            artist_search_str = ' '.join(artist['name'] for artist in track['artists'])
            artist_file_str = ', '.join(artist['name'] for artist in track['artists'])
            title_str = track['name']

            self.logger.info(f"Processing {step}/{total}: {artist_file_str} - {title_str}")

            if track_id in self.song_archive:
                self.logger.info(f"Track already in archive. Adding to playlist {playlist_name} and skipping download...")
                if file_handler.check_if_song_exists(artist_file_str, title_str, self.env['CLEAN_DIR'], self.logger, ext="ogg"):
                    file_handler.create_and_add_to_m3u(playlist_name, artist_file_str, title_str, self.env['CLEAN_DIR'], self.logger, ext="ogg")
                elif file_handler.check_if_song_exists(artist_file_str, title_str, self.env['CLEAN_DIR'], self.logger, ext="mp3"):
                    file_handler.create_and_add_to_m3u(playlist_name, artist_file_str, title_str, self.env['CLEAN_DIR'], self.logger, ext="mp3")
                else:
                    self.logger.warning(f"Archived song '{artist_file_str} - {title_str}' not found on disk. Re-downloading might be necessary.")
                continue

            if self.try_usenet_download(artist_search_str, artist_file_str, title_str, track_id, playlist_name):
                continue

            self.logger.warning(f"No NZB found for '{artist_file_str} - {title_str}', trying SpotDL...")
            self.try_spotdl_download(track_id, artist_file_str, title_str, playlist_name)

    def try_usenet_download(self, artist_search_str, artist_file_str, title_str, track_id, playlist_name):
        if self.check_events():
            return
        query = f"{artist_search_str} {title_str}"
        data = services.get_music_by_search(query, self.env['SCENENZBS_API_KEY'], self.logger)
        if not data or data.get("rss", {}).get("channel", {}).get("newznab:response", {}).get("@total") == "0":
            return False

        items = data['rss']['channel'].get('item', [])
        items = [items] if isinstance(items, dict) else items

        for item in items:
            nzb_url = item.get('enclosure', {}).get('@url')
            nzb_title = f"{artist_file_str} - {title_str}"
            if nzb_url:
                self.logger.info(f"NZB found: {nzb_title}")
                services.send_to_sabnzbd(nzb_url, nzb_title, self.env['SABNZBD_URL'], self.env['SABNZBD_API_KEY'], self.env['SABNZBD_CAT'], self.logger)
                
                ext = file_handler.wait_for_download_folder(nzb_title, self.env['DOWNLOAD_DIR'], self.logger)
                if ext:
                    file_handler.move_and_rename_downloaded_file(nzb_title, artist_file_str, title_str, ext, self.env['DOWNLOAD_DIR'], self.env['CLEAN_DIR'], self.logger)
                    
                    final_ext = "ogg" if ext == "flac" else ext
                    if file_handler.check_if_song_exists(artist_file_str, title_str, self.env['CLEAN_DIR'], self.logger, ext=final_ext):
                        utils.save_to_song_archive(self.song_archive_path, track_id, self.logger)
                        self.song_archive.add(track_id)
                        file_handler.create_and_add_to_m3u(playlist_name, artist_file_str, title_str, self.env['CLEAN_DIR'], self.logger, ext=final_ext)
                        return True
        return False

    def try_spotdl_download(self, track_id, artist_file_str, title_str, playlist_name):
        if self.check_events():
            return
        try:
            services.download_with_spotdl(track_id, artist_file_str, title_str, self.env['CLEAN_DIR'], self.logger)
            
            if file_handler.check_if_song_exists(artist_file_str, title_str, self.env['CLEAN_DIR'], self.logger, ext="ogg"):
                utils.save_to_song_archive(self.song_archive_path, track_id, self.logger)
                self.song_archive.add(track_id)
                file_handler.create_and_add_to_m3u(playlist_name, artist_file_str, title_str, self.env['CLEAN_DIR'], self.logger, ext="ogg")
        except Exception as e:
            self.logger.error(f"SpotDL download failed for '{artist_file_str} - {title_str}': {e}")

    def download_each_playlist(self):
        if self.check_events():
            return
        try:
            file_path = os.path.join(self.env["SPOTIFY_PLAYLISTS_PATH"], 'playlists.txt')
            with open(file_path, "r") as f:
                playlists = [line.strip() for line in f if line.strip().startswith("https://open.spotify.com/")]
        except Exception as e:
            self.logger.error(f"Error reading playlists file: {e}")
            return

        if not playlists:
            self.logger.error("No playlists found in the file.")
            return

        for playlist_url in playlists:
            self.logger.info(f"Begin processing playlist: {playlist_url}")
            playlist_id = playlist_url.split('/')[-1].split('?')[0]
            playlist_name, tracks = services.find_playlist_tracks(playlist_id, self.env['SPOTIFY_CLIENT_ID'], self.env['SPOTIFY_CLIENT_SECRET'], self.logger)
            if tracks:
                self.download_tracks(tracks, playlist_name)

    def remove_empty_folders(self):
        self.logger.info("Removing empty folders in the clean directory...")
        file_handler.remove_empty_folders(self.env['CLEAN_DIR'], self.logger)