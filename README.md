# Spotify Data Analytics Dashboard

<img width="1171" alt="Spotify Dashboard Overview" src="https://github.com/user-attachments/assets/34aa7362-55cd-4864-96c5-82009dd85338">

This web application allows you to visualize your top Spotify artists, tracks, and recently played tracks over the past 6 months in addition to recommending you new songs and automatically creating new playlists based on your activity. It leverages the Spotify API to gather data, which is then presented in a user-friendly web interface.

## Features

- **Top Artists**: Displays your top 10 artists over the past 6 months, including their popularity and genres.
- **Top Tracks**: Lists your top 10 tracks over the past 6 months, including track popularity and album name.
- **Recently Played Tracks**: Retrieves all your recently played tracks (up to the last 90 days) and analyzes them to provide insights.
- **Song Recommendations**: Recommends new songs based on your listening history.
- **Automatic Playlist Creation**: Creates new playlists based on your top tracks and recommendations.

## Prerequisites

- Python 3.x
- Spotify Developer Account (for API credentials)

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/spotify-season-summary.git
   cd spotify-season-summary
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   Create a `.env` file in the root of your project and add your Spotify API credentials:
   ```
   SPOTIPY_CLIENT_ID=your_spotify_client_id
   SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
   SPOTIPY_REDIRECT_URI=http://localhost:8000/callback
   ```

4. **Run the Flask application**:
   ```bash
   python main.py
   ```

5. **Access the application**:
   Open your browser and navigate to `http://localhost:8000`.

## File Structure

- **main.py**: The main Flask application file that handles routing, data retrieval, and analysis.
- **templates/index.html**: The HTML template for rendering the user's Spotify data.
- **static/styles.css**: The stylesheet to style the application interface.

## Screenshots

<img width="1185" alt="Screen Shot 2024-08-12 at 11 07 14 PM" src="https://github.com/user-attachments/assets/34f3354d-51e6-44df-9922-825859a7bb81">


<img width="705" alt="Spotify Top Tracks" src="https://github.com/user-attachments/assets/f7825ce5-7893-44c1-8dda-f09f3e3004b3">

## How It Works

1. **Authentication**: Users are authenticated with Spotify using OAuth2.0.
2. **Data Retrieval**: The app retrieves the user's top artists, top tracks, and recently played tracks (up to the last 90 days).
3. **Data Analysis**: The app analyzes the retrieved data to determine the most popular tracks and artists based on stream counts and popularity.
4. **Recommendations**: The app generates song recommendations based on the user's top tracks.
5. **Playlist Creation**: A new playlist is created with the user's top tracks and recommended songs.
6. **Visualization**: The analyzed data is presented to the user in a clean and organized web interface.

## Customization

- **Styles**: You can customize the appearance of the app by modifying the `styles.css` file.
- **Templates**: Modify `index.html` to change the structure or presentation of the data.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Flask](https://flask.palletsprojects.com/)
- [Spotipy](https://spotipy.readthedocs.io/)
- [Spotify API](https://developer.spotify.com/documentation/web-api/)
