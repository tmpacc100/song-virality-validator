import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_youtube_service():
    mock = MagicMock()
    return mock

@pytest.fixture
def mock_requests_get():
    mock = MagicMock()
    return mock
