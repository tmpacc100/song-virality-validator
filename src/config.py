import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # YouTube API
    YOUTUBE_API_KEYS = [
        key.strip() 
        for key in os.getenv('YOUTUBE_API_KEYS', '').split(',') 
        if key.strip()
    ]
    
    # Game Server
    GAME_SERVER_USER = os.getenv('GAME_SERVER_USER')
    GAME_SERVER_PASSWORD = os.getenv('GAME_SERVER_PASSWORD')
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CACHE_DIR = os.path.join(BASE_DIR, 'RAW DATA')
    OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
    
    @classmethod
    def validate(cls):
        if not cls.YOUTUBE_API_KEYS:
            raise ValueError("Environment variable YOUTUBE_API_KEYS is missing or empty.")
        if not cls.GAME_SERVER_USER or not cls.GAME_SERVER_PASSWORD:
            print("Warning: Game server credentials (GAME_SERVER_USER/PASSWORD) are missing.")

# Validate on import (optional, or call explicitly)
# Config.validate()
