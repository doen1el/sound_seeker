import os
import threading
import time
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from sound_seeker.core import SoundSeeker
from sound_seeker.utils import get_cached_env
from sound_seeker import services
import logging

app = Flask(__name__, template_folder='web/templates', static_folder='web/static')
socketio = SocketIO(app, cors_allowed_origins="*")

class SocketLogger(logging.Logger):
    def __init__(self, name, level=logging.INFO):
        super().__init__(name, level)
        self.messages = []
        
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False):
        super()._log(level, msg, args, exc_info, extra, stack_info)
        log_entry = {
            'level': logging.getLevelName(level),
            'message': msg % args if args else msg,
            'timestamp': time.strftime('%H:%M:%S')
        }
        self.messages.append(log_entry)
        if len(self.messages) > 100:
            self.messages.pop(0)
        socketio.emit('log_message', log_entry)

logger = SocketLogger("SoundSeekerWeb", level=logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)

downloader = None
download_thread = None
stop_event = threading.Event()
pause_event = threading.Event()
download_status = {
    'running': False,
    'paused': False,
    'total_tracks': 0,
    'processed_tracks': 0,
    'current_track': '',
    'current_method': ''
}

last_update_time = 0

track_info_cache = {}
playlist_info_cache = {}

def get_track_info_cached(track_id, client_id, client_secret, logger):
    """Cached version of track info retrieval"""
    global track_info_cache
    
    if track_id in track_info_cache:
        return track_info_cache[track_id]
    
    try:
        track_info = services.get_track_info(track_id, client_id, client_secret, logger)
        if track_info:
            track_info_cache[track_id] = track_info
        return track_info
    except Exception as e:
        logger.error(f"Error getting track info: {e}")
        return None

def get_playlists():
    try:
        env = get_cached_env(logger)

        file_path = os.path.join(env["SPOTIFY_PLAYLISTS_PATH"], 'playlists.txt')
        with open(file_path, "r") as f:
            playlist_urls = [line.strip() for line in f if line.strip().startswith("https://open.spotify.com/")]
        
        from sound_seeker.services import get_playlist_info
        playlists_with_details = []
        
        for url in playlist_urls:
            playlist_id = url.split('/')[-1].split('?')[0]
            try:
                info = get_playlist_info(
                    playlist_id, 
                    env['SPOTIFY_CLIENT_ID'], 
                    env['SPOTIFY_CLIENT_SECRET'], 
                    logger
                )
                if info:
                    info['url'] = url
                    playlists_with_details.append(info)
                else:
                    playlists_with_details.append({
                        'id': playlist_id,
                        'name': f"Playlist {playlist_id}",
                        'tracks_total': 0,
                        'image': '',
                        'owner': '',
                        'url': url
                    })
            except Exception as e:
                logger.error(f"Error fetching details for playlist {playlist_id}: {e}")
                playlists_with_details.append({
                    'id': playlist_id,
                    'name': f"Playlist {playlist_id}",
                    'tracks_total': 0,
                    'image': '',
                    'owner': '',
                    'url': url
                })
        
        return playlists_with_details
    except Exception as e:
        logger.error(f"Error reading playlists: {e}")
        return []

def save_playlists(playlists):
    try:
        env = get_cached_env(logger)
        file_path = os.path.join(env["SPOTIFY_PLAYLISTS_PATH"], 'playlists.txt')
        with open(file_path, "w") as f:
            for playlist in playlists:
                url = playlist if isinstance(playlist, str) else playlist.get('url', '')
                if url:
                    f.write(f"{url}\n")
        return True
    except Exception as e:
        logger.error(f"Error saving playlists: {e}")
        return False

def get_downloaded_songs():
    try:
        env = get_cached_env(logger)
        song_archive_path = os.path.join(env["SONG_ARCHIVE_DIR"], "songarchive.log")
        downloaded_songs = []
        
        if os.path.exists(song_archive_path):
            with open(song_archive_path, "r") as f:
                track_ids = [line.strip() for line in f if line.strip()]
            downloaded_songs = [{'id': track_id} for track_id in track_ids]
        
        return downloaded_songs
    except Exception as e:
        logger.error(f"Error getting downloaded songs: {e}")
        return []
    
