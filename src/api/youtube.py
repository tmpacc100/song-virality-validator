import datetime
import time
from typing import List, Optional, Dict, Any, Union
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.config import Config

class YouTubeClient:
    """Unified YouTube API Client with key rotation support."""
    
    def __init__(self):
        self.api_keys = Config.YOUTUBE_API_KEYS
        if not self.api_keys:
            raise ValueError("No YouTube API keys found in configuration.")
            
        self.current_key_index = 0
        self.service = self._build_service()
        self.request_count = 0
    
    def _build_service(self):
        """Builds the YouTube API service with the current key."""
        return build('youtube', 'v3', developerKey=self.api_keys[self.current_key_index])
    
    def _switch_api_key(self) -> bool:
        """Switch to the next available API key."""
        self.current_key_index += 1
        if self.current_key_index >= len(self.api_keys):
            print("⚠ All YouTube API keys exhausted.")
            return False
            
        print(f"🔑 Switching API Key ({self.current_key_index + 1}/{len(self.api_keys)})")
        try:
            self.service = self._build_service()
            return True
        except Exception as e:
            print(f"Failed to switch key: {e}")
            return False

    def execute_request(self, request_func, max_retries: int = 3) -> Optional[Any]:
        """Execute an API request with automatic retry and key rotation."""
        for attempt in range(max_retries):
            try:
                response = request_func().execute()
                self.request_count += 1
                return response
            except HttpError as e:
                if e.resp.status == 403 and 'quota' in str(e).lower():
                    print(f"⚠ Quota exceeded for key {self.current_key_index + 1}.")
                    if self._switch_api_key():
                        # Retry immediately with new key
                        continue 
                    else:
                        raise e # Propagate if no keys left
                
                if e.resp.status == 429 or (e.resp.status == 403 and 'rateLimit' in str(e).lower()):
                    sleep_time = 2 ** attempt
                    print(f"⏳ Rate limited. Sleeping for {sleep_time}s...")
                    time.sleep(sleep_time)
                    continue
                    
                print(f"❌ API Error: {e}")
                if attempt == max_retries - 1:
                    return None
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(1)
        return None

    def search_video(self, query: str, max_results: int = 5) -> Optional[Dict]:
        """Search for a video by query."""
        request = lambda: self.service.search().list(
            q=query,
            part='id,snippet',
            maxResults=max_results,
            type='video'
        )
        response = self.execute_request(request)
        if response and response.get('items'):
            return response['items'][0]
        return None

    def get_video_details(self, video_id: str) -> Optional[Dict]:
        """Get detailed statistics for a video."""
        request = lambda: self.service.videos().list(
            id=video_id,
            part='statistics,snippet,contentDetails,status'
        )
        response = self.execute_request(request)
        if response and response.get('items'):
            return response['items'][0]
        return None

    def get_channel_details(self, channel_id: str) -> Optional[Dict]:
        """Get detailed statistics for a channel."""
        request = lambda: self.service.channels().list(
            id=channel_id,
            part='statistics,snippet,contentDetails'
        )
        response = self.execute_request(request)
        if response and response.get('items'):
            return response['items'][0]
        return None
