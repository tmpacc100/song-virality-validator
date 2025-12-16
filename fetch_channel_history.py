#!/usr/bin/env python3
"""
チャンネルの過去投稿データを取得して学習用データを生成
YouTube Data API v3を使用
"""

import os
import json
import csv
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time

# YouTube API設定
API_KEYS = [
    "AIzaSyCJGKejEe2kWJL2_OaXgqP2__jndZEy588",
    "AIzaSyAYjocbnNJabLlrdAoi5ynmTZ05TOgumwE",
    "AIzaSyAxpi2HcJx88xGFnK0Dl1fs55Ge_wWye2s",
    "AIzaSyAau11IT5KoG-GMEEjph5PnIgLzcEPc3bg",
    "AIzaSyB4mI2gLeVQ38FJmc-LB2iAhgM4lmvRwXg",
    "AIzaSyAyZ1CX-itALbov6ehkcTbzOcYOU41Xhpc",
    "AIzaSyC7qvI2c0TDCBtOJAUDeXl6i17VVN-SEBI",
    "AIzaSyBj5AIrkv1wTUfa6VQK2ur8Ldx4h8IoETo",
    "AIzaSyBURv-z_cInwFq5pYNCr4CpJkvqLyMKCkI",
    "AIzaSyAnf54Nc8N6LP605ce1i-XESRV6an2WXFw",
    "AIzaSyDWfhm7MB6lyoU5QOLXs3dw6JDeCuTo_Gw",
    "AIzaSyCmIltqc6DQdmP5tYAUpTWRYmBQpFVXUvw",
    "AIzaSyBR1XE02737tE2sPvjcCzpji0sS7N4pvhA",
    "AIzaSyAAR8KMXFCKNzKVN6ZOI7auUC1R0PiffNs",
    "AIzaSyBZFye-ujRnbHVtIluKMNQZ_6CIQymRg2g",
    "AIzaSyBRGbHlkw9AoXC6vkFHxqUAUuxhErBhoQM",
    "AIzaSyAVU6CKXYGA3xXW8CeIoZgMujQqYl0eAqM",
    "AIzaSyDsny--LjcpRYFpMFCa2rAGZNrAatxHAZE",
    "AIzaSyDcA4yi9a6rmozfXQ7P9luYyXK9m8hewrY"
]

CHANNEL_HANDLE = '@taiko_de_hit_song'
OUTPUT_CSV = 'channel_history.csv'
OUTPUT_JSON = 'channel_history.json'

current_api_key_index = 0

def get_youtube_client():
    """YouTube APIクライアントを取得（キーローテーション対応）"""
    global current_api_key_index
    api_key = API_KEYS[current_api_key_index % len(API_KEYS)]
    return build('youtube', 'v3', developerKey=api_key)

def rotate_api_key():
    """APIキーをローテーション"""
    global current_api_key_index
    current_api_key_index += 1
    print(f"APIキーをローテーション: {current_api_key_index % len(API_KEYS) + 1}/{len(API_KEYS)}")

def get_channel_id_from_handle(youtube, handle):
    """ハンドル名からチャンネルIDを取得"""
    try:
        # @を除去
        handle = handle.lstrip('@')

        # 検索APIでチャンネルを探す
        request = youtube.search().list(
            part='snippet',
            q=handle,
            type='channel',
            maxResults=5
        )
        response = request.execute()

        for item in response.get('items', []):
            channel_title = item['snippet']['title']
            channel_id = item['snippet']['channelId']
            print(f"候補: {channel_title} (ID: {channel_id})")

            # タイトルにハンドル名が含まれているか確認
            if handle.lower() in channel_title.lower() or 'taiko' in channel_title.lower():
                print(f"✓ チャンネルを特定: {channel_title}")
                return channel_id

        # 見つからない場合は最初の結果を使用
        if response.get('items'):
            channel_id = response['items'][0]['snippet']['channelId']
            print(f"デフォルト選択: {response['items'][0]['snippet']['title']}")
            return channel_id

        return None

    except HttpError as e:
        print(f"エラー: チャンネルID取得失敗 - {e}")
        if e.resp.status == 403:
            rotate_api_key()
            return get_channel_id_from_handle(get_youtube_client(), handle)
        return None

def get_uploads_playlist_id(youtube, channel_id):
    """チャンネルのアップロードプレイリストIDを取得"""
    try:
        request = youtube.channels().list(
            part='contentDetails',
            id=channel_id
        )
        response = request.execute()

        if response.get('items'):
            uploads_playlist = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            return uploads_playlist
        return None

    except HttpError as e:
        print(f"エラー: プレイリストID取得失敗 - {e}")
        if e.resp.status == 403:
            rotate_api_key()
            return get_uploads_playlist_id(get_youtube_client(), channel_id)
        return None

