import os
from flask import Flask, request, redirect, session, render_template
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import datetime
import numpy as np
from collections import Counter

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace this with a real secret key
app.config['SESSION_COOKIE_NAME'] = 'spotify-login-session'

SPOTIPY_CLIENT_ID = ''
SPOTIPY_CLIENT_SECRET = ''
SPOTIPY_REDIRECT_URI = 'http://localhost:8000/callback'
SCOPE = 'user-top-read user-read-recently-played'

@app.route('/')
def index():
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    sp_oauth = create_spotify_oauth()
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info
    return redirect("/analyze")

@app.route('/analyze')
def analyze():
    session['token_info'], authorized = get_token()
    session.modified = True
    if not authorized:
        return redirect('/')
    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
    
    # Get user's top artists
    top_artists = sp.current_user_top_artists(limit=5, time_range='medium_term')
    
    # Get user's recently played tracks
    recent_tracks = sp.current_user_recently_played(limit=50)
    
    # Analyze the data
    analytics = analyze_data(sp, top_artists, recent_tracks)
    
    return render_template('index.html', analytics=analytics)

def analyze_data(sp, top_artists, recent_tracks):
    # Analyze top artists
    artist_data = []
    for artist in top_artists['items']:
        artist_info = {
            'name': artist['name'],
            'popularity': artist['popularity'],
            'genres': artist['genres'],
            'image_url': artist['images'][0]['url'] if artist['images'] else None
        }
        artist_data.append(artist_info)
    
    # Analyze recent tracks
    track_data = []
    total_listen_time_ms = 0
    for item in recent_tracks['items']:
        track = item['track']
        played_at = datetime.datetime.strptime(item['played_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
        track_info = {
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'album': track['album']['name'],
            'duration_ms': track['duration_ms'],
            'played_at': played_at
        }
        track_data.append(track_info)
        total_listen_time_ms += track['duration_ms']
    
    # Calculate listening stats
    total_listen_time_hours = total_listen_time_ms / (1000 * 60 * 60)
    avg_track_duration_min = np.mean([track['duration_ms'] for track in track_data]) / (1000 * 60)
    
    # Get user's audio features preferences
    track_ids = [item['track']['id'] for item in recent_tracks['items']]
    audio_features = sp.audio_features(track_ids)
    avg_audio_features = {
        'danceability': np.mean([feat['danceability'] for feat in audio_features if feat]),
        'energy': np.mean([feat['energy'] for feat in audio_features if feat]),
        'valence': np.mean([feat['valence'] for feat in audio_features if feat])
    }
    
    return {
        'top_artists': artist_data,
        'recent_tracks': track_data,
        'total_listen_time_hours': round(total_listen_time_hours, 2),
        'avg_track_duration_min': round(avg_track_duration_min, 2),
        'avg_audio_features': avg_audio_features
    }

def create_spotify_oauth():
    return SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=SCOPE)

def get_token():
    token_valid = False
    token_info = session.get("token_info", {})

    if not (session.get('token_info', False)):
        token_valid = False
        return token_info, token_valid

    now = int(time.time())
    is_token_expired = session.get('token_info').get('expires_at') - now < 60

    if (is_token_expired):
        sp_oauth = create_spotify_oauth()
        token_info = sp_oauth.refresh_access_token(session.get('token_info').get('refresh_token'))

    token_valid = True
    return token_info, token_valid

if __name__ == '__main__':
    app.run(debug=True, port=8000)
