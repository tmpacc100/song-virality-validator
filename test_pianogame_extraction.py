#!/usr/bin/env python3
"""PianoGameのBody欄からのアーティスト名抽出テスト"""
import re

# テストケース：実際のBody欄のフォーマット
test_cases = [
    {
        'body': 'Saucy Dog「シンデレラボーイ」を追加しました！ぜひあそんでみてね♪',
        'expected': 'Saucy Dog',
        'song': 'シンデレラボーイ'
    },
    {
        'body': 'たくさんのリクエストの中からSaucy Dog「シンデレラボーイ」を追加しました',
        'expected': 'Saucy Dog',
        'song': 'シンデレラボーイ'
    },
    {
        'body': 'imase「NIGHT DANCER」を追加しました！ぜひあそんでみてね♪',
        'expected': 'imase',
        'song': 'NIGHT DANCER'
    },
    {
        'body': 'たくさんのリクエストの中からなとり「Overdose」を追加しました',
        'expected': 'なとり',
        'song': 'Overdose'
    },
    {
        'body': 'Vaundy「踊り子」を追加しました！',
        'expected': 'Vaundy',
        'song': '踊り子'
    },
]

print("=" * 70)
print("PianoGame Body欄からのアーティスト名抽出テスト")
print("=" * 70)

passed = 0
failed = 0

for i, test in enumerate(test_cases, 1):
    body = test['body']
    expected = test['expected']
    song = test['song']

    # 抽出ロジック
    match = re.search(r'([^「」]+)「[^」]+」を追加しました', body)
    if match:
        artist_part = match.group(1)
        # "から"または"で"の後ろを取得、なければ全体
        artist = re.split(r'(?:から|で)', artist_part)[-1].strip()
    else:
        artist = None

    # 検証
    if artist == expected:
        status = "✓"
        passed += 1
    else:
        status = "✗"
        failed += 1

    print(f"\n{i}. {status} Body: {body}")
    print(f"   期待値: {expected}")
    print(f"   結果  : {artist}")

print("\n" + "=" * 70)
print(f"テスト結果: {passed}件成功、{failed}件失敗")
print("=" * 70)