def get_video_details(youtube, video_id):
    """動画の詳細情報を取得"""
    try:
        request = youtube.videos().list(
            part='snippet,statistics,contentDetails',
            id=video_id
        )
        response = request.execute()

        if not response.get('items'):
            return None

        item = response['items'][0]
        snippet = item['snippet']
        statistics = item.get('statistics', {})
        content_details = item['contentDetails']

        # 投稿日時をパース
        published_at = snippet['publishedAt']
        dt = datetime.strptime(published_at, '%Y-%m-%dT%H:%M:%SZ')

        # ショート動画かどうか判定（60秒以下）
        duration = content_details.get('duration', 'PT0S')
        # ISO 8601形式をパース（例: PT1M30S -> 90秒）
        import re
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            total_seconds = hours * 3600 + minutes * 60 + seconds
        else:
            total_seconds = 0

        is_short = total_seconds <= 60

        return {
            'video_id': video_id,
            'title': snippet['title'],
            'description': snippet.get('description', ''),
            'published_at': published_at,
            'published_date': dt.strftime('%Y-%m-%d'),
            'published_time': dt.strftime('%H:%M:%S'),
            'published_hour': dt.hour,
            'published_day_of_week': dt.weekday(),  # 0=月曜
            'published_is_weekend': 1 if dt.weekday() >= 5 else 0,
            'view_count': int(statistics.get('viewCount', 0)),
            'like_count': int(statistics.get('likeCount', 0)),
            'comment_count': int(statistics.get('commentCount', 0)),
            'duration_seconds': total_seconds,
            'is_short': is_short,
            'tags': ','.join(snippet.get('tags', [])),
        }

    except HttpError as e:
        print(f"エラー: 動画詳細取得失敗 ({video_id}) - {e}")
        if e.resp.status == 403:
            rotate_api_key()
            return get_video_details(get_youtube_client(), video_id)
        return None
    except Exception as e:
        print(f"エラー: データパース失敗 ({video_id}) - {e}")
        return None

def fetch_all_videos(youtube, playlist_id, max_results=None):
    """プレイリストから全動画を取得"""
    videos = []
    next_page_token = None

    if max_results:
        print(f"\n動画データ取得開始（最大{max_results}件）...")
    else:
        print(f"\n動画データ取得開始（全件取得）...")

    while True:
        try:
            # max_resultsがある場合は制限、ない場合は全件取得
            if max_results:
                if len(videos) >= max_results:
                    break
                batch_size = min(50, max_results - len(videos))
            else:
                batch_size = 50

            request = youtube.playlistItems().list(
                part='contentDetails',
                playlistId=playlist_id,
                maxResults=batch_size,
                pageToken=next_page_token
            )
            response = request.execute()

            for item in response.get('items', []):
                video_id = item['contentDetails']['videoId']
                if max_results:
                    print(f"  取得中: {video_id} ({len(videos) + 1}/{max_results})")
                else:
                    print(f"  取得中: {video_id} ({len(videos) + 1}件目)")

                video_data = get_video_details(youtube, video_id)
                if video_data:
                    videos.append(video_data)
                    print(f"    ✓ {video_data['title'][:50]}... - {video_data['view_count']:,} views")

                time.sleep(0.1)  # API制限対策

            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

        except HttpError as e:
            print(f"エラー: 動画リスト取得失敗 - {e}")
            if e.resp.status == 403:
                rotate_api_key()
                youtube = get_youtube_client()
                continue
            break

    return videos

def save_to_csv(videos, filename):
    """CSVファイルに保存"""
    if not videos:
        print("保存するデータがありません")
        return

    fieldnames = [
        'video_id', 'title', 'published_at', 'published_date', 'published_time',
        'published_hour', 'published_day_of_week', 'published_is_weekend',
        'view_count', 'like_count', 'comment_count',
        'duration_seconds', 'is_short', 'tags'
    ]

    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(videos)

    print(f"\n✓ CSV保存完了: {filename} ({len(videos)}件)")

