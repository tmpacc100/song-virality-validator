#!/usr/bin/env python3
import re

test_titles = [
    ("WATCH ME!YOASOBIよあそびアニメ「ウィッチウォッチ」オープニングテーマ", "うぉっちみー"),
    ("らしさOfficial髭男dismおふぃしゃるひげだんでぃずむ劇場アニメ「ひゃくえむ。」主題歌", "らしさ"),
    ("SO BADKing GnuきんぐぬーUSJ『ハロウィーン・ホラー・ナイト』『ゾンビ・デ・ダンス』テーマソング", "そーばっど"),
    ("カイコ feat. 初音ミクDECO*27", "かいこ"),
]

for title, furigana in test_titles:
    print(f"\nTitle: {title}")
    print(f"ふりがな: {furigana}")

    # すべてのひらがな連続部分を見つける
    hiragana_matches = list(re.finditer(r'[ぁ-ん]+', title))
    print(f"ひらがな連続: {[m.group() for m in hiragana_matches]}")

    if len(hiragana_matches) >= 2:
        second_hira = hiragana_matches[1]
        before_artist_yomi = title[:second_hira.start()]
        print(f"2番目ひらがなの前: '{before_artist_yomi}'")

        # 曲名とアーティスト名を分離
        match_eng = re.match(r'^([A-Za-z0-9\s!?\-\'"〜♪・]+)', before_artist_yomi)
        if match_eng:
            song = match_eng.group(1).strip()
            artist = before_artist_yomi[len(song):].strip()
            print(f"→ 曲名: {song}, アーティスト: {artist}")
