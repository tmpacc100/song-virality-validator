#!/usr/bin/env python3
"""iTunes API機能のテスト"""
import requests


def fetch_itunes_artist(song_name):
    """iTunes APIから曲のアーティスト名を取得

    Args:
        song_name: 曲名

    Returns:
        str: アーティスト名、見つからない場合はNone
    """
    try:
        # iTunes Search API
        base_url = 'https://itunes.apple.com/search'
        params = {
            'term': song_name,
            'country': 'JP',  # 日本のストア
            'media': 'music',
            'entity': 'song',
            'limit': 5  # 上位5件を取得
        }

        response = requests.get(base_url, params=params, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()
        results = data.get('results', [])

        if not results:
            return None

        # 最初の結果からアーティスト名を取得
        # trackNameが曲名と一致するものを優先
        for result in results:
            track_name = result.get('trackName', '')
            artist_name = result.get('artistName', '')

            # 曲名が部分一致する場合はそのアーティストを返す
            if song_name.lower() in track_name.lower() or track_name.lower() in song_name.lower():
                return artist_name

        # 完全一致がない場合は最初の結果を返す
        return results[0].get('artistName')

    except Exception:
        # iTunes APIエラーは無視してNoneを返す（フォールバックが動作する）
        return None


# テストケース
test_songs = [
    "NIGHT DANCER",
    "Overdose",
    "踊り子",
    "IRIS OUT",
    "オトノケ",
    "廻廻奇譚",
    "グッバイ宣言",
]

print("=" * 70)
print("iTunes API テスト")
print("=" * 70)

for song in test_songs:
    artist = fetch_itunes_artist(song)
    if artist:
        print(f"✓ {song} → {artist}")
    else:
        print(f"✗ {song} → 見つかりませんでした")

print("=" * 70)
