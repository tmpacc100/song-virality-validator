#!/usr/bin/env python3
"""Test script to verify song ID-based video file search"""

import csv
import os

# ranking_all.csvの最初の5曲をテスト
print("="*70)
print("曲IDベースのMP4ファイル検索テスト")
print("="*70)

video_source_dir = 'output'

with open('ranking_all.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)

    for i, row in enumerate(reader):
        if i >= 5:  # 最初の5曲のみ
            break

        song_id = row.get('id', '').strip()
        song_name = row.get('曲名', '').strip()
        artist = row.get('アーティスト名', '').strip()

        print(f"\n[曲 {i+1}]")
        print(f"  アーティスト: {artist}")
        print(f"  曲名: {song_name}")
        print(f"  ID: {song_id or '(なし)'}")

        # 優先順位1: 曲IDで検索
        found = False
        if song_id:
            song_id_path = os.path.join(video_source_dir, f"{song_id}.mp4")
            if os.path.exists(song_id_path):
                print(f"  ✓ 曲IDで発見: {song_id_path}")
                found = True
            else:
                print(f"  ✗ 曲IDで見つからず: {song_id_path}")

        # 優先順位2: 曲名で検索
        if not found:
            song_name_path = os.path.join(video_source_dir, f"{song_name}.mp4")
            if os.path.exists(song_name_path):
                print(f"  ✓ 曲名で発見: {song_name_path}")
                found = True
            else:
                print(f"  ✗ 曲名でも見つからず: {song_name_path}")

        # 優先順位3: デフォルト
        if not found:
            print(f"  → デフォルトbase.mp4を使用")

print("\n" + "="*70)
print("テスト完了")
print("="*70)
