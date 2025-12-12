#!/usr/bin/env python3
"""アーティスト名取得の優先順位テスト

優先順位:
1. PianoGame
2. iTunes API
3. 動画タイトル抽出
"""
import requests
import re
from bs4 import BeautifulSoup


def extract_artist_from_title(video_title):
    """動画タイトルからアーティスト名を抽出"""
    if not video_title:
        return None

    # パターン1: 【artist】（角括弧内）
    match = re.search(r'【(.+?)】', video_title)
    if match:
        artist = match.group(1).strip()
        noise_words = ['第', '回', '歌合戦', 'NHK', '紅白', 'MV', 'MUSIC', 'Official', 'オリジナル楽曲', '歌唱曲']
        if not any(noise in artist for noise in noise_words):
            return artist

    # パターン2: artist｢song｣ または artist「song」（全角括弧の前）
    match = re.match(r'^([^\｢「]+)[｢「]', video_title)
    if match:
        return match.group(1).strip()

    # パターン3: artist - song（ハイフンの前）
    match = re.match(r'^(.+?)\s*[-−ー]\s*', video_title)
    if match:
        return match.group(1).strip()

    # パターン4: / artist :（スラッシュの後、コロンの前）
    match = re.search(r'/\s*(.+?)[:：]', video_title)
    if match:
        return match.group(1).strip()

    # パターン5: / artist（スラッシュの後）
    match = re.search(r'/\s*(.+?)$', video_title)
    if match:
        artist = match.group(1).strip()
        artist = re.sub(r'\s*(MUSIC\s+VIDEO|MV|Official.*|[\(\（].*?[\)\）]).*$', '', artist, flags=re.IGNORECASE)
        return artist.strip() if artist else None

    # パターン6: artist 'song' または artist "song"（半角引用符の前、スペース必須）
    match = re.match(r'^(.+?)\s+[\'\"\"'']', video_title)
    if match:
        artist = match.group(1).strip()
        artist = re.sub(r'\s+feat\..*$', '', artist, flags=re.IGNORECASE)
        return artist

    return None


def fetch_pianogame_artists():
    """PianoGameサーバーからアーティスト情報を取得"""
    username = 'shii'
    password = '0619'
    notifications_url = 'https://pianogame-server.herokuapp.com/notifications'

    artists_dict = {}

    try:
        response = requests.get(notifications_url, auth=(username, password))

        if response.status_code != 200:
            return artists_dict

        soup = BeautifulSoup(response.text, 'html.parser')

        table = soup.find('table')
        if table:
            rows = table.find_all('tr')[1:]

            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 5:
                    body = cols[2].get_text(strip=True)
                    song_name = cols[4].get_text(strip=True)

                    # Body列から「アーティスト名「曲名」を追加しました」を抽出
                    match = re.search(r'([^「」]+)「[^」]+」を追加しました', body)
                    if match:
                        artist_part = match.group(1)
                        # "から"または"で"の後ろを取得、なければ全体
                        artist = re.split(r'(?:から|で)', artist_part)[-1].strip()
                        if artist:
                            artists_dict[song_name] = artist

    except Exception:
        pass

    return artists_dict


def fetch_itunes_artist(song_name):
    """iTunes APIから曲のアーティスト名を取得"""
    try:
        base_url = 'https://itunes.apple.com/search'
        params = {
            'term': song_name,
            'country': 'JP',
            'media': 'music',
            'entity': 'song',
            'limit': 5
        }

        response = requests.get(base_url, params=params, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()
        results = data.get('results', [])

        if not results:
            return None

        for result in results:
            track_name = result.get('trackName', '')
            artist_name = result.get('artistName', '')

            if song_name.lower() in track_name.lower() or track_name.lower() in song_name.lower():
                return artist_name

        return results[0].get('artistName')

    except Exception:
        return None


# テストケース
test_cases = [
    {
        'song_name': 'NIGHT DANCER',
        'video_title': '【imase】NIGHT DANCER（MV）',
        'expected_source': 'PianoGame or iTunes or 動画タイトル',
    },
    {
        'song_name': 'Overdose',
        'video_title': 'なとり - Overdose',
        'expected_source': 'iTunes or 動画タイトル',
    },
    {
        'song_name': '踊り子',
        'video_title': '【第75回NHK紅白歌合戦 歌唱曲】踊り子 / Vaundy：MUSIC VIDEO',
        'expected_source': 'iTunes or 動画タイトル',
    },
]

print("=" * 70)
print("アーティスト名取得 優先順位テスト")
print("=" * 70)
print("優先順位: 1. PianoGame → 2. iTunes API → 3. 動画タイトル抽出")
print("=" * 70)

# PianoGameデータを取得
print("\n📡 PianoGameサーバーからアーティスト情報を取得中...")
pianogame_artists = fetch_pianogame_artists()
print(f"✓ PianoGameから {len(pianogame_artists)} 曲のアーティスト情報を取得")

print("\n" + "=" * 70)
print("テスト実行")
print("=" * 70)

for i, test in enumerate(test_cases, 1):
    song_name = test['song_name']
    video_title = test['video_title']

    print(f"\n{i}. 曲名: {song_name}")
    print(f"   動画タイトル: {video_title}")

    artist = None
    source = None

    # 優先順位1: PianoGame
    if song_name in pianogame_artists:
        artist = pianogame_artists[song_name]
        source = 'PianoGame'

    # 優先順位2: iTunes API
    if not artist:
        itunes_artist = fetch_itunes_artist(song_name)
        if itunes_artist:
            artist = itunes_artist
            source = 'iTunes API'

    # 優先順位3: 動画タイトル抽出
    if not artist:
        title_artist = extract_artist_from_title(video_title)
        if title_artist:
            artist = title_artist
            source = '動画タイトル'

    if artist:
        print(f"   ✓ アーティスト: {artist} (ソース: {source})")
    else:
        print(f"   ✗ アーティスト名を取得できませんでした")

print("\n" + "=" * 70)
print("テスト完了")
print("=" * 70)
