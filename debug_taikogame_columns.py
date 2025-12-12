#!/usr/bin/env python3
"""TaikoGameサーバーのテーブル構造をデバッグ"""
import requests
from bs4 import BeautifulSoup

username = 'shii'
password = '0619'
songs_url = 'https://taikogame-server.herokuapp.com/songs'

print("TaikoGameサーバーからテーブル構造を確認中...")
response = requests.get(songs_url, auth=(username, password))

if response.status_code != 200:
    print(f"エラー: {response.status_code}")
    exit(1)

soup = BeautifulSoup(response.text, 'html.parser')
table = soup.find('table')

if not table:
    print("テーブルが見つかりません")
    exit(1)

# ヘッダー行を取得
header_row = table.find('tr')
headers = header_row.find_all('th')

print("\nテーブルヘッダー:")
for i, header in enumerate(headers):
    print(f"  cols[{i}] = {header.get_text(strip=True)}")

# 最初のデータ行を取得
data_rows = table.find_all('tr')[1:]
if data_rows:
    first_row = data_rows[0]
    cols = first_row.find_all('td')

    print(f"\n最初のデータ行（{len(cols)}列）:")
    for i, col in enumerate(cols):
        text = col.get_text(separator='|', strip=True)[:100]
        print(f"  cols[{i}] = {text}")
