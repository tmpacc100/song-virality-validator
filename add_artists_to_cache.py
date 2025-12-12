#!/usr/bin/env python3
"""既存のキャッシュにアーティスト名を追加するスクリプト（API不要）"""

import json
from main import extract_artist_from_title, save_cache, create_rankings, save_rankings

def main():
    print("="*60)
    print("既存データにアーティスト名を追加します（API不要）")
    print("="*60)

    # youtube_stats.jsonを読み込む
    try:
        with open('youtube_stats.json', 'r', encoding='utf-8') as f:
            songs_data = json.load(f)
    except FileNotFoundError:
        print("エラー: youtube_stats.json が見つかりません")
        return

    print(f"\n読み込み: {len(songs_data)}曲")

    # 各曲にアーティスト名を追加
    updated_count = 0
    for song in songs_data:
        song_name = song.get('song_name', '')
        video_title = song.get('video_title', '')

        # video_titleがない場合はスキップ
        if not video_title:
            song['artist_name'] = ''
            continue

        # タイトルからアーティスト名を抽出
        artist_name = extract_artist_from_title(video_title, song_name)
        song['artist_name'] = artist_name

        if artist_name:
            updated_count += 1
            print(f"  ✓ {song_name}: {artist_name}")
        else:
            print(f"  - {song_name}: アーティスト名なし")

    print(f"\n結果: {updated_count}/{len(songs_data)}曲にアーティスト名を追加しました")

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
