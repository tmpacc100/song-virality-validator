import re
from typing import Optional

def extract_artist_from_title(video_title: str) -> Optional[str]:
    """Extract artist name from video title using heuristic patterns."""
    if not video_title:
        return None

    # Pattern 1: 【artist】
    match = re.search(r'【(.+?)】', video_title)
    if match:
        artist = match.group(1).strip()
        # Removed 'Official' from noise words as it matches bands like Official髭男dism
        noise_words = ['第', '回', '歌合戦', 'NHK', '紅白', 'MV', 'MUSIC', 'オリジナル楽曲', '歌唱曲']
        if not any(noise in artist for noise in noise_words):
            return artist

    # Pattern 2: artist｢song｣ or artist「song」
    match = re.match(r'^([^\｢「]+)[｢「]', video_title)
    if match:
        return match.group(1).strip()

    # Pattern 3: artist - song
    match = re.match(r'^(.+?)\s*[-−ー]\s*', video_title)
    if match:
        return match.group(1).strip()

    # Pattern 4: / artist :
    match = re.search(r'/\s*(.+?)[:：]', video_title)
    if match:
        return match.group(1).strip()

    # Pattern 5: / artist (End of string)
    match = re.search(r'/\s*(.+?)$', video_title)
    if match:
        artist = match.group(1).strip()
        artist = re.sub(r'\s*(MUSIC\s+VIDEO|MV|Official.*|[\(\（].*?[\)\）]).*$', '', artist, flags=re.IGNORECASE)
        return artist.strip() if artist else None

    # Pattern 6: artist 'song'
    match = re.match(r'^(.+?)\s+[\'""'']', video_title)
    if match:
        artist = match.group(1).strip()
        artist = re.sub(r'\s+feat\..*$', '', artist, flags=re.IGNORECASE)
        return artist

    return None

def clean_japanese_artist_name(artist_name: str) -> str:
    """Removes Romanized suffix from Japanese artist names (e.g. '米津玄師 Kenshi Yonezu')."""
    if not artist_name:
        return ""
        
    if re.search(r'[ぁ-んァ-ヶー一-龯]', artist_name):
        # Only remove if separated by space to avoid breaking names like Official髭男dism
        # Remove suffix alphabet (requires space before)
        japanese_part = re.sub(r'\s+[A-Za-z\s]+$', '', artist_name).strip()
        # Remove prefix alphabet (requires space after)
        japanese_part = re.sub(r'^[A-Za-z\s]+\s+', '', japanese_part).strip()
        return japanese_part if japanese_part else artist_name
        
    return artist_name
