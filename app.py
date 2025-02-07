import os
import re
import yt_dlp
import spotipy
from flask import Flask, request, render_template, send_from_directory
from spotipy.oauth2 import SpotifyClientCredentials

app = Flask(__name__)

# Spotify API Credentials
CLIENT_ID = "6719b14874e540b89b7246528f1f056c"
CLIENT_SECRET = "497187857747433dbf26f346cc63e3b4"

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=CLIENT_ID, client_secret=CLIENT_SECRET))

# Set a fixed download folder
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def get_playlist_tracks(playlist_id):
    """Fetch track names from Spotify playlist."""
    results = sp.playlist_tracks(playlist_id)
    tracks = []

    for item in results["items"]:
        track = item["track"]
        track_name = f"{track['name']} - {track['artists'][0]['name']}"
        tracks.append(track_name)

    return tracks

def get_youtube_link(song_name):
    """Finds a YouTube link for the song."""
    ydl_opts = {'quiet': True, 'format': 'bestaudio', 'noplaylist': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{song_name}", download=False)
        return info['entries'][0]['webpage_url'] if 'entries' in info else None

def download_audio(video_url, filename):
    """Downloads audio from YouTube as MP3."""
    safe_filename = re.sub(r'[\\/*?:"<>|]', '', filename)  # Remove invalid characters
    output_path = os.path.join(DOWNLOAD_FOLDER, f"{safe_filename}.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }],
        'outtmpl': output_path,  # Enforce correct filename
        'quiet': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    return os.path.join(DOWNLOAD_FOLDER, f"{safe_filename}.mp3") 

def extract_playlist_id(playlist_url):
    """Extracts the Spotify Playlist ID from the URL."""
    match = re.search(r'playlist/([a-zA-Z0-9]+)', playlist_url)
    return match.group(1) if match else None

@app.route('/', methods=['GET', 'POST'])
def index():
    """Handles downloading Spotify playlist as MP3."""
    if request.method == 'POST':
        playlist_input = request.form['playlist_url']
        playlist_id = extract_playlist_id(playlist_input)

        if not playlist_id:
            return "Invalid Spotify playlist URL!"

        # Get Spotify tracks
        tracks = get_playlist_tracks(playlist_id)
        downloaded_files = []

        for track in tracks:
            youtube_url = get_youtube_link(track)
            if youtube_url:
                file_path = download_audio(youtube_url, track)
                downloaded_files.append(file_path)

        return render_template('index.html', files=downloaded_files)

    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    """Allows users to download MP3 files from the website."""
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)