def save_to_json(videos, filename):
    """JSONファイルに保存"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)

    print(f"✓ JSON保存完了: {filename} ({len(videos)}件)")

def detect_ads(videos):
    """広告・プロモーション動画を検出"""
    # より厳密な広告検出（#shortsは除外）
    ad_keywords_title = [
        '広告', 'sponsored', 'promotion', 'プロモーション',
        'コマーシャル', '提供', 'presented by', 'タイアップ'
    ]

    ad_keywords_desc = [
        '#ad', '#pr', '案件', '広告', 'sponsored'
    ]

    ads = []
    for v in videos:
        title_lower = v['title'].lower()
        desc_lower = v['description'].lower()

        is_ad = False

        # タイトルに明確な広告キーワードがあるか
        for keyword in ad_keywords_title:
            if keyword in title_lower:
                is_ad = True
                break

        # 説明文に広告マーカーがあるか（より厳密に）
        if not is_ad:
            for keyword in ad_keywords_desc:
                # #ad や #pr は単語境界で判定（#shorts などを誤検出しない）
                if keyword.startswith('#'):
                    # ハッシュタグとして完全一致
                    if keyword + ' ' in desc_lower or keyword + '\n' in desc_lower or desc_lower.endswith(keyword):
                        is_ad = True
                        break
                elif keyword in desc_lower:
                    is_ad = True
                    break

        if is_ad:
            ads.append(v)

    return ads

def analyze_shorts_patterns(videos):
    """ショート動画のパターンを分析（広告を除外）"""
    # 広告動画を検出
    ads = detect_ads(videos)

    # 広告以外のショート動画
    shorts = [v for v in videos if v['is_short'] and v not in ads]
    ad_shorts = [v for v in videos if v['is_short'] and v in ads]

    if not shorts:
        print("\nショート動画が見つかりませんでした")
        return

    print(f"\n{'='*60}")
    print(f"ショート動画分析結果（広告除外）")
    print(f"{'='*60}")
    print(f"総動画数: {len(videos)}件")
    print(f"  - ショート動画: {len([v for v in videos if v['is_short']])}件")
    print(f"  - 通常動画: {len([v for v in videos if not v['is_short']])}件")
    print(f"広告・プロモーション動画: {len(ads)}件")
    print(f"  - 広告ショート: {len(ad_shorts)}件")
    print(f"分析対象（広告除外後）: {len(shorts)}件")

    # 曜日別平均視聴数
    print(f"\n【曜日別平均視聴数（ショートのみ）】")
    day_names = ['月曜', '火曜', '水曜', '木曜', '金曜', '土曜', '日曜']
    for day in range(7):
        day_shorts = [v for v in shorts if v['published_day_of_week'] == day]
        if day_shorts:
            avg_views = sum(v['view_count'] for v in day_shorts) / len(day_shorts)
            print(f"  {day_names[day]}: {avg_views:,.0f} views (投稿数: {len(day_shorts)})")

    # 時間帯別平均視聴数
    print(f"\n【時間帯別平均視聴数（ショートのみ）】")
    for hour in range(24):
        hour_shorts = [v for v in shorts if v['published_hour'] == hour]
        if hour_shorts:
            avg_views = sum(v['view_count'] for v in hour_shorts) / len(hour_shorts)
            print(f"  {hour:02d}時台: {avg_views:,.0f} views (投稿数: {len(hour_shorts)})")

    # トップ10ショート
    print(f"\n【視聴数トップ10（ショートのみ）】")
    top_shorts = sorted(shorts, key=lambda x: x['view_count'], reverse=True)[:10]
    for i, video in enumerate(top_shorts, 1):
        dt = datetime.strptime(video['published_at'], '%Y-%m-%dT%H:%M:%SZ')
        print(f"  {i}. {video['view_count']:>10,} views - {dt.strftime('%Y-%m-%d %H:%M')} ({day_names[dt.weekday()]})")
        print(f"     {video['title'][:60]}...")

def main():
    print("="*60)
    print("YouTubeチャンネル履歴データ取得")
    print("="*60)

    youtube = get_youtube_client()

    # チャンネルIDを取得
    print(f"\n1. チャンネルID取得: {CHANNEL_HANDLE}")
    channel_id = get_channel_id_from_handle(youtube, CHANNEL_HANDLE)
    if not channel_id:
        print("エラー: チャンネルが見つかりませんでした")
        return

    print(f"   チャンネルID: {channel_id}")

    # アップロードプレイリストIDを取得
    print(f"\n2. アップロードプレイリストID取得")
    playlist_id = get_uploads_playlist_id(youtube, channel_id)
    if not playlist_id:
        print("エラー: プレイリストが見つかりませんでした")
        return

    print(f"   プレイリストID: {playlist_id}")

    # 全動画を取得（制限なし）
    print(f"\n3. 動画データ取得")
    videos = fetch_all_videos(youtube, playlist_id, max_results=None)

    if not videos:
        print("エラー: 動画データが取得できませんでした")
        return

    # 広告動画を検出
    print(f"\n4. 広告動画検出")
    ads = detect_ads(videos)
    if ads:
        print(f"  検出された広告動画: {len(ads)}件")
        # 広告動画を別ファイルに保存
        save_to_csv(ads, 'channel_history_ads.csv')
        print(f"  広告動画を channel_history_ads.csv に保存しました")

    # 広告を除外したデータを保存
    non_ad_videos = [v for v in videos if v not in ads]

    # 保存
    print(f"\n5. データ保存")
    save_to_csv(videos, OUTPUT_CSV)  # 全動画
    save_to_json(videos, OUTPUT_JSON)  # 全動画
    save_to_csv(non_ad_videos, 'channel_history_clean.csv')  # 広告除外
    print(f"  広告除外データを channel_history_clean.csv に保存しました")

    # 分析
    print(f"\n6. パターン分析")
    analyze_shorts_patterns(videos)

    print(f"\n{'='*60}")
    print("✅ 完了")
    print(f"{'='*60}")
    print(f"\n次のステップ:")
    print(f"  1. {OUTPUT_CSV} を確認")
    print(f"  2. ML/RLモデルに学習データとして追加")
    print(f"  3. 信頼度スコアの再計算")

if __name__ == '__main__':
    main()
