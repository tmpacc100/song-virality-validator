import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Tuple, Any
from src.config import Config

class GameServerClient:
    """Client for fetching data from game servers."""
    
    def __init__(self):
        self.user = Config.GAME_SERVER_USER
        self.password = Config.GAME_SERVER_PASSWORD
        self.taiko_url = 'https://taikogame-server.herokuapp.com/songs'
        self.piano_url = 'https://pianogame-server.herokuapp.com/notifications'
        
    def fetch_taiko_songs(self) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
        """Fetch songs from TaikoGame server."""
        if not self.user or not self.password:
            print("⚠ Skipping Game Server fetch: Credentials missing.")
            return {}, []
            
        try:
            print("Fetching data from TaikoGame server...")
            response = requests.get(self.taiko_url, auth=(self.user, self.password))
            if response.status_code != 200:
                print(f"⚠ Server access failed: {response.status_code}")
                return {}, []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table')
            if not table:
                return {}, []

            artists_dict = {}
            songs_list = []
            
            rows = table.find_all('tr')[1:] # Skip header
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 12:
                    # Extract logic mirroring original main.py
                    title_text = cols[2].get_text(separator='\n')
                    lines = [line.strip() for line in title_text.split('\n') if line.strip()]
                    
                    song_name = lines[0] if len(lines) >= 1 else ''
                    artist_name = lines[1] if len(lines) >= 2 else ''
                    
                    if song_name and artist_name:
                        artists_dict[song_name] = artist_name
                        
                    songs_list.append({
                        'id': cols[0].get_text(strip=True),
                        'title': title_text.replace('\n', ' '),
                        'song_name': song_name,
                        'artist_name': artist_name,
                        'youtube': cols[9].get_text(strip=True),
                        'release_date': cols[1].get_text(strip=True)
                    })
            
            print(f"✓ Fetched {len(songs_list)} songs from TaikoGame.")
            return artists_dict, songs_list
            
        except Exception as e:
            print(f"⚠ Failed to fetch from TaikoGame: {e}")
            return {}, []
