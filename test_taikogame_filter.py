#!/usr/bin/env python3
"""TaikoGameフィルタリングテスト"""
import sys
sys.path.insert(0, '/Users/shii/Desktop/song virality validator')

from main import fetch_taikogame_artists

print("=" * 70)
print("TaikoGameアーティスト情報取得テスト（リリース状態フィルタあり）")
print("=" * 70)

# TaikoGameからアーティスト情報を取得
artists_dict = fetch_taikogame_artists()

print(f"\n取得した曲数: {len(artists_dict)}")

# 最初の10件を表示
print("\n最初の10件:")
for i, (song, artist) in enumerate(list(artists_dict.items())[:10], 1):
    print(f"{i}. 曲名: {song}")
    print(f"   アーティスト: {artist}")

print("\n=" * 70)
print("テスト完了")
print("=" * 70)
