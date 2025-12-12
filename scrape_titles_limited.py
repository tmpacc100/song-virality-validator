#!/usr/bin/env python3
"""video_idからYouTubeページをスクレイピングしてタイトルを取得（制限付き）"""

import json
import re
import time
import requests
import sys
import urllib.parse
from main import extract_artist_from_title, save_cache, create_rankings, save_rankings, get_artist_from_itunes

def get_video_title_from_page(video_id):
    """YouTubeページからタイトルとチャンネル名を取得"""
    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            title = None
            channel = None

            # タイトルを抽出（<title>タグから）
            title_match = re.search(r'<title>(.+?) - YouTube</title>', response.text)
            if title_match:
                title = title_match.group(1)
            else:
                # og:titleメタタグから抽出（フォールバック）
                og_title_match = re.search(r'<meta property="og:title" content="(.+?)"', response.text)
                if og_title_match:
                    title = og_title_match.group(1)

            # チャンネル名を抽出
            channel_match = re.search(r'"ownerChannelName":"([^"]+)"', response.text)
            if channel_match:
                channel = channel_match.group(1)
            else:
                # 別のパターンを試す
                channel_match2 = re.search(r'"author":"([^"]+)"', response.text)
                if channel_match2:
                    channel = channel_match2.group(1)

            return title, channel
    except Exception as e:
        print(f"    エラー: {e}")
        return None, None

    return None, None

def main():
    # コマンドライン引数で処理する曲数を指定（デフォルト: 全曲）
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    print("="*60)
    if limit:
        print(f"YouTubeページから最初の{limit}曲のタイトルをスクレイピングします")
    else:
        print("YouTubeページからタイトルをスクレイピングします（全曲）")
    print("="*60)

    # youtube_stats.jsonを読み込む
    try:
        with open('youtube_stats.json', 'r', encoding='utf-8') as f:
            songs_data = json.load(f)
    except FileNotFoundError:
        print("エラー: youtube_stats.json が見つかりません")
        return

    total = len(songs_data)
    process_count = min(limit, total) if limit else total

    print(f"\n読み込み: {total}曲")
    print(f"処理対象: {process_count}曲")
    print("タイトルを取得中...\n")

    # 各曲のタイトルを取得してアーティスト名を抽出
    updated_count = 0
    for i, song in enumerate(songs_data[:process_count] if limit else songs_data, 1):
        song_name = song.get('song_name', '')
        video_id = song.get('video_id', '')

        if not video_id:
            song['video_title'] = ''
            song['artist_name'] = ''
            continue

        print(f"[{i}/{process_count}] {song_name} ({video_id})")

        # タイトルとチャンネル名を取得
        title, channel = get_video_title_from_page(video_id)

        if title:
            song['video_title'] = title
            if channel:
                song['channel_title'] = channel

            # アーティスト名取得の優先順位:
            # 1. iTunes Search API (exactマッチのみ)
            # 2. 動画タイトルから抽出
            # 3. iTunes Search API (candidateも使用)
            # 4. チャンネル名から抽出

            # 1. iTunes Search APIで検索（動画情報を渡して精度向上）
            itunes_artist, itunes_confidence = get_artist_from_itunes(song_name, title, channel)

            # exactマッチの場合はそのまま使用
            if itunes_confidence == "exact":
                artist_name = itunes_artist
            else:
                # 2. タイトルから抽出を試みる
                print(f"  📺 タイトルから抽出を試みます")
                artist_name = extract_artist_from_title(title, song_name)

                # 3. タイトルから抽出できず、iTunesに候補がある場合は候補を使用
                if not artist_name and itunes_confidence == "candidate":
                    artist_name = itunes_artist

            # アーティスト名に日本語とアルファベットが混在している場合、日本語のみ抽出
            if artist_name and re.search(r'[ぁ-んァ-ヶー一-龯]', artist_name):
                # 末尾のアルファベットを削除
                japanese_artist = re.sub(r'\s*[A-Za-z\s]+$', '', artist_name).strip()
                # 先頭のアルファベットも削除
                japanese_artist = re.sub(r'^[A-Za-z\s]+\s*', '', japanese_artist).strip()
                if japanese_artist:
                    artist_name = japanese_artist

            # 3. タイトルから抽出できない場合は、チャンネル名を使用
            # ただし、チャンネル名が曲名と同じ場合は使用しない
            if not artist_name and channel:
                print(f"  📢 チャンネル名から抽出を試みます")
                # チャンネル名が曲名と違う場合のみ使用
                if channel.lower() != song_name.lower():
                    # 「チャンネル」や「channel」が含まれている場合、その前の部分を抽出
                    cleaned_channel = channel
                    if 'チャンネル' in channel:
                        cleaned_channel = channel.split('チャンネル')[0].strip()
                    elif 'channel' in channel.lower():
                        # 大文字小文字を区別せずに分割
                        match = re.search(r'(.+?)\s*channel', channel, re.IGNORECASE)
                        if match:
                            cleaned_channel = match.group(1).strip()

                    # 日本語とアルファベットが混在している場合、日本語部分のみを抽出
                    # 例: "米津玄師  Kenshi Yonezu" -> "米津玄師"
                    # 例: "Kenshi Yonezu  米津玄師" -> "米津玄師"
                    if re.search(r'[ぁ-んァ-ヶー一-龯]', cleaned_channel):  # 日本語が含まれているか
                        # 日本語とアルファベットが混在している場合
                        # 末尾のアルファベットを削除
                        japanese_part = re.sub(r'\s*[A-Za-z\s]+$', '', cleaned_channel).strip()
                        # 先頭のアルファベットも削除
                        japanese_part = re.sub(r'^[A-Za-z\s]+\s*', '', japanese_part).strip()
                        if japanese_part:
                            cleaned_channel = japanese_part

                    # クリーン後のチャンネル名が空でない場合のみ使用
                    if cleaned_channel:
                        artist_name = cleaned_channel

            song['artist_name'] = artist_name

            if artist_name:
                print(f"  ✓ タイトル: {title}")
                print(f"  ✓ チャンネル: {channel or '(不明)'}")
                print(f"  ✓ アーティスト: {artist_name}")
                updated_count += 1
            else:
                print(f"  - タイトル: {title}")
                print(f"  - チャンネル: {channel or '(不明)'}")
                print(f"  - アーティスト名を抽出できませんでした")
        else:
            song['video_title'] = ''
            song['artist_name'] = ''
            print(f"  ✗ タイトル取得失敗")

        # レート制限を避けるため少し待機
        if i % 10 == 0:
            print(f"\n  休憩中... ({i}/{process_count})\n")
            time.sleep(2)
        else:
            time.sleep(0.5)

    print(f"\n結果: {updated_count}/{process_count}曲にアーティスト名を追加しました")

    # キャッシュを保存
    save_cache(songs_data)
    print("✓ キャッシュを更新しました")

    # ランキングを再計算
    print("\nランキングを再計算中...")
    rankings = create_rankings(songs_data)
    save_rankings(rankings)
    print("✓ ランキングを保存しました")

    print("\n" + "="*60)
    print("完了！次のコマンドでCSVを生成してください:")
    print("  python3 json_to_csv.py")
    print("="*60)

if __name__ == '__main__':
    main()
