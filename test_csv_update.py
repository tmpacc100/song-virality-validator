#!/usr/bin/env python3
"""CSVファイルのアーティスト名抽出テスト"""
import csv
import re

def extract_artist_from_title(video_title):
    """動画タイトルからアーティスト名を抽出"""
    if not video_title:
        return None

    # パターン1: 【artist】（角括弧内）
    match = re.search(r'【(.+?)】', video_title)
    if match:
        artist = match.group(1).strip()
        # ノイズワードを除去（番組名など）
        noise_words = ['第', '回', '歌合戦', 'NHK', '紅白', 'MV', 'MUSIC', 'Official', 'オリジナル楽曲', '歌唱曲']
        if not any(noise in artist for noise in noise_words):
            return artist

    # パターン2: artist｢song｣ または artist「song」（全角括弧の前）
    match = re.match(r'^([^\｢「]+)[｢「]', video_title)
    if match:
        return match.group(1).strip()

    # パターン3: artist - song（ハイフンの前）
    match = re.match(r'^(.+?)\s*[-−ー]\s*', video_title)
    if match:
        return match.group(1).strip()

    # パターン4: / artist :（スラッシュの後、コロンの前）
    match = re.search(r'/\s*(.+?)[:：]', video_title)
    if match:
        return match.group(1).strip()

    # パターン5: / artist（スラッシュの後）
    match = re.search(r'/\s*(.+?)$', video_title)
    if match:
        artist = match.group(1).strip()
        # MUSIC VIDEO、MV、括弧内などのノイズを除去
        artist = re.sub(r'\s*(MUSIC\s+VIDEO|MV|Official.*|[\(\（].*?[\)\）]).*$', '', artist, flags=re.IGNORECASE)
        return artist.strip() if artist else None

    # パターン6: artist 'song' または artist "song"（半角引用符の前、スペース必須）
    match = re.match(r'^(.+?)\s+[\'""'']', video_title)
    if match:
        artist = match.group(1).strip()
        # feat.を含む場合はそこで切る
        artist = re.sub(r'\s+feat\..*$', '', artist, flags=re.IGNORECASE)
        return artist

    return None


# ranking_all.csvを読み込んでテスト
print("=" * 80)
print("CSV実データでのアーティスト名抽出テスト")
print("=" * 80)

csv_file = 'ranking_all.csv'
updated_count = 0
no_change_count = 0
no_extract_count = 0

with open(csv_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"\n総曲数: {len(rows)}\n")

for i, row in enumerate(rows[:20], 1):  # 最初の20曲を表示
    original_artist = row['アーティスト名']
    video_title = row['動画タイトル']
    extracted_artist = extract_artist_from_title(video_title)

    if extracted_artist:
        if original_artist != extracted_artist:
            updated_count += 1
            print(f"{i}. 🔄 更新")
            print(f"   元: {original_artist}")
            print(f"   新: {extracted_artist}")
            print(f"   動画タイトル: {video_title[:60]}...")
        else:
            no_change_count += 1
            print(f"{i}. ✓ 変更なし: {original_artist}")
    else:
        no_extract_count += 1
        print(f"{i}. ⚠ 抽出不可: {original_artist} (タイトル: {video_title[:50]}...)")

print("\n" + "=" * 80)
print(f"結果サマリー（最初の20曲）:")
print(f"  更新: {updated_count}曲")
print(f"  変更なし: {no_change_count}曲")
print(f"  抽出不可: {no_extract_count}曲")
print("=" * 80)
