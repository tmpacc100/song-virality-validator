#!/usr/bin/env python3
"""TaikoGame HTMLデバッグ"""
import requests
from bs4 import BeautifulSoup

username = 'shii'
password = '0619'
songs_url = 'https://taikogame-server.herokuapp.com/songs'

response = requests.get(songs_url, auth=(username, password))

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')

    if table:
        # ヘッダー行を確認
        headers = table.find('tr')
        if headers:
            print("ヘッダー:")
            for i, th in enumerate(headers.find_all(['th', 'td'])):
                print(f"  列{i}: {th.get_text(strip=True)}")

        print("\n最初の5データ行:")
        rows = table.find_all('tr')[1:6]  # 最初の5行
        for row_idx, row in enumerate(rows, 1):
            print(f"\n行 {row_idx}:")
            cols = row.find_all('td')
            # <br>タグを改行に変換
            title_with_br = cols[2].get_text(separator='\n') if len(cols) > 2 else ''
            furigana = cols[3].get_text(strip=True) if len(cols) > 3 else ''

            print(f"  Title (cols[2]) with separator:")
            print(f"  {repr(title_with_br)}")  # 改行を表示するためにrepr()を使用
            print(f"  ふりがな (cols[3]): {furigana}")

            # 改行で分割
            lines = [line.strip() for line in title_with_br.split('\n') if line.strip()]
            if lines:
                print(f"  分割された行数: {len(lines)}")
                for i, line in enumerate(lines, 1):
                    print(f"    行{i}: {line}")
