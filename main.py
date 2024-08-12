import os
from flask import Flask, request, redirect, session, render_template
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
from collections import Counter, defaultdict

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
    return redirect("/season-summary")

@app.route('/season-summary')
def season_summary():
    session['token_info'], authorized = get_token()
    session.modified = True
    if not authorized:
        return redirect('/')
    
    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
    
    # Get user's top artists and tracks for medium term (approx. 6 months)
    top_artists = sp.current_user_top_artists(limit=10, time_range='medium_term')
    top_tracks = sp.current_user_top_tracks(limit=10, time_range='medium_term')
    
    # Get all user's recently played tracks (limited to last 90 days)
    recent_tracks = get_all_recently_played_tracks(sp)
    
    # Combine and analyze data
    analytics = analyze_seasonal_data(top_artists, top_tracks, recent_tracks)
    
    return render_template('index.html', analytics=analytics)

def get_all_recently_played_tracks(sp, limit=50):
    all_tracks = []
    last_timestamp = None

    while True:
        if last_timestamp:
            recent_tracks = sp.current_user_recently_played(limit=limit, after=last_timestamp)
        else:
            recent_tracks = sp.current_user_recently_played(limit=limit)

        all_tracks.extend(recent_tracks['items'])

        # Break if fewer tracks are returned than the limit, indicating no more tracks
        if len(recent_tracks['items']) < limit:
            break

        # Set the last timestamp to the played_at time of the last track in the current batch
        last_timestamp = recent_tracks['items'][-1]['played_at']

    return all_tracks

def analyze_seasonal_data(top_artists, top_tracks, recent_tracks):
    # Analyze top artists and top tracks
    artist_data = []
    track_data = []
    artist_stream_count = Counter()
    artist_top_track = defaultdict(lambda: {'name': '', 'popularity': 0})

    # Count streams and find most popular track per artist in recent tracks
    for item in recent_tracks:
        track = item['track']
        artist_names = [artist['name'] for artist in track['artists']]
        
        for artist_name in artist_names:
            artist_stream_count[artist_name] += 1
            if track['popularity'] > artist_top_track[artist_name]['popularity']:
                artist_top_track[artist_name] = {'name': track['name'], 'popularity': track['popularity']}
    
    # Prepare artist data with the number of streams and most popular track
    for artist in top_artists['items']:
        artist_name = artist['name']
        artist_info = {
            'name': artist_name,
            'popularity': artist['popularity'],
            'genres': artist['genres'],
            'image_url': artist['images'][0]['url'] if artist['images'] else None,
            'streams': artist_stream_count.get(artist_name, 0),
            'most_popular_track': artist_top_track[artist_name]['name']
        }
        artist_data.append(artist_info)
    
    # Rank artists by stream count
    artist_data.sort(key=lambda x: x['streams'], reverse=True)
    
    # Prepare top track data and rank by popularity
    for track in top_tracks['items']:
        track_info = {
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'album': track['album']['name'],
            'popularity': track['popularity'],
        }
        track_data.append(track_info)
    
    # Rank tracks by popularity
    track_data.sort(key=lambda x: x['popularity'], reverse=True)
    
    return {
        'top_artists': artist_data,
        'top_tracks': track_data,  # Ensure top tracks are included in the output
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
