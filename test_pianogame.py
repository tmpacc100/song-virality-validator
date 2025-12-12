#!/usr/bin/env python3
"""PianoGameサーバーからのアーティスト情報取得テスト"""
import re
import requests
from bs4 import BeautifulSoup

def fetch_pianogame_artists():
    """PianoGameサーバーからアーティスト情報を取得"""
    username = 'shii'
    password = '0619'
    login_url = 'https://pianogame-server.herokuapp.com/users/sign_in'
    notifications_url = 'https://pianogame-server.herokuapp.com/notifications'

    artists_dict = {}

    try:
        # セッションを作成
        session = requests.Session()

        # ログインページを取得してCSRFトークンを抽出
        print("PianoGameサーバーにログイン中...")
        response = session.get(login_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # CSRFトークンを取得
        csrf_token = soup.find('meta', {'name': 'csrf-token'})
        if csrf_token:
            csrf_token = csrf_token.get('content')
            print(f"CSRFトークン取得: {csrf_token[:20]}...")

        # ログイン
        login_data = {
            'user[email]': username,
            'user[password]': password,
            'authenticity_token': csrf_token
        }
        login_response = session.post(login_url, data=login_data)
        print(f"ログイン応答: {login_response.status_code}")

        # 通知ページを取得
        print("\nアーティスト情報を取得中...")
        response = session.get(notifications_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # テーブルから情報を抽出
        table = soup.find('table')
        if table:
            print("テーブル発見")
            rows = table.find_all('tr')[1:]  # ヘッダー行をスキップ
            print(f"データ行数: {len(rows)}")

            for i, row in enumerate(rows[:10], 1):  # 最初の10行のみ表示
                cols = row.find_all('td')
                if len(cols) >= 5:
                    released_at = cols[0].get_text(strip=True)
                    headline = cols[1].get_text(strip=True)
                    body = cols[2].get_text(strip=True)
                    url = cols[3].get_text(strip=True)
                    song_name = cols[4].get_text(strip=True)

                    print(f"\n{i}. 曲名: {song_name}")
                    print(f"   Body: {body}")

                    # Body列から「アーティスト名「曲名」」を抽出
                    match = re.match(r'^(.+?)「(.+?)」', body)
                    if match:
                        artist = match.group(1).strip()
                        song_in_body = match.group(2).strip()
                        artists_dict[song_name] = artist
                        print(f"   抽出されたアーティスト: {artist}")
                    else:
                        print(f"   抽出失敗")
        else:
            print("テーブルが見つかりません")

        print(f"\n✓ PianoGameから {len(artists_dict)} 曲のアーティスト情報を取得しました")
        print("\n取得したデータ:")
        for song, artist in list(artists_dict.items())[:10]:
            print(f"  {song}: {artist}")

    except Exception as e:
        print(f"⚠ エラー: {e}")
        import traceback
        traceback.print_exc()

    return artists_dict


if __name__ == '__main__':
    fetch_pianogame_artists()