def get_recent_downloads(limit=5):
    try:
        env = get_cached_env(logger)
        song_archive_path = os.path.join(env["SONG_ARCHIVE_DIR"], "songarchive.log")
        recent_tracks = []
        
        if os.path.exists(song_archive_path):
            with open(song_archive_path, "r") as f:
                all_lines = f.readlines()
                track_ids = [line.strip() for line in all_lines[-limit:] if line.strip()]
            
            if track_ids:                
                for track_id in reversed(track_ids):
                    track_info = get_track_info_cached(
                        track_id, 
                        env['SPOTIFY_CLIENT_ID'], 
                        env['SPOTIFY_CLIENT_SECRET'], 
                        logger
                    )
                    if track_info:
                        recent_tracks.append(track_info)
        
        return recent_tracks
    except Exception as e:
        logger.error(f"Error getting recent downloads: {e}")
        return []
    
def emit_update_recent_downloads():
    global last_update_time
    current_time = time.time()
    
    if current_time - last_update_time > 5:
        socketio.emit('update_recent_downloads')
        last_update_time = current_time

def download_worker():
    global downloader, download_status
    
    
    downloader.stop_event = stop_event
    downloader.pause_event = pause_event
    
    original_info = downloader.logger.info
    original_warning = downloader.logger.warning
    original_error = downloader.logger.error
    
    def patched_info(msg, *args, **kwargs):
        original_info(msg, *args, **kwargs)
        if "Processing" in msg and ":" in msg:
            try:
                parts = msg.split(":")
                track_info = parts[1].strip()
                download_status['current_track'] = track_info
                socketio.emit('status_update', download_status)
            except:
                pass
        elif "NZB found:" in msg:
            download_status['current_method'] = 'Usenet'
            socketio.emit('status_update', download_status)
        elif "Downloading with SpotDL:" in msg:
            download_status['current_method'] = 'SpotDL'
            socketio.emit('status_update', download_status)
        elif "Successfully downloaded with NZB" in msg:
            download_status['processed_tracks'] += 1
            socketio.emit('status_update', download_status)
            emit_update_recent_downloads()
        elif "Successfully downloaded" in msg or "Track already in archive" in msg:
            download_status['processed_tracks'] += 1
            socketio.emit('status_update', download_status)
            emit_update_recent_downloads()
        elif msg.startswith("SpotDL:"):
            download_status['current_track'] += f"\n{msg[8:]}"
            socketio.emit('status_update', download_status)

    def patched_warning(msg, *args, **kwargs):
        original_warning(msg, *args, **kwargs)
        if "Song file not found at expected path:" in msg:
            download_status['processed_tracks'] += 1
            socketio.emit('status_update', download_status)

    downloader.logger.info = patched_info
    downloader.logger.warning = patched_warning
    downloader.logger.error = original_error
    
    try:
        downloader.remove_empty_folders()
        
        file_path = os.path.join(downloader.env["SPOTIFY_PLAYLISTS_PATH"], 'playlists.txt')
        with open(file_path, "r") as f:
            playlists = [line.strip() for line in f if line.strip().startswith("https://open.spotify.com/")]
        
        total_tracks = 0
        for playlist_url in playlists:
            playlist_id = playlist_url.split('/')[-1].split('?')[0]
            playlist_name, tracks = services.find_playlist_tracks(
                playlist_id, 
                downloader.env['SPOTIFY_CLIENT_ID'],
                downloader.env['SPOTIFY_CLIENT_SECRET'],
                logger
            )
            if tracks:
                total_tracks += len(tracks)
        
        download_status['total_tracks'] = total_tracks
        socketio.emit('status_update', download_status)
        
        downloader.download_each_playlist()
        logger.info("All downloads completed successfully")
    except Exception as e:
        logger.error(f"Error in download thread: {e}")
    finally:
        download_status['running'] = False
        download_status['paused'] = False
        socketio.emit('status_update', download_status)
        socketio.emit('update_recent_downloads')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/playlists', methods=['GET'])
