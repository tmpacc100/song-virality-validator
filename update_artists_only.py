#!/usr/bin/env python3
"""YouTube APIを使わずにアーティスト名のみを更新するスクリプト"""

import json
import re
import time
from main import get_artist_from_itunes, extract_artist_from_title, save_cache, create_rankings, save_rankings


def main():
    print("="*60)
    print("アーティスト名のみ更新（YouTube API不使用）")
    print("="*60)
    print("既存のyoutube_stats.jsonからアーティスト名のみを更新します")
    print("（動画タイトル、チャンネル名、再生数などは変更されません）")
    print("="*60)

    # youtube_stats.jsonを読み込む
    try:
        with open('youtube_stats.json', 'r', encoding='utf-8') as f:
            songs_data = json.load(f)
    except FileNotFoundError:
        print("\nエラー: youtube_stats.json が見つかりません")
        print("先に「1. 新動画fetch」を実行してください")
        return

    print(f"\n読み込み: {len(songs_data)}曲")
    print("\nアーティスト名を更新中...\n")

    updated_count = 0
    exact_match_count = 0
    candidate_match_count = 0
    title_extract_count = 0
    channel_extract_count = 0
    not_found_count = 0

    for i, song in enumerate(songs_data, 1):
        song_name = song.get('song_name', '')
        current_artist = song.get('artist_name', '')
        video_title = song.get('video_title', '')
        channel_title = song.get('channel_title', '')

        if not song_name:
            continue

        print(f"[{i}/{len(songs_data)}] {song_name}")
        if current_artist:
            print(f"  現在のアーティスト: {current_artist}")

        # アーティスト名取得の優先順位:
        # 1. iTunes Search API (exactマッチのみ)
        # 2. 動画タイトルから抽出
        # 3. iTunes Search API (candidateも使用)
        # 4. チャンネル名から抽出

        artist_name = ""
        source = ""

        # 1. iTunes Search APIで検索（動画情報を渡して精度向上）
        itunes_artist, itunes_confidence = get_artist_from_itunes(song_name, video_title, channel_title)

        # exactマッチの場合はそのまま使用
        if itunes_confidence == "exact":
            artist_name = itunes_artist
            source = "iTunes API (exact)"
            exact_match_count += 1
        else:
            # 2. タイトルから抽出を試みる
            if video_title:
                print(f"  📺 タイトルから抽出を試みます")
                artist_name = extract_artist_from_title(video_title, song_name)
                if artist_name:
                    source = "動画タイトル"
                    title_extract_count += 1

            # 3. タイトルから抽出できず、iTunesに候補がある場合は候補を使用
            if not artist_name and itunes_confidence == "candidate":
                artist_name = itunes_artist
                source = "iTunes API (candidate)"
                candidate_match_count += 1

            # アーティスト名に日本語とアルファベットが混在している場合、日本語のみ抽出
            if artist_name and re.search(r'[ぁ-んァ-ヶー一-龯]', artist_name):
                # 末尾のアルファベットを削除
                japanese_artist = re.sub(r'\s*[A-Za-z\s]+$', '', artist_name).strip()
                # 先頭のアルファベットも削除
                japanese_artist = re.sub(r'^[A-Za-z\s]+\s*', '', japanese_artist).strip()
                if japanese_artist:
                    artist_name = japanese_artist

            # 4. タイトルから抽出できない場合は、チャンネル名を使用
            if not artist_name and channel_title:
                print(f"  📢 チャンネル名から抽出を試みます")
                # チャンネル名が曲名と違う場合のみ使用
                if channel_title.lower() != song_name.lower():
                    # 「チャンネル」や「channel」が含まれている場合、その前の部分を抽出
                    cleaned_channel = channel_title
                    if 'チャンネル' in channel_title:
                        cleaned_channel = channel_title.split('チャンネル')[0].strip()
                    elif 'channel' in channel_title.lower():
                        # 大文字小文字を区別せずに分割
                        match = re.search(r'(.+?)\s*channel', channel_title, re.IGNORECASE)
                        if match:
                            cleaned_channel = match.group(1).strip()

                    # 日本語とアルファベットが混在している場合、日本語部分のみを抽出
                    if re.search(r'[ぁ-んァ-ヶー一-龯]', cleaned_channel):
                        # 末尾のアルファベットを削除
                        japanese_part = re.sub(r'\s*[A-Za-z\s]+$', '', cleaned_channel).strip()
                        # 先頭のアルファベットも削除
                        japanese_part = re.sub(r'^[A-Za-z\s]+\s*', '', japanese_part).strip()
                        if japanese_part:
                            cleaned_channel = japanese_part

                    # クリーン後のチャンネル名が空でない場合のみ使用
                    if cleaned_channel:
                        artist_name = cleaned_channel
                        source = "チャンネル名"
                        channel_extract_count += 1

        # アーティスト名を更新
        if artist_name:
            song['artist_name'] = artist_name
            updated_count += 1

            if current_artist != artist_name:
                print(f"  ✏️  更新: {current_artist or '(なし)'} → {artist_name} (出典: {source})")
            else:
                print(f"  ✓ 既存のアーティスト名を確認: {artist_name} (出典: {source})")
        else:
            not_found_count += 1
            if current_artist:
                print(f"  ⚠️  新しいアーティスト名が見つからず、既存を保持: {current_artist}")
            else:
                print(f"  ❌ アーティスト名を取得できませんでした")

        # APIレート制限を避けるため少し待機
        if i % 10 == 0:
            print(f"\n  休憩中... ({i}/{len(songs_data)})\n")
            time.sleep(2)
        else:
            time.sleep(0.3)

    print(f"\n" + "="*60)
    print("結果サマリー")
    print("="*60)
    print(f"処理した曲数: {len(songs_data)}曲")
    print(f"アーティスト名を取得できた曲: {updated_count}曲")
    print(f"  - iTunes API (exact): {exact_match_count}曲")
    print(f"  - 動画タイトルから抽出: {title_extract_count}曲")
    print(f"  - iTunes API (candidate): {candidate_match_count}曲")
    print(f"  - チャンネル名から抽出: {channel_extract_count}曲")
    print(f"アーティスト名を取得できなかった曲: {not_found_count}曲")

    # キャッシュを保存
    save_cache(songs_data)
    print("\n✓ youtube_stats.json を更新しました")

    # ランキングを再計算
    print("\nランキングを再計算中...")
    rankings = create_rankings(songs_data)
    save_rankings(rankings)
    print("✓ ランキングを保存しました")

    print("\n" + "="*60)
    print("完了！次のステップ:")
    print("  3. CSV出力 → 7. 全て更新してCSV出力")
    print("="*60)


if __name__ == '__main__':
    main()
