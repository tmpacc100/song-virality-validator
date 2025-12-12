#!/usr/bin/env python3
"""アーティスト名抽出機能のテスト"""
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

    # パターン2: artist - song（ハイフンの前）
    match = re.match(r'^(.+?)\s*[-−ー]\s*', video_title)
    if match:
        return match.group(1).strip()

    # パターン3: / artist :（スラッシュの後、コロンの前）
    match = re.search(r'/\s*(.+?)[:：]', video_title)
    if match:
        return match.group(1).strip()

    # パターン4: / artist（スラッシュの後）
    match = re.search(r'/\s*(.+?)$', video_title)
    if match:
        artist = match.group(1).strip()
        # MUSIC VIDEO、MV、括弧内などのノイズを除去
        artist = re.sub(r'\s*(MUSIC\s+VIDEO|MV|Official.*|[\(\（].*?[\)\）]).*$', '', artist, flags=re.IGNORECASE)
        return artist.strip() if artist else None

    # パターン5: artist 'song' または artist "song"（シングルクォート・ダブルクォートの前）
    match = re.match(r'^(.+?)\s+[\'""'']', video_title)
    if match:
        artist = match.group(1).strip()
        # feat.を含む場合はそこで切る
        artist = re.sub(r'\s+feat\..*$', '', artist, flags=re.IGNORECASE)
        return artist

    return None


# テストケース
test_cases = [
    ("【imase】NIGHT DANCER（MV）", "imase"),
    ("なとり - Overdose", "なとり"),
    ("【第75回NHK紅白歌合戦 歌唱曲】踊り子 / Vaundy：MUSIC VIDEO", "Vaundy"),
    ("米津玄師  Kenshi Yonezu - IRIS OUT", "米津玄師  Kenshi Yonezu"),
    ("【オリジナル楽曲】粛聖!! ロリ神レクイエム☆ / しぐれうい（9さい）【IOSYS（まろん&D.watt）】", "しぐれうい（9さい）"),
    ("Creepy Nuts - オトノケ(Otonoke) 【Official MV】 [Dandadan OP]", "Creepy Nuts"),
    ("廻廻奇譚 - Eve MV", "廻廻奇譚"),
    ("DECO*27 - モニタリング feat. 初音ミク", "DECO*27"),
    ("モエチャッカファイア / 弌誠：MUSIC VIDEO", "弌誠"),
    ("Chinozo 'グッバイ宣言' feat.FloweR", "Chinozo"),
]

print("=" * 70)
print("アーティスト名抽出テスト")
print("=" * 70)

passed = 0
failed = 0

for title, expected in test_cases:
    result = extract_artist_from_title(title)
    status = "✓" if result == expected else "✗"

    if result == expected:
        passed += 1
    else:
        failed += 1

    print(f"\n{status} タイトル: {title}")
    print(f"  期待値: {expected}")
    print(f"  結果  : {result}")

print("\n" + "=" * 70)
print(f"テスト結果: {passed}件成功、{failed}件失敗")
print("=" * 70)
