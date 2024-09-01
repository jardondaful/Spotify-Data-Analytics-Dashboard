# Updated imports
import os
from flask import Flask, request, redirect, session, render_template
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

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace this with a real secret key
app.config['SESSION_COOKIE_NAME'] = 'spotify-login-session'

SPOTIPY_CLIENT_ID = ''
SPOTIPY_CLIENT_SECRET = ''
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
    
    # Get recommendations based on top 5 tracks
    top_5_track_ids = [track['id'] for track in top_tracks['items'][:5]]
    recommendations = sp.recommendations(seed_tracks=top_5_track_ids, limit=5)
    
    # Create a playlist with top 5 tracks and 5 recommendations
    playlist = create_playlist(sp, top_5_track_ids, [track['id'] for track in recommendations['tracks']])
    
    # Analyze listening habits over time
    listening_time_plot, date_range_data = analyze_listening_habits(recent_tracks)
    
    # Analyze listening trends
    listening_trends = analyze_listening_trends(sp, recent_tracks, top_artists)
    
    # Combine and analyze data
    analytics = analyze_seasonal_data(top_artists, top_tracks, recent_tracks, recommendations, playlist)
    analytics['listening_time_plot'] = listening_time_plot  # Add the listening habits plot
    analytics['listening_trends'] = listening_trends  # Add the listening trends analysis
    analytics['date_range_data'] = date_range_data or []  # Ensure date_range_data is a list
    
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

def analyze_seasonal_data(top_artists, top_tracks, recent_tracks, recommendations, playlist):
    artist_data = []
    track_data = []
    artist_stream_count = Counter()
    artist_top_track = defaultdict(lambda: {'name': 'Not available', 'popularity': 0})
    total_popularity = 0

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
            'streams': max(artist_stream_count.get(artist_name, 0), 1),  # Ensure at least 1 stream
            'most_popular_track': artist_top_track[artist_name]['name']
        }
        artist_data.append(artist_info)
    
    # Rank artists by stream count
    artist_data.sort(key=lambda x: x['streams'], reverse=True)
    
    # Prepare top track data and calculate total popularity
    for track in top_tracks['items']:
        track_info = {
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'album': track['album']['name'],
            'popularity': track['popularity'],
        }
        track_data.append(track_info)
        total_popularity += track['popularity']
    
    # Calculate average popularity
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
    # Extract played_at timestamps and track information
    timestamps = [track['played_at'] for track in recent_tracks]
    track_names = [track['track']['name'] for track in recent_tracks]
    
    # Convert to datetime using a more flexible approach
    timestamps = pd.to_datetime(timestamps, format='mixed', utc=True)

    # Create dataframe with timestamps and track names
    df = pd.DataFrame({'timestamp': timestamps, 'track': track_names})

    # Extract date and hour
    df['date'] = df['timestamp'].dt.date
    df['hour'] = df['timestamp'].dt.hour

    # Count tracks by hour of the day
    hourly_counts = df.groupby('hour').size().reset_index(name='count')

    # Set the style
    plt.style.use('dark_background')
    
    # Create a new figure for the hourly listening habits
    fig, ax = plt.subplots(figsize=(12, 6), facecolor='#121212')
    
    # Plot: Hourly Listening Habits (line chart)
    ax.plot(hourly_counts['hour'], hourly_counts['count'], color='#1DB954', linewidth=2, marker='o', markersize=6)
    ax.fill_between(hourly_counts['hour'], hourly_counts['count'], color='#1DB954', alpha=0.2)

    # Customize the plot
    ax.set_facecolor('#181818')
    ax.set_xlabel('Hour of the Day', fontsize=12, color='#FFFFFF')
    ax.set_ylabel('Number of Tracks Played', fontsize=12, color='#FFFFFF')
    ax.set_title('Hourly Listening Habits of the Day', fontsize=16, color='#1DB954')
    ax.set_xticks(range(24))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(24)], rotation=45, ha='right')
    ax.tick_params(colors='#FFFFFF')

    # Adjust layout and save
    plt.tight_layout()
    
    # Save plot to a PNG image and encode it in base64
    buf = io.BytesIO()
    plt.savefig(buf, format="png", facecolor='#121212', edgecolor='none', bbox_inches='tight')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    
    # Prepare data for interactive chart
    date_range_data = df.groupby(['date', 'hour']).size().reset_index(name='count')
    date_range_data['date'] = date_range_data['date'].astype(str)
    date_range_data = date_range_data.to_dict(orient='records')
    
    return img_str, date_range_data




def analyze_listening_trends(sp, recent_tracks, top_artists):
    # Extract genres from top artists
    top_genres = [genre for artist in top_artists['items'] for genre in artist['genres']]
    genre_counts = Counter(top_genres)
    
    # Get track features for recent tracks
    track_ids = [track['track']['id'] for track in recent_tracks]
    audio_features = sp.audio_features(track_ids)
    
    # Create a DataFrame with track features
    df = pd.DataFrame(audio_features)
    df['played_at'] = [track['played_at'] for track in recent_tracks]
    
    # Parse the 'played_at' column using a more flexible approach
    df['played_at'] = pd.to_datetime(df['played_at'], format='ISO8601')
    df = df.sort_values('played_at')
    
    # Analyze trends in audio features
    feature_trends = {}
    for feature in ['danceability', 'energy', 'valence']:
        trend = df[feature].rolling(window=10).mean().iloc[-1] - df[feature].rolling(window=10).mean().iloc[0]
        feature_trends[feature] = trend
    
    # Identify emerging genres (genres in recent tracks not in top genres)
    recent_genres = [genre for track in recent_tracks for genre in sp.artist(track['track']['artists'][0]['id'])['genres']]
    recent_genre_counts = Counter(recent_genres)
    emerging_genres = [genre for genre, count in recent_genre_counts.items() if genre not in genre_counts]
    
    # Generate recommendations based on trends
    recommendations = []
    if feature_trends['energy'] > 0:
        recommendations.append("You've been listening to more energetic music lately. Try out some upbeat dance or rock tracks!")
    if feature_trends['valence'] < 0:
        recommendations.append("Your music choices have been a bit more melancholic recently. How about some uplifting pop or feel-good indie tracks?")
    if emerging_genres:
        recommendations.append(f"You're exploring new genres like {', '.join(emerging_genres[:3])}. Keep discovering with similar artists in these genres!")
    
    # Find potential new favorite artist (simplified for this example)
    potential_new_favorite = "Based on your recent listening, you might enjoy exploring more music by [Artist Name]"
    
    return {
        'top_genres': dict(genre_counts.most_common(5)),
        'feature_trends': feature_trends,
        'emerging_genres': emerging_genres[:5],
        'recommendations': recommendations,
        'potential_new_favorite': potential_new_favorite
    }

def create_playlist(sp, top_track_ids, recommended_track_ids):
    user_id = sp.me()['id']
    playlist = sp.user_playlist_create(user_id, "Your Top Tracks + Recommendations", public=False)
    
    tracks_to_add = top_track_ids + recommended_track_ids
    sp.user_playlist_add_tracks(user_id, playlist['id'], tracks_to_add)
    
    return {
        'name': playlist['name'],
        'url': playlist['external_urls']['spotify'],
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
