from unittest.mock import patch, MagicMock
from src.api.youtube import YouTubeClient

@patch('src.api.youtube.build')
@patch('src.config.Config.YOUTUBE_API_KEYS', ['key1', 'key2'])
def test_youtube_client_init(mock_build):
    client = YouTubeClient()
    assert client.current_key_index == 0
    mock_build.assert_called_with('youtube', 'v3', developerKey='key1')

@patch('src.api.youtube.build')
@patch('src.config.Config.YOUTUBE_API_KEYS', ['key1', 'key2'])
def test_key_rotation(mock_build):
    client = YouTubeClient()
    
    # Simulate switch
    success = client._switch_api_key()
    
    assert success is True
    assert client.current_key_index == 1
    mock_build.assert_called_with('youtube', 'v3', developerKey='key2')

@patch('src.api.youtube.build')
@patch('src.config.Config.YOUTUBE_API_KEYS', ['key1'])
def test_key_exhaustion(mock_build):
    client = YouTubeClient()
    assert client._switch_api_key() is False # Index becomes 1, len is 1 -> Fail