def api_get_playlists():
    return jsonify(get_playlists())

@app.route('/api/playlists', methods=['POST'])
def api_add_playlist():
    data = request.json
    playlists = get_playlists()
    
    if data and 'playlist_url' in data:
        playlist_url = data['playlist_url'].strip()
        if playlist_url.startswith("https://open.spotify.com/") and playlist_url not in playlists:
            playlists.append(playlist_url)
            if save_playlists(playlists):
                return jsonify({"success": True, "playlists": playlists})
    
    return jsonify({"success": False, "message": "Invalid playlist URL"}), 400

@app.route('/api/playlists', methods=['DELETE'])
def api_remove_playlist():
    data = request.json
    playlist_objects = get_playlists()
    
    if data and 'playlist_url' in data:
        playlist_url = data['playlist_url']
        
        playlist_urls = []
        found = False
        
        for playlist in playlist_objects:
            current_url = playlist.get('url') if isinstance(playlist, dict) else playlist
            
            if current_url != playlist_url:
                playlist_urls.append(current_url)
            else:
                found = True
        
        if found and save_playlists(playlist_urls):
            return jsonify({"success": True})
        
    return jsonify({"success": False, "message": "Playlist not found"}), 404

@app.route('/api/downloads', methods=['GET'])
def api_get_downloads():
    return jsonify({
        "status": download_status,
        "downloaded_songs": get_downloaded_songs(),
        "recent_tracks": get_recent_downloads(5)
    })

@app.route('/api/downloads/start', methods=['POST'])
def api_start_download():
    global downloader, download_thread, download_status
    
    if download_status['running']:
        if download_status['paused']:
            pause_event.clear()
            download_status['paused'] = False
            socketio.emit('status_update', download_status)
            logger.info("Download resumed")
            return jsonify({"success": True, "message": "Download resumed"})
        return jsonify({"success": False, "message": "Download already running"}), 400
    
    download_status = {
        'running': True,
        'paused': False,
        'total_tracks': 0,
        'processed_tracks': 0,
        'current_track': 'Initializing...',
        'current_method': ''
    }
    
    stop_event.clear()
    pause_event.clear()
    
    downloader = SoundSeeker(logger=logger)
    download_thread = threading.Thread(target=download_worker)
    download_thread.daemon = True
    download_thread.start()
    
    socketio.emit('status_update', download_status)
    logger.info("Download started")
    return jsonify({"success": True, "message": "Download started"})

@app.route('/api/downloads/pause', methods=['POST'])
def api_pause_download():
    global download_status
    
    if not download_status['running']:
        return jsonify({"success": False, "message": "No download running"}), 400
    
    if download_status['paused']:
        return jsonify({"success": False, "message": "Download already paused"}), 400
    
    pause_event.set()
    download_status['paused'] = True
    socketio.emit('status_update', download_status)
    logger.info("Download paused")
    return jsonify({"success": True, "message": "Download paused"})

@app.route('/api/downloads/stop', methods=['POST'])
def api_stop_download():
    global download_status
    
    if not download_status['running']:
        return jsonify({"success": False, "message": "No download running"}), 400
    
    stop_event.set()
    pause_event.clear()
    download_status['running'] = False
    download_status['paused'] = False
    socketio.emit('status_update', download_status)
    logger.info("Download stopped")
    return jsonify({"success": True, "message": "Download stopped"})

@app.route('/api/logs', methods=['GET'])
def api_get_logs():
    return jsonify(logger.messages)

@socketio.on('connect')
def handle_connect():
    socketio.emit('status_update', download_status)
    for msg in logger.messages:
        socketio.emit('log_message', msg)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)