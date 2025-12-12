#!/usr/bin/env python3
"""iTunes Search APIを使って曲名からアーティスト名を取得する専用スクリプト"""

import sys
import urllib.parse
import requests


def get_artist_from_itunes(song_name):
    """iTunes Search APIからアーティスト名を取得

    Args:
        song_name: 曲名

    Returns:
        アーティスト名（見つからない場合は空文字列）
    """
    try:
        # 曲名をURLエンコード
        encoded_song = urllib.parse.quote(song_name)
        url = f"https://itunes.apple.com/search?term={encoded_song}&country=jp&media=music&limit=10"

        print(f"🎵 iTunes APIで検索中: {song_name}")
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])

            if results:
                print(f"\n検索結果: {len(results)}件\n")

                # 曲名が一致する結果を表示
                matched_count = 0
                for i, result in enumerate(results, 1):
                    artist = result.get('artistName', '')
                    track = result.get('trackName', '')

                    # 曲名が一致する場合
                    if song_name.lower() in track.lower() or track.lower() in song_name.lower():
                        matched_count += 1
                        print(f"{matched_count}. アーティスト: {artist}")
                        print(f"   曲名: {track}")

                        # アーティスト名と曲名が同じ場合は警告
                        if artist.lower() == song_name.lower():
                            print(f"   ⚠️  注意: アーティスト名と曲名が同じです")
                        print()

                if matched_count == 0:
                    print("❌ 曲名が一致する結果が見つかりませんでした")
                    print("\n全検索結果:")
                    for i, result in enumerate(results[:5], 1):
                        artist = result.get('artistName', '')
                        track = result.get('trackName', '')
                        print(f"{i}. アーティスト: {artist}")
                        print(f"   曲名: {track}")
                        print()
                    return ""

                # 最初の一致した結果を返す
                for result in results:
                    artist = result.get('artistName', '')
                    track = result.get('trackName', '')

                    if song_name.lower() in track.lower() or track.lower() in song_name.lower():
                        if artist and artist.lower() != song_name.lower():
                            print(f"✅ 選択されたアーティスト: {artist}")
                            return artist

                return ""

        print(f"❌ iTunes APIで見つかりませんでした")
        return ""

    except Exception as e:
        print(f"⚠️  iTunes API エラー: {e}")
        return ""


def main():
    """メイン関数"""
    if len(sys.argv) < 2:
        print("使用方法: python3 get_artist_from_itunes.py <曲名>")
        print("例: python3 get_artist_from_itunes.py Lemon")
        sys.exit(1)

    song_name = " ".join(sys.argv[1:])
    print("="*60)
    print("iTunes Search API - アーティスト名取得")
    print("="*60)
    print()

    artist = get_artist_from_itunes(song_name)

    print()
    print("="*60)
    if artist:
        print(f"結果: {artist}")
    else:
        print("結果: アーティスト名を取得できませんでした")
    print("="*60)


if __name__ == '__main__':
    main()
