document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    let downloadStatus = {
        running: false,
        paused: false,
        total_tracks: 0,
        processed_tracks: 0,
        current_track: '',
        current_method: ''
    };

    const startBtn = document.getElementById('start-btn');
    const pauseBtn = document.getElementById('pause-btn');
    const stopBtn = document.getElementById('stop-btn');
    const statusContainer = document.getElementById('status-container');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const downloadMethod = document.getElementById('download-method');
    const currentTrack = document.getElementById('current-track');
    const logMessages = document.getElementById('log-messages');
    const playlistForm = document.getElementById('playlist-form');
    const playlistInput = document.getElementById('playlist-url');
    const playlistList = document.getElementById('playlist-list');
    const downloadCount = document.getElementById('download-count');

    loadPlaylists();
    loadDownloadStatus();
    loadDownloadedSongs();

    socket.on('connect', () => {
    });

    socket.on('disconnect', () => {
    });

    socket.on('log_message', (data) => {
        addLogMessage(data.timestamp, data.level, data.message);
    });

    socket.on('status_update', (data) => {
        updateDownloadStatus(data);
    });

    socket.on('update_recent_downloads', (data) => {
        loadDownloadedSongs();
    });

    startBtn.addEventListener('click', () => {
        if (downloadStatus.paused) {
            fetch('/api/downloads/start', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                    }
                })
                .catch(err => console.error('Error resuming download:', err));
        } else {
            fetch('/api/downloads/start', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                    }
                })
                .catch(err => console.error('Error starting download:', err));
        }
    });

    pauseBtn.addEventListener('click', () => {
        fetch('/api/downloads/pause', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    addLogMessage('System', 'INFO', 'Download paused');
                }
            })
            .catch(err => console.error('Error pausing download:', err));
    });

    stopBtn.addEventListener('click', () => {
        fetch('/api/downloads/stop', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    addLogMessage('System', 'INFO', 'Download stopped');
                }
            })
            .catch(err => console.error('Error stopping download:', err));
    });

    playlistForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const playlistUrl = playlistInput.value.trim();
        
        if (!playlistUrl) return;
        
        fetch('/api/playlists', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ playlist_url: playlistUrl })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                playlistInput.value = '';
                loadPlaylists();
                addLogMessage('System', 'INFO', 'Playlist successfully added');
            } else {
                addLogMessage('System', 'ERROR', 'Error adding playlist: ' + data.message);
            }
        })
        .catch(err => {
            console.error('Error adding playlist:', err);
            addLogMessage('System', 'ERROR', 'Error while adding playlist');
        });
    });

    function updateDownloadStatus(data) {
        downloadStatus = data;
        
        startBtn.disabled = downloadStatus.running && !downloadStatus.paused;
        pauseBtn.disabled = !downloadStatus.running || downloadStatus.paused;
        stopBtn.disabled = !downloadStatus.running;
        
        if (downloadStatus.running) {
            statusContainer.innerHTML = downloadStatus.paused 
                ? '<div class="alert alert-warning">Download paused</div>'
                : '<div class="alert alert-success">Download running</div>';
            
            progressContainer.classList.remove('d-none');
            
            const percent = downloadStatus.total_tracks > 0 
                ? (downloadStatus.processed_tracks / downloadStatus.total_tracks) * 100 
                : 0;
            progressBar.style.width = `${percent}%`;
            progressText.textContent = `Progress: ${downloadStatus.processed_tracks}/${downloadStatus.total_tracks}`;
            
            currentTrack.textContent = downloadStatus.current_track || 'Initialize...';
            downloadMethod.textContent = downloadStatus.current_method 
                ? `Download-Method: ${downloadStatus.current_method}` 
                : '';
        } else {
            statusContainer.innerHTML = '<div class="alert alert-info">No download active. Start a download with the Start button.</div>';
            progressContainer.classList.add('d-none');
        }
    }

    function addLogMessage(timestamp, level, message) {
        const li = document.createElement('li');
        li.className = `list-group-item log-item log-${level.toLowerCase()}`;
        li.textContent = `[${timestamp}] ${level}: ${message}`;
        
        logMessages.appendChild(li);
        
        const logContainer = document.getElementById('log-container');
        logContainer.scrollTop = logContainer.scrollHeight;
        
        if (logMessages.children.length > 100) {
            logMessages.removeChild(logMessages.children[0]);
        }
    }

    function loadPlaylists() {
        fetch('/api/playlists')
            .then(res => res.json())
            .then(data => {
                if (data && data.length > 0) {
                    playlistList.innerHTML = '';
                    data.forEach(playlist => {
                        const li = document.createElement('li');
                        li.className = 'list-group-item';
                        
                        const card = document.createElement('div');
                        card.className = 'card border-0';
                        
                        const row = document.createElement('div');
                        row.className = 'row g-0';
                        
                        const imgCol = document.createElement('div');
                        imgCol.className = 'col-md-2';
                        
                        if (playlist.image) {
                            const img = document.createElement('img');
                            img.src = playlist.image;
                            img.className = 'img-fluid rounded';
                            img.alt = 'Playlist Cover';
                            imgCol.appendChild(img);
                        } else {
                            const noImg = document.createElement('div');
                            noImg.className = 'no-image d-flex justify-content-center align-items-center bg-light rounded';
                            noImg.style.height = '80px';
                            noImg.innerHTML = '<i class="bi bi-music-note-list"></i>';
                            imgCol.appendChild(noImg);
                        }
                        
                        const detailsCol = document.createElement('div');
                        detailsCol.className = 'col-md-8';
                        
                        const cardBody = document.createElement('div');
                        cardBody.className = 'card-body py-1';
                        
                        const title = document.createElement('h5');
                        title.className = 'card-title mb-1';
                        title.textContent = playlist.name || formatPlaylistUrl(playlist.url || playlist);
                        
                        const owner = document.createElement('p');
                        owner.className = 'card-text small mb-1';
                        owner.textContent = playlist.owner ? `von ${playlist.owner}` : '';
                        
                        const tracks = document.createElement('p');
                        tracks.className = 'card-text small text-muted';
                        tracks.textContent = playlist.tracks_total ? `${playlist.tracks_total} Songs` : '';
                        
                        cardBody.appendChild(title);
                        cardBody.appendChild(owner);
                        cardBody.appendChild(tracks);
                        detailsCol.appendChild(cardBody);
                        
                        const deleteCol = document.createElement('div');
                        deleteCol.className = 'col-md-2 d-flex align-items-center justify-content-end';
                        
                        const deleteBtn = document.createElement('button');
                        deleteBtn.className = 'btn btn-sm btn-outline-danger delete-btn';
                        deleteBtn.textContent = 'Remove';
                        deleteBtn.addEventListener('click', () => deletePlaylist(playlist.url || playlist));
                        
                        deleteCol.appendChild(deleteBtn);
                        
                        row.appendChild(imgCol);
                        row.appendChild(detailsCol);
                        row.appendChild(deleteCol);
                        card.appendChild(row);
                        li.appendChild(card);
                        playlistList.appendChild(li);
                    });
                } else {
                    playlistList.innerHTML = '<li class="list-group-item text-center text-muted">No playlists available</li>';
                }
            })
            .catch(err => {
                console.error('Error loading playlists:', err);
                playlistList.innerHTML = '<li class="list-group-item text-center text-danger">Error loading playlists</li>';
            });
    }

    function deletePlaylist(playlistUrl) {
        fetch('/api/playlists', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ playlist_url: playlistUrl })
        })
        .then(res => res.json())
        .then(data => {
             if (data.success) {
                loadPlaylists();
                addLogMessage('System', 'INFO', 'Playlist successfully removed');
            } else {
                addLogMessage('System', 'ERROR', 'Error adding playlist: ' + data.message);
            }
        })
        .catch(err => {
            console.error('Error deleting playlist:', err);
            addLogMessage('System', 'ERROR', 'Error while removing playlist');
        });
    }

    function formatPlaylistUrl(url) {
        const parts = url.split('/');
        const id = parts[parts.length - 1].split('?')[0];
        return id.length > 10 ? `...${id.substring(0, 10)}` : id;
    }

    function loadDownloadStatus() {
        fetch('/api/downloads')
            .then(res => res.json())
            .then(data => {
                if (data && data.status) {
                    updateDownloadStatus(data.status);
                }
            })
            .catch(err => console.error('Error loading download status:', err));
    }

    function loadDownloadedSongs() {
        fetch('/api/downloads')
            .then(res => res.json())
            .then(data => {
                if (data) {
                    if (data.downloaded_songs) {
                        downloadCount.textContent = data.downloaded_songs.length;
                    }
                    
                    const recentTracksContainer = document.getElementById('recent-tracks');
                    if (recentTracksContainer && data.recent_tracks && data.recent_tracks.length > 0) {
                        recentTracksContainer.innerHTML = '';
                        
                        data.recent_tracks.forEach(track => {
                            const div = document.createElement('div');
                            div.className = 'recent-track d-flex align-items-center mb-2';
                            
                            const img = document.createElement('img');
                            img.src = track.image || 'https://www.svgrepo.com/svg/507644/disk';
                            img.alt = 'Album Cover';
                            img.className = 'recent-track-img me-2';
                            img.style.width = '40px';
                            img.style.height = '40px';
                            
                            const info = document.createElement('div');
                            info.className = 'recent-track-info';
                            
                            const title = document.createElement('div');
                            title.className = 'track-title small fw-bold';
                            title.textContent = track.name;
                            
                            const artist = document.createElement('div');
                            artist.className = 'track-artist small text-muted';
                            artist.textContent = track.artists;
                            
                            info.appendChild(title);
                            info.appendChild(artist);
                            
                            div.appendChild(img);
                            div.appendChild(info);
                            recentTracksContainer.appendChild(div);
                        });
                    } else if (recentTracksContainer) {
                        recentTracksContainer.innerHTML = '<div class="text-muted small">No recent downloads</div>';
                    }
                }
            })
            .catch(err => console.error('Error loading downloaded songs:', err));
    }

    setInterval(() => {
        if (!downloadStatus.running) {
            loadDownloadedSongs();
        }
    }, 30000);
});