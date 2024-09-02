import os
from flask import Flask, request, redirect, session, render_template, jsonify
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
from collections import Counter, defaultdict
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server-side plotting
import matplotlib.pyplot as plt
import io
import base64
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from flask_caching import Cache
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace this with a real secret key
app.config['SESSION_COOKIE_NAME'] = 'spotify-login-session'

# Setup caching
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Setup thread pool for async processing
executor = ThreadPoolExecutor(max_workers=3)

SPOTIPY_CLIENT_ID = '5f07fc9c17594557b51376250950342b'
SPOTIPY_CLIENT_SECRET = '6bce146d812142c2a9f345c7d476e72f'
SPOTIPY_REDIRECT_URI = 'http://localhost:8000/callback'
SCOPE = 'user-top-read user-read-recently-played playlist-modify-private'

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
@cache.cached(timeout=3600)  # Cache for 1 hour
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
    
    # Get recommendations based on top 5 tracks
    top_5_track_ids = [track['id'] for track in top_tracks['items'][:5]]
    recommendations = sp.recommendations(seed_tracks=top_5_track_ids, limit=5)
    
    # Create a playlist with top 5 tracks and 5 recommendations
    playlist = {
        'name': "Your Top Tracks + Recommendations",
        'url': None  # We'll generate this URL when the user clicks the button
    }
    
    # Run heavy computations asynchronously
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_listening_habits = executor.submit(analyze_listening_habits, recent_tracks)
        future_listening_trends = executor.submit(analyze_listening_trends, sp, recent_tracks, top_artists)
        future_seasonal_data = executor.submit(analyze_seasonal_data, top_artists, top_tracks, recent_tracks, recommendations, playlist)
        
        # Wait for all computations to complete
        listening_time_plot, date_range_data = future_listening_habits.result()
        listening_trends = future_listening_trends.result()
        analytics = future_seasonal_data.result()
    
    # Combine data
    analytics['listening_time_plot'] = listening_time_plot
    analytics['listening_trends'] = listening_trends
    analytics['date_range_data'] = date_range_data or []
    
    return render_template('index.html', analytics=analytics)

@app.route('/create-playlist', methods=['POST'])
def create_playlist_route():
    session['token_info'], authorized = get_token()
    if not authorized:
        return jsonify({'error': 'Not authorized'}), 401
    
    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
    
    # Get top tracks and recommendations
    top_tracks = sp.current_user_top_tracks(limit=20, time_range='medium_term')
    top_track_ids = [track['id'] for track in top_tracks['items']]
    recommendations = sp.recommendations(seed_tracks=top_track_ids[:5], limit=30)
    recommended_track_ids = [track['id'] for track in recommendations['tracks']]
    
    # Create the playlist
    playlist = create_playlist(sp, top_track_ids, recommended_track_ids)
    
    return jsonify(playlist)

def create_playlist(sp, top_track_ids, recommended_track_ids):
    user_id = sp.me()['id']
    playlist_name = "Your Top 20 + 30 Recommendations"
    
    # Delete existing playlists with the same name
    delete_existing_playlists(sp, playlist_name)
    
    # Create new playlist
    playlist = sp.user_playlist_create(user_id, playlist_name, public=False)
    
    tracks_to_add = top_track_ids + recommended_track_ids
    sp.user_playlist_add_tracks(user_id, playlist['id'], tracks_to_add)
    
    return {
        'name': playlist['name'],
        'url': playlist['external_urls']['spotify'],
    }

def get_all_recently_played_tracks(sp, limit=50):
    all_tracks = []
    last_timestamp = None

    while True:
        if last_timestamp:
            recent_tracks = sp.current_user_recently_played(limit=limit, after=last_timestamp)
        else:
            recent_tracks = sp.current_user_recently_played(limit=limit)

        all_tracks.extend(recent_tracks['items'])

        if len(recent_tracks['items']) < limit:
            break

        last_timestamp = recent_tracks['items'][-1]['played_at']

    return all_tracks

def analyze_seasonal_data(top_artists, top_tracks, recent_tracks, recommendations, playlist):
    artist_data = []
    track_data = []
    artist_stream_count = Counter()
    artist_top_track = defaultdict(lambda: {'name': 'Not available', 'popularity': 0})
    total_popularity = 0

    for item in recent_tracks:
        track = item['track']
        artist_names = [artist['name'] for artist in track['artists']]
        
        for artist_name in artist_names:
            artist_stream_count[artist_name] += 1
            if track['popularity'] > artist_top_track[artist_name]['popularity']:
                artist_top_track[artist_name] = {'name': track['name'], 'popularity': track['popularity']}
    
    for artist in top_artists['items']:
        artist_name = artist['name']
        
        artist_info = {
            'name': artist_name,
            'popularity': artist['popularity'],
            'genres': artist['genres'],
            'image_url': artist['images'][0]['url'] if artist['images'] else None,
            'streams': max(artist_stream_count.get(artist_name, 0), 1),
            'most_popular_track': artist_top_track[artist_name]['name']
        }
        artist_data.append(artist_info)
    
    artist_data.sort(key=lambda x: x['streams'], reverse=True)
    
    for track in top_tracks['items']:
        track_info = {
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'album': track['album']['name'],
            'popularity': track['popularity'],
        }
        track_data.append(track_info)
        total_popularity += track['popularity']
    
    average_popularity = total_popularity / len(top_tracks['items']) if top_tracks['items'] else 0
    
    recommended_tracks = []
    for track in recommendations['tracks']:
        track_info = {
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'album': track['album']['name'],
            'popularity': track['popularity'],
        }
        recommended_tracks.append(track_info)
    
    return {
        'top_artists': artist_data,
        'top_tracks': track_data,
        'recommended_tracks': recommended_tracks,
        'playlist': playlist,
        'average_popularity': average_popularity,
    }

