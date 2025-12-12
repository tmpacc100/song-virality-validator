#!/usr/bin/env python3
"""TaikoGameデータをフィルタリング: リリース済み・開発中のみ抽出"""
import csv
import os

def filter_released_songs():
    """リリース済みと開発中の曲のみを抽出してCSVに保存"""

    input_file = 'RAW DATA/taiko_server_raw.csv'
    output_dir = 'filtered data'
    output_file = os.path.join(output_dir, 'taiko_server_リリース_開発中_filtered.csv')

    # 出力ディレクトリを作成
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 70)
    print("TaikoGameデータフィルタリング")
    print("=" * 70)
    print(f"\n入力: {input_file}")
    print(f"出力: {output_file}")
    print("\nフィルタ条件: リリース状態が「リリース」または「開発中」")

    if not os.path.exists(input_file):
        print(f"\nエラー: {input_file} が見つかりません")
        print("先にメインメニューの「8. TaikoGameデータ取得・CSV保存」を実行してください")
        return

    # 入力CSVを読み込み
    filtered_songs = []
    total_count = 0
    release_count = 0
    dev_count = 0

    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for row in reader:
            total_count += 1
            release_status = row.get('release_status', '')

            if release_status == 'リリース':
                filtered_songs.append(row)
                release_count += 1
            elif release_status == '開発中':
                filtered_songs.append(row)
                dev_count += 1

    # フィルタリング結果をCSVに保存
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered_songs)

    print("\n" + "=" * 70)
    print("フィルタリング結果:")
    print("=" * 70)
    print(f"  元データ: {total_count}曲")
    print(f"  リリース: {release_count}曲")
    print(f"  開発中: {dev_count}曲")
    print(f"  合計: {len(filtered_songs)}曲")
    print(f"\n✓ {output_file} に保存しました")
    print("=" * 70)


if __name__ == '__main__':
    filter_released_songs()
