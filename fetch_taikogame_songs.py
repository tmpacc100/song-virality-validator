#!/usr/bin/env python3
"""TaikoGameサーバーから曲情報を取得してCSVに保存"""
import requests
import csv
import re


def fetch_taikogame_songs():
    """TaikoGameサーバーから曲情報を取得

    Returns:
        list: [{song_name: str, artist_name: str}, ...] の配列
    """
    username = 'shii'
    password = '0619'
    songs_url = 'https://taikogame-server.herokuapp.com/songs'

    songs_list = []

    try:
        print("TaikoGameサーバーから曲情報を取得中...")
        response = requests.get(songs_url, auth=(username, password))

        if response.status_code != 200:
            print(f"⚠ サーバーアクセス失敗: {response.status_code}")
            return songs_list

        data = response.json()

        if not isinstance(data, list):
            print(f"⚠ 予期しないデータ形式: {type(data)}")
            return songs_list

        print(f"✓ {len(data)} 件の曲データを取得しました\n")

        for song in data:
            title = song.get('title', '')

            if not title:
                continue

            # Titleから曲名とアーティスト名を抽出
            # パターン例:
            # "曲名 / アーティスト名(ふりがな)"
            # "曲名 / アーティスト名(ふりがな) (アニメ名主題歌)"

            # まず / で分割
            if '/' in title:
                parts = title.split('/', 1)
                song_name = parts[0].strip()
                artist_part = parts[1].strip() if len(parts) > 1 else ''

                # アーティスト部分から (振り仮名) や (主題歌) を除去
                # "アーティスト名(ふりがな) (アニメ名主題歌)" → "アーティスト名"
                artist_name = re.sub(r'\([^)]+\)', '', artist_part).strip()

                if song_name and artist_name:
                    songs_list.append({
                        'song_name': song_name,
                        'artist_name': artist_name,
                        'original_title': title
                    })
            else:
                # / がない場合はタイトル全体を曲名として扱う
                song_name = re.sub(r'\([^)]+\)', '', title).strip()
                if song_name:
                    songs_list.append({
                        'song_name': song_name,
                        'artist_name': '',
                        'original_title': title
                    })

        print(f"✓ {len(songs_list)} 曲を抽出しました")

    except Exception as e:
        print(f"⚠ エラー: {e}")

    return songs_list


def save_to_csv(songs_list, output_file='taikogame_songs.csv'):
    """曲リストをCSVに保存

    Args:
        songs_list: 曲情報のリスト
        output_file: 出力CSVファイル名
    """
    if not songs_list:
        print("保存する曲データがありません")
        return

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['song_name', 'artist_name', 'original_title'])
        writer.writeheader()
        writer.writerows(songs_list)

    print(f"\n✓ {output_file} に保存しました")


if __name__ == '__main__':
    print("=" * 70)
    print("TaikoGame 曲情報取得")
    print("=" * 70)

    songs = fetch_taikogame_songs()

    # 最初の10件を表示
    print("\n" + "=" * 70)
    print("取得データサンプル（最初の10件）:")
    print("=" * 70)
    for i, song in enumerate(songs[:10], 1):
        print(f"{i}. 曲名: {song['song_name']}")
        print(f"   アーティスト: {song['artist_name']}")
        print(f"   元タイトル: {song['original_title']}")
        print()

    # CSVに保存
    save_to_csv(songs)

    print("=" * 70)
    print(f"完了: {len(songs)} 曲を処理しました")
    print("=" * 70)
