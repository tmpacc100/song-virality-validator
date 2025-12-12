#!/usr/bin/env python3
"""Test case-insensitive MP4 file search"""

import os

video_source_dir = 'output'
song_id = '10014802'
song_name = 'IRIS OUT'

print("="*70)
print("大文字小文字対応のMP4ファイル検索テスト")
print("="*70)

print(f"\n曲ID: {song_id}")
print(f"曲名: {song_name}")

# 優先順位1: 曲IDで検索（大文字小文字両方）
found = False
for ext in ['.mp4', '.MP4']:
    song_id_video_path = os.path.join(video_source_dir, f"{song_id}{ext}")
    print(f"\n検索: {song_id_video_path}")
    if os.path.exists(song_id_video_path):
        print(f"  ✓ 発見！")
        found = True
        break
    else:
        print(f"  ✗ 存在しない")

if not found:
    print("\n曲IDで見つからず、曲名で検索...")
    for ext in ['.mp4', '.MP4']:
        song_video_path = os.path.join(video_source_dir, f"{song_name}{ext}")
        print(f"\n検索: {song_video_path}")
        if os.path.exists(song_video_path):
            print(f"  ✓ 発見！")
            found = True
            break
        else:
            print(f"  ✗ 存在しない")

print("\n" + "="*70)
if found:
    print("結果: ✅ MP4ファイルが見つかりました")
else:
    print("結果: ❌ MP4ファイルが見つかりませんでした")
print("="*70)
