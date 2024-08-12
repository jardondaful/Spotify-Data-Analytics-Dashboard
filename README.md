# Spotify Analysis Project

This project is a web application that provides users with insights into their Spotify listening habits. It uses the Spotify API to fetch user data and presents it in an easy-to-understand format.

![Spotify Analysis Dashboard](https://github.com/user-attachments/assets/ae9e2ab1-6f97-4df3-861c-e03ecdd7d9e3)

## Features

- Display of top artists
- Recent listening history
- Total listening time analysis
- Average track duration calculation
- Audio features analysis (danceability, energy, valence)
- Interactive radar chart for audio preferences

## Prerequisites

Before you begin, ensure you have met the following requirements:

- Python 3.7 or higher
- A Spotify Developer account and registered application
- Flask
- Spotipy
- NumPy

## Setup

1. Clone this repository to your local machine.

2. Install the required Python packages:
   ```
   pip install flask spotipy numpy
   ```

3. Set up your Spotify Developer account and create a new application at https://developer.spotify.com/dashboard/

4. In your Spotify Developer Dashboard, set the Redirect URI to `http://localhost:8000/callback`

5. Copy your Client ID and Client Secret from the Spotify Developer Dashboard.

6. Open `app.py` and replace the placeholder values with your actual Spotify API credentials:
   ```python
   SPOTIPY_CLIENT_ID = 'your_client_id_here'
   SPOTIPY_CLIENT_SECRET = 'your_client_secret_here'
   ```

7. Replace the `app.secret_key` with a secure random string:
   ```python
   app.secret_key = 'your_secret_key_here'
   ```

## Running the Application

1. Navigate to the project directory in your terminal.

2. Run the Flask application:
   ```
   python app.py
   ```

3. Open a web browser and go to `http://localhost:8000`

4. You will be redirected to Spotify to log in and authorize the application.

5. After authorization, you will be redirected back to the application where you can view your Spotify insights.

## Project Structure

- `app.py`: The main Flask application
- `templates/index.html`: HTML template for the dashboard
- `static/styles.css`: CSS styles for the dashboard

## Contributing

Contributions to this project are welcome. Please fork the repository and create a pull request with your changes.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Spotify for providing the API
- Flask and Spotipy for making web development and Spotify API integration easy
