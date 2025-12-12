#!/usr/bin/env python3
"""iTunes Search APIを使って全曲のアーティスト名を更新するスクリプト"""

import json
import time
from main import get_artist_from_itunes, save_cache, create_rankings, save_rankings


def main():
    print("="*60)
    print("iTunes APIで全曲のアーティスト名を更新します")
    print("="*60)

    # youtube_stats.jsonを読み込む
    try:
        with open('youtube_stats.json', 'r', encoding='utf-8') as f:
            songs_data = json.load(f)
    except FileNotFoundError:
        print("エラー: youtube_stats.json が見つかりません")
        print("先に動画データを取得してください")
        return

    print(f"\n読み込み: {len(songs_data)}曲")
    print("iTunes APIでアーティスト名を検索中...\n")

    # 各曲のアーティスト名をiTunes APIで検索
    updated_count = 0
    exact_match_count = 0
    candidate_match_count = 0
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

        # iTunes APIで検索（動画情報を渡して精度向上）
        itunes_artist, itunes_confidence = get_artist_from_itunes(song_name, video_title, channel_title)

        if itunes_artist:
            song['artist_name'] = itunes_artist
            updated_count += 1

            if itunes_confidence == "exact":
                exact_match_count += 1
            elif itunes_confidence == "candidate":
                candidate_match_count += 1

            if current_artist != itunes_artist:
                print(f"  ✏️  更新: {current_artist or '(なし)'} → {itunes_artist}")
        else:
            not_found_count += 1
            if current_artist:
                print(f"  ⚠️  iTunes APIで見つからず、既存のアーティスト名を保持: {current_artist}")
            else:
                print(f"  ❌ iTunes APIで見つかりませんでした")

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
    print(f"iTunes APIで見つかった曲: {updated_count}曲")
    print(f"  - 高精度マッチ（動画情報と一致）: {exact_match_count}曲")
    print(f"  - 候補マッチ: {candidate_match_count}曲")
    print(f"iTunes APIで見つからなかった曲: {not_found_count}曲")

    # キャッシュを保存
    save_cache(songs_data)
    print("\n✓ キャッシュを更新しました")

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
