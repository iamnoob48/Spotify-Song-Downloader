import os
import re
import yt_dlp
import spotipy
from flask import Flask, request, render_template, send_from_directory, jsonify, Response
from spotipy.oauth2 import SpotifyClientCredentials

# Initialize Flask app
app = Flask(__name__)

# Spotify API Credentials
CLIENT_ID = "6719b14874e540b89b7246528f1f056c"
CLIENT_SECRET = "497187857747433dbf26f346cc63e3b4"

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=CLIENT_ID, client_secret=CLIENT_SECRET))

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def get_playlist_tracks(playlist_id):
    results = sp.playlist_tracks(playlist_id)
    tracks = [f"{item['track']['name']} - {item['track']['artists'][0]['name']}" for item in results["items"]]
    return tracks

def get_youtube_link(song_name):
    ydl_opts = {'quiet': False, 'format': 'bestaudio', 'noplaylist': True}
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{song_name}", download=False)
            if 'entries' in info and len(info['entries']) > 0:
                youtube_url = info['entries'][0]['webpage_url']
                return youtube_url
            return None
        except Exception as e:
            print(f"Error finding YouTube link: {e}")
            return None

def download_audio(video_url, filename):
    safe_filename = re.sub(r'[\\/*?:"<>|]', '', filename)
    output_path = os.path.join(DOWNLOAD_FOLDER, f"{safe_filename}.mp3")

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }],
        'outtmpl': output_path,
        'quiet': False,  
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([video_url])
        except Exception as e:
            print(f"Error downloading {filename}: {e}")

    return safe_filename

def extract_playlist_id(playlist_url):
    """Extract Spotify playlist ID from URL."""
    match = re.search(r'playlist/([a-zA-Z0-9]+)', playlist_url)
    return match.group(1) if match else None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download')
def download():
    """Handle the download process and send progress updates via SSE."""
    playlist_url = request.args.get('playlist_url')
    playlist_id = extract_playlist_id(playlist_url)

    if not playlist_id:
        return "Invalid Spotify playlist URL!", 400

    tracks = get_playlist_tracks(playlist_id)
    if not tracks:
        return "No tracks found in the playlist!", 400

    # Start download process and stream progress updates
    def generate():
        total_songs = len(tracks)
        completed = 0

        for track in tracks:
            youtube_url = get_youtube_link(track)

            if youtube_url:
                download_audio(youtube_url, track)
                completed += 1
                progress = int((completed / total_songs) * 100)
                yield f"data: {progress}\n\n"  # Send progress update to the client

        yield "data: 100\n\n"  

    return Response(generate(), mimetype='text/event-stream')

@app.route('/downloads')
def list_downloads():
    """Return list of downloaded MP3 files."""
    files = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.endswith('.mp3')]
    return jsonify(files)

@app.route('/download/<filename>')
def download_file(filename):
    """Serve downloaded MP3 files."""
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host="127.0.0.1", port=5000)
