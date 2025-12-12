#!/usr/bin/env python3
"""YouTubeチャンネルで既に投稿されている動画をフィルタリング"""
import csv
import os
import requests
from bs4 import BeautifulSoup
from googleapiclient.discovery import build

# YouTube API設定
YOUTUBE_API_KEY = "AIzaSyBbSQiuuHzqGfXEzKYU86wYTnCdIYYTQn4"
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# チャンネルURL
CHANNEL_URL = "https://www.youtube.com/@taiko_de_hit_song"


def get_channel_id_from_handle(channel_handle):
    """チャンネルハンドルからチャンネルIDを取得

    Args:
        channel_handle: チャンネルハンドル（例: @taiko_de_hit_song）

    Returns:
        チャンネルID
    """
    try:
        # @を削除
        handle = channel_handle.replace('@', '')

        # YouTube APIでチャンネルを検索
        request = youtube.search().list(
            part="snippet",
            q=handle,
            type="channel",
            maxResults=5
        )
        response = request.execute()

        # 最初のチャンネルIDを返す
        if response['items']:
            channel_id = response['items'][0]['snippet']['channelId']
            print(f"✓ チャンネルID: {channel_id}")
            return channel_id

    except Exception as e:
        print(f"⚠ チャンネルID取得エラー: {e}")

    return None


def get_uploaded_video_titles(channel_id):
    """チャンネルから投稿済み動画のタイトルを取得

    Args:
        channel_id: YouTubeチャンネルID

    Returns:
        set: 投稿済み動画のタイトルセット
    """
    uploaded_titles = set()

    try:
        # チャンネルの「アップロード」プレイリストIDを取得
        channel_response = youtube.channels().list(
            part="contentDetails",
            id=channel_id
        ).execute()

        if not channel_response['items']:
            print("⚠ チャンネルが見つかりません")
            return uploaded_titles

        uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        print(f"\n動画リストを取得中...")

        # プレイリストから全動画を取得
        next_page_token = None
        video_count = 0

        while True:
            playlist_response = youtube.playlistItems().list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=50,
                pageToken=next_page_token
            ).execute()

            for item in playlist_response['items']:
                title = item['snippet']['title']
                # 「広告」という文字が含まれている動画は除外
                if '広告' not in title:
                    uploaded_titles.add(title)
                    video_count += 1

            next_page_token = playlist_response.get('nextPageToken')

            if not next_page_token:
                break

            print(f"  取得中... {video_count}件")

        print(f"✓ {len(uploaded_titles)} 件の動画タイトルを取得しました")

    except Exception as e:
        print(f"⚠ 動画リスト取得エラー: {e}")
        import traceback
        traceback.print_exc()

    return uploaded_titles


def extract_song_from_title(title):
    """動画タイトルから曲名を抽出

    Args:
        title: 動画タイトル

    Returns:
        曲名（抽出できない場合はタイトルそのまま）
    """
    # 【曲名 - アーティスト名】パターンから曲名を抽出
    # 例: "【聖者の行進 - キタニタツヤ】たいこで叩いてみた" → "聖者の行進"
    import re

    # パターン1: 【曲名 - アーティスト名】
    match = re.search(r'【([^-】]+)\s*-', title)
    if match:
        return match.group(1).strip()

    # パターン2: 【曲名】
    match = re.search(r'【([^】]+)】', title)
    if match:
        return match.group(1).strip()

    # パターン3: タイトルそのまま
    return title


def filter_csv_by_uploaded_videos(input_csv, output_csv, uploaded_titles):
    """CSVから投稿済み動画をフィルタリング

    Args:
        input_csv: 入力CSVファイルパス
        output_csv: 出力CSVファイルパス
        uploaded_titles: 投稿済み動画タイトルのセット
    """
    if not os.path.exists(input_csv):
        print(f"\nエラー: {input_csv} が見つかりません")
        return

    filtered_songs = []
    total_count = 0
    filtered_count = 0

    # 投稿済みタイトルから曲名を抽出
    uploaded_song_names = set()
    for title in uploaded_titles:
        song = extract_song_from_title(title)
        uploaded_song_names.add(song)

    print(f"\n投稿済み曲名パターン数: {len(uploaded_song_names)}")

    # デバッグ: 最初の10件の抽出結果を表示
    print("\n動画タイトルサンプル（最初の10件）:")
    for i, title in enumerate(list(uploaded_titles)[:10], 1):
        extracted = extract_song_from_title(title)
        print(f"{i}. 元タイトル: {title}")
        print(f"   抽出曲名: {extracted}")
        print()

    # CSVを読み込んでフィルタリング
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for row in reader:
            total_count += 1
            song_name = row.get('song_name', '') or row.get('曲名', '')

            # 投稿済みかチェック
            if song_name in uploaded_song_names:
                filtered_count += 1
                print(f"  除外: {song_name}")
            else:
                filtered_songs.append(row)

    # フィルタリング結果を保存
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered_songs)

    print("\n" + "=" * 70)
    print("フィルタリング結果:")
    print("=" * 70)
    print(f"  元データ: {total_count}曲")
    print(f"  除外: {filtered_count}曲（既に投稿済み）")
    print(f"  残り: {len(filtered_songs)}曲")
    print(f"\n✓ {output_csv} に保存しました")
    print("=" * 70)


def main():
    """メイン処理"""
    print("=" * 70)
    print("YouTubeチャンネル投稿済み動画フィルタリング")
    print("=" * 70)

    # チャンネルIDを取得
    print(f"\nチャンネル: {CHANNEL_URL}")
    channel_id = get_channel_id_from_handle("@taiko_de_hit_song")

    if not channel_id:
        print("\n⚠ チャンネルIDが取得できませんでした")
        return

    # 投稿済み動画のタイトルを取得
    uploaded_titles = get_uploaded_video_titles(channel_id)

    if not uploaded_titles:
        print("\n⚠ 投稿済み動画が見つかりませんでした")
        return

    # デフォルトで filtered data のリリース/開発中データをフィルタリング
    input_csv = 'filtered data/taiko_server_リリース_開発中_filtered.csv'
    output_csv = 'filtered data/taiko_server_未投稿_filtered.csv'

    print("\n" + "=" * 70)
    print("フィルタリング対象:")
    print("=" * 70)
    print(f"入力: {input_csv}")
    print(f"出力: {output_csv}")

    # フィルタリング実行
    filter_csv_by_uploaded_videos(input_csv, output_csv, uploaded_titles)


if __name__ == '__main__':
    main()
