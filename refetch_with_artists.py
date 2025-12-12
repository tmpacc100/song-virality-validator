#!/usr/bin/env python3
"""アーティスト名を含めてYouTubeデータを再取得するスクリプト"""

import sys
import os

# main.pyから必要な関数をインポート
from main import process_songs_from_csv, save_cache, create_rankings, save_rankings

def main():
    print("="*60)
    print("アーティスト名を含めてYouTubeデータを再取得します")
    print("="*60)
    print("\n⚠ 警告: 全ての曲を再取得します（API使用量に注意）\n")

    csv_file = 'songs.csv'

    if not os.path.exists(csv_file):
        print(f"エラー: {csv_file} が見つかりません")
        sys.exit(1)

    # force_refresh=True でキャッシュを無視して再取得
    print("YouTubeデータを取得中...\n")
    songs_data = process_songs_from_csv(csv_file, use_cache=True, force_refresh=True)

    if not songs_data:
        print("データが取得できませんでした。")
        sys.exit(1)

    # キャッシュを保存
    save_cache(songs_data)
    print(f"\n✓ データをキャッシュに保存しました（{len(songs_data)}曲）")

    # ランキングを計算
    print("\nランキングを計算中...")
    rankings = create_rankings(songs_data)

    # ランキングを保存
    save_rankings(rankings)
    print("✓ ランキングを保存しました")

    # アーティスト名が含まれているか確認
    print("\n確認: アーティスト名の取得状況")
    with_artist = sum(1 for song in songs_data if song.get('artist_name'))
    print(f"  - アーティスト名あり: {with_artist}/{len(songs_data)}曲")

    print("\n" + "="*60)
    print("完了！次のコマンドでCSVを生成してください:")
    print("  python3 json_to_csv.py")
    print("="*60)

if __name__ == '__main__':
    main()