def analyze_listening_habits(recent_tracks):
    timestamps = [track['played_at'] for track in recent_tracks]
    track_names = [track['track']['name'] for track in recent_tracks]
    
    timestamps = pd.to_datetime(timestamps, format='mixed', utc=True)

    df = pd.DataFrame({'timestamp': timestamps, 'track': track_names})

    df['date'] = df['timestamp'].dt.date
    df['hour'] = df['timestamp'].dt.hour

    hourly_counts = df.groupby('hour').size().reset_index(name='count')

    plt.style.use('dark_background')
    
    fig = plt.figure(figsize=(12, 6), facecolor='#121212')
    ax = fig.add_subplot(111)
    
    ax.plot(hourly_counts['hour'], hourly_counts['count'], color='#1DB954', linewidth=2, marker='o', markersize=6)
    ax.fill_between(hourly_counts['hour'], hourly_counts['count'], color='#1DB954', alpha=0.2)

    ax.set_facecolor('#181818')
    ax.set_xlabel('Hour of the Day', fontsize=12, color='#FFFFFF')
    ax.set_ylabel('Number of Tracks Played', fontsize=12, color='#FFFFFF')
    ax.set_title('Hourly Listening Habits of the Day', fontsize=16, color='#1DB954')
    ax.set_xticks(range(24))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(24)], rotation=45, ha='right')
    ax.tick_params(colors='#FFFFFF')

    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format="png", facecolor='#121212', edgecolor='none', bbox_inches='tight')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    
    date_range_data = df.groupby(['date', 'hour']).size().reset_index(name='count')
    date_range_data['date'] = date_range_data['date'].astype(str)
    date_range_data = date_range_data.to_dict(orient='records')
    
    return img_str, date_range_data

def analyze_listening_trends(sp, recent_tracks, top_artists):
    top_genres = [genre for artist in top_artists['items'] for genre in artist['genres']]
    genre_counts = Counter(top_genres)
    
    track_ids = [track['track']['id'] for track in recent_tracks]
    audio_features = sp.audio_features(track_ids)
    
    df = pd.DataFrame(audio_features)
    df['played_at'] = [track['played_at'] for track in recent_tracks]
    
    df['played_at'] = pd.to_datetime(df['played_at'], format='ISO8601')
    df = df.sort_values('played_at')
    
    feature_trends = {}
    for feature in ['danceability', 'energy', 'valence']:
        trend = df[feature].rolling(window=10).mean().iloc[-1] - df[feature].rolling(window=10).mean().iloc[0]
        feature_trends[feature] = trend
    
    recent_genres = [genre for track in recent_tracks for genre in sp.artist(track['track']['artists'][0]['id'])['genres']]
    recent_genre_counts = Counter(recent_genres)
    emerging_genres = [genre for genre, count in recent_genre_counts.items() if genre not in genre_counts]
    
    recommendations = []
    if feature_trends['energy'] > 0:
        recommendations.append("You've been listening to more energetic music lately. Try out some upbeat dance or rock tracks!")
    if feature_trends['valence'] < 0:
        recommendations.append("Your music choices have been a bit more melancholic recently. How about some uplifting pop or feel-good indie tracks?")
    if emerging_genres:
        recommendations.append(f"You're exploring new genres like {', '.join(emerging_genres[:3])}. Keep discovering with similar artists in these genres!")
    
    potential_new_favorite = "Based on your recent listening, you might enjoy exploring more music by [Artist Name]"
    
    return {
        'top_genres': dict(genre_counts.most_common(5)),
        'feature_trends': feature_trends,
        'emerging_genres': emerging_genres[:5],
        'recommendations': recommendations,
        'potential_new_favorite': potential_new_favorite
    }

def delete_existing_playlists(sp, playlist_name):
    user_id = sp.me()['id']
    playlists = sp.user_playlists(user_id)
    
    while playlists:
        for playlist in playlists['items']:
            if playlist['name'] == playlist_name and playlist['owner']['id'] == user_id:
                sp.user_playlist_unfollow(user_id, playlist['id'])
                print(f"Deleted playlist: {playlist['name']}")
        
        if playlists['next']:
            playlists = sp.next(playlists)
        else:
            playlists = None

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
