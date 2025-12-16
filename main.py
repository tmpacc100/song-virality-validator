import datetime
import calendar
import csv
import json
import os
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# YouTube API設定（複数のキーをリストで管理）
YOUTUBE_API_KEYS = [
    "AIzaSyCJGKejEe2kWJL2_OaXgqP2__jndZEy588",
    "AIzaSyAYjocbnNJabLlrdAoi5ynmTZ05TOgumwE",
    "AIzaSyAxpi2HcJx88xGFnK0Dl1fs55Ge_wWye2s",
    "AIzaSyAau11IT5KoG-GMEEjph5PnIgLzcEPc3bg",
    "AIzaSyB4mI2gLeVQ38FJmc-LB2iAhgM4lmvRwXg",
    "AIzaSyAyZ1CX-itALbov6ehkcTbzOcYOU41Xhpc",
    "AIzaSyC7qvI2c0TDCBtOJAUDeXl6i17VVN-SEBI",
    "AIzaSyBj5AIrkv1wTUfa6VQK2ur8Ldx4h8IoETo",
    "AIzaSyBURv-z_cInwFq5pYNCr4CpJkvqLyMKCkI",
    "AIzaSyAnf54Nc8N6LP605ce1i-XESRV6an2WXFw",
    "AIzaSyDWfhm7MB6lyoU5QOLXs3dw6JDeCuTo_Gw",
    "AIzaSyCmIltqc6DQdmP5tYAUpTWRYmBQpFVXUvw",
    "AIzaSyBR1XE02737tE2sPvjcCzpji0sS7N4pvhA",
    "AIzaSyAAR8KMXFCKNzKVN6ZOI7auUC1R0PiffNs",
    "AIzaSyBZFye-ujRnbHVtIluKMNQZ_6CIQymRg2g",
    "AIzaSyBRGbHlkw9AoXC6vkFHxqUAUuxhErBhoQM",
    "AIzaSyAVU6CKXYGA3xXW8CeIoZgMujQqYl0eAqM",
    "AIzaSyDsny--LjcpRYFpMFCa2rAGZNrAatxHAZE",
    "AIzaSyDcA4yi9a6rmozfXQ7P9luYyXK9m8hewrY",
]

# 現在使用中のAPIキーのインデックス
current_api_key_index = 0
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEYS[current_api_key_index])


def switch_to_next_api_key():
    """次のYouTube APIキーに切り替える

    Returns:
        bool: 切り替えに成功した場合True、全てのキーを使い切った場合False
    """
    global current_api_key_index, youtube

    current_api_key_index += 1

    if current_api_key_index >= len(YOUTUBE_API_KEYS):
        return False  # 全てのキーを使い切った

    # 新しいキーでYouTubeクライアントを再構築
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEYS[current_api_key_index])
    print(f"\n🔑 APIキーを切り替えました（キー {current_api_key_index + 1}/{len(YOUTUBE_API_KEYS)}）")

    return True

# キャッシュファイル（RAW DATAディレクトリに保存）
CACHE_FILE = 'RAW DATA/Youtube_API_raw.json'
RANKINGS_FILE = 'rankings.json'
TASKS_FILE = 'tasks.json'


def load_cache():
    """キャッシュを読み込む"""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_cache(data):
    """キャッシュを保存"""
    # RAW DATAディレクトリを作成
    os.makedirs('RAW DATA', exist_ok=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_cache_valid(cached_date_str):
    """キャッシュが1日以内かチェック"""
    cached_date = datetime.datetime.fromisoformat(cached_date_str)
    now = datetime.datetime.now(datetime.timezone.utc)
    delta = now - cached_date
    return delta.total_seconds() < 86400  # 24時間


def extract_artist_from_title(video_title):
    """動画タイトルからアーティスト名を抽出

    優先順位:
    1. 【artist】pattern → artist（ノイズ除去）
    2. artist - song pattern → artist
    3. / artist : pattern → artist
    4. / artist pattern → artist（ノイズ除去）

    Args:
        video_title: YouTube動画のタイトル

    Returns:
        抽出されたアーティスト名、または None
    """
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


# def fetch_pianogame_artists():
#     """PianoGameサーバーからアーティスト情報を取得
#
#     Returns:
#         dict: {曲名: アーティスト名} の辞書
#     """
#     from bs4 import BeautifulSoup
#
#     username = 'shii'
#     password = '0619'
#     notifications_url = 'https://pianogame-server.herokuapp.com/notifications'
#
#     artists_dict = {}
#
#     try:
#         # Basic認証でアクセス
#         print("  PianoGameサーバーからアーティスト情報を取得中...")
#         response = requests.get(notifications_url, auth=(username, password))
#
#         if response.status_code != 200:
#             print(f"  ⚠ サーバーアクセス失敗: {response.status_code}")
#             return artists_dict
#
#         soup = BeautifulSoup(response.text, 'html.parser')
#
#         # テーブルから情報を抽出
#         table = soup.find('table')
#         if table:
#             rows = table.find_all('tr')[1:]  # ヘッダー行をスキップ
#
#             for row in rows:
#                 cols = row.find_all('td')
#                 if len(cols) >= 5:
#                     body = cols[2].get_text(strip=True)  # "Body"列
#                     song_name = cols[4].get_text(strip=True)  # "Song"列
#
#                     # Body列から「アーティスト名「曲名」を追加しました」を抽出
#                     # 形式: アーティスト名「曲名」を追加しました！ぜひあそんでみてね♪
#                     # または: たくさんのリクエストの中からアーティスト名「曲名」を追加しました
#
#                     # 「」の直前のアーティスト名を抽出（最後の「の前の部分）
#                     # まず「曲名」のパターンを探す
#                     match = re.search(r'([^「」]+)「[^」]+」を追加しました', body)
#                     if match:
#                         # マッチした部分からアーティスト名を抽出
#                         # "たくさんのリクエストの中からSaucy Dog" → "Saucy Dog"
#                         artist_part = match.group(1)
#                         # "から"または"で"の後ろを取得、なければ全体
#                         artist = re.split(r'(?:から|で)', artist_part)[-1].strip()
#                         if artist:
#                             artists_dict[song_name] = artist
#
#         print(f"  ✓ PianoGameから {len(artists_dict)} 曲のアーティスト情報を取得しました")
#
#     except Exception as e:
#         print(f"  ⚠ PianoGameサーバーからの取得に失敗: {e}")
#
#     return artists_dict


def fetch_taikogame_artists():
    """TaikoGameサーバーから曲情報を取得

    Returns:
        tuple: (artists_dict, songs_list)
            - artists_dict: {曲名: アーティスト名} の辞書（後方互換性のため）
            - songs_list: 全14列のデータを含む辞書のリスト
    """
    username = 'shii'
    password = '0619'
    songs_url = 'https://taikogame-server.herokuapp.com/songs'

    artists_dict = {}
    songs_list = []

    try:
        print("  TaikoGameサーバーから曲情報を取得中...")
        response = requests.get(songs_url, auth=(username, password))

        if response.status_code != 200:
            print(f"  ⚠ サーバーアクセス失敗: {response.status_code}")
            return artists_dict, songs_list

        # HTMLをパース
        soup = BeautifulSoup(response.text, 'html.parser')

        # テーブルから情報を抽出
        table = soup.find('table')
        if not table:
            print("  ⚠ テーブルが見つかりません")
            return artists_dict, songs_list

        rows = table.find_all('tr')[1:]  # ヘッダー行をスキップ

        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 12:  # リリース状態列まで存在することを確認
                # cols[0]=ID, cols[1]=リリース日, cols[2]=Title, cols[3]=ふりがな
                # cols[4]=編集, cols[5]=タグ, cols[6]=データ, cols[7]=Jasrac code
                # cols[8]=難易度, cols[9]=youtube, cols[10]=ダウンロード, cols[11]=リリース状態

                # リリース状態を取得
                release_status = cols[11].get_text(strip=True)

                # フィルタリングなし - 全ての曲を取得
                # （以前は「リリース」または「開発中」のみだった）

                # 全12列を取得
                id_value = cols[0].get_text(strip=True)
                release_date = cols[1].get_text(strip=True)
                title_text = cols[2].get_text(separator='\n')
                furigana = cols[3].get_text(strip=True)
                edit = cols[4].get_text(strip=True)
                tags = cols[5].get_text(strip=True)
                data = cols[6].get_text(strip=True)
                jasrac_code = cols[7].get_text(strip=True)
                difficulty = cols[8].get_text(strip=True)
                youtube = cols[9].get_text(strip=True)
                download = cols[10].get_text(strip=True)

                # 改行で分割してアーティスト名と曲名を抽出
                # 構造: 行1=曲名, 行2=アーティスト名, 行3=アーティスト読み, 行4=主題歌情報
                lines = [line.strip() for line in title_text.split('\n') if line.strip()]

                song_name = ''
                artist_name = ''

                if len(lines) >= 2:
                    # 行1: 曲名
                    song_name = lines[0]
                    # 行2: アーティスト名
                    artist_name = lines[1]

                if song_name and artist_name:
                    artists_dict[song_name] = artist_name

                # 全データを保存
                songs_list.append({
                    'id': id_value,
                    'release_date': release_date,
                    'title': title_text.replace('\n', ' '),
                    'furigana': furigana,
                    'edit': edit,
                    'tags': tags,
                    'data': data,
                    'jasrac_code': jasrac_code,
                    'difficulty': difficulty,
                    'youtube': youtube,
                    'download': download,
                    'release_status': release_status,
                    'song_name': song_name if song_name else '',
                    'artist_name': artist_name if artist_name else ''
                })

        print(f"  ✓ TaikoGameから {len(songs_list)} 曲のデータを取得しました（全ての曲を含む）")
        print(f"    アーティスト名が抽出できた曲: {len(artists_dict)}曲")

    except Exception as e:
        print(f"  ⚠ TaikoGameサーバーからの取得に失敗: {e}")
        import traceback
        traceback.print_exc()

    return artists_dict, songs_list


def fetch_itunes_artist(song_name):
    """iTunes APIから曲のアーティスト名を取得

    Args:
        song_name: 曲名

    Returns:
        str: アーティスト名、見つからない場合はNone
    """
    try:
        # iTunes Search API
        base_url = 'https://itunes.apple.com/search'
        params = {
            'term': song_name,
            'country': 'JP',  # 日本のストア
            'media': 'music',
            'entity': 'song',
            'limit': 5  # 上位5件を取得
        }

        response = requests.get(base_url, params=params, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()
        results = data.get('results', [])

        if not results:
            return None

        # 最初の結果からアーティスト名を取得
        # trackNameが曲名と一致するものを優先
        for result in results:
            track_name = result.get('trackName', '')
            artist_name = result.get('artistName', '')

            # 曲名が部分一致する場合はそのアーティストを返す
            if song_name.lower() in track_name.lower() or track_name.lower() in song_name.lower():
                return artist_name

        # 完全一致がない場合は最初の結果を返す
        return results[0].get('artistName')

    except Exception:
        # iTunes APIエラーは無視してNoneを返す（フォールバックが動作する）
        return None


def update_artist_names_in_data(songs_data):
    """アーティスト名を複数のソースから取得して更新

    優先順位:
    1. TaikoGameから取得したアーティスト名（最優先）
    2. 動画タイトルから抽出したアーティスト名（フォールバック）

    Args:
        songs_data: 曲データのリスト（各要素は辞書）

    Returns:
        更新された曲データのリスト
    """
    # TaikoGameからアーティスト情報を取得
    print("\n" + "="*60)
    print("TaikoGameサーバーからアーティスト情報を取得")
    print("="*60)
    taikogame_artists, taikogame_full_data = fetch_taikogame_artists()

    updated_count = 0
    taikogame_count = 0
    # itunes_count = 0
    title_extraction_count = 0

    for song in songs_data:
        song_name = song.get('song_name', '')
        video_title = song.get('video_title', '')
        original_artist = song.get('artist_name', '')
        new_artist = None
        source = ''

        # 優先順位1: TaikoGameから取得（最優先）
        if song_name in taikogame_artists:
            new_artist = taikogame_artists[song_name]
            source = 'TaikoGame'
            taikogame_count += 1

        # # 優先順位2: iTunes APIから取得（コメントアウト）
        # if not new_artist and song_name:
        #     itunes_artist = fetch_itunes_artist(song_name)
        #     if itunes_artist:
        #         new_artist = itunes_artist
        #         source = 'iTunes API'
        #         itunes_count += 1

        # 優先順位2: 動画タイトルから抽出（フォールバック）
        if not new_artist:
            new_artist = extract_artist_from_title(video_title, song_name)
            if new_artist:
                source = '動画タイトル'
                title_extraction_count += 1

        # アーティスト名を更新
        if new_artist and original_artist != new_artist:
            song['artist_name'] = new_artist
            updated_count += 1
            print(f"  更新: {original_artist} → {new_artist} (ソース: {source}, 曲: {song_name})")

    print(f"\n" + "="*60)
    print(f"アーティスト名更新結果:")
    print(f"  - TaikoGameから取得: {taikogame_count}曲")
    # print(f"  - iTunes APIから取得: {itunes_count}曲")
    print(f"  - 動画タイトルから抽出: {title_extraction_count}曲")
    print(f"  - 更新された曲数: {updated_count}曲")
    print("="*60)

    return songs_data


def search_youtube_video(song_name):
    """曲名でYouTube動画を検索して最も関連性の高い動画IDとタイトルを取得"""
    import time

    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"  - 検索クエリ: {song_name}")
            search_response = youtube.search().list(
                q=song_name,
                part='id,snippet',
                maxResults=5,
                type='video'
            ).execute()

            print(f"  - 検索結果数: {len(search_response.get('items', []))}")

            if search_response['items']:
                video = search_response['items'][0]
                video_id = video['id']['videoId']
                video_title = video['snippet']['title']
                print(f"  - 選択された動画: {video_title} (ID: {video_id})")
                return video_id, video_title
            else:
                print(f"  - 検索結果が見つかりませんでした")
                return None, None
        except HttpError as e:
            # クオータエラーをチェック
            if e.resp.status == 403 and 'quotaExceeded' in str(e):
                print(f"  - ⚠ APIクオータ制限に達しました")
                # 次のAPIキーに切り替え
                if switch_to_next_api_key():
                    print(f"  - リトライします...")
                    continue  # 同じ曲で再試行
                else:
                    print(f"  - ✗ 全てのAPIキーを使い切りました")
                    raise  # クオータエラーを上位に伝播

            print(f"  - YouTube検索エラー: {e}")
            if attempt < max_retries - 1:
                print(f"  - リトライ {attempt + 1}/{max_retries - 1}...")
                time.sleep(2)
            else:
                return None, None
        except Exception as e:
            print(f"  - ネットワークエラー: {type(e).__name__}: {e}")
            if attempt < max_retries - 1:
                print(f"  - リトライ {attempt + 1}/{max_retries - 1}...")
                time.sleep(2)
            else:
                print(f"  - 最大リトライ回数に達しました。スキップします。")
                return None, None

    return None, None


def get_video_stats(video_id):
    """YouTube動画の統計情報を取得"""
    import time

    max_retries = 3
    for attempt in range(max_retries):
        try:
            video_response = youtube.videos().list(
                id=video_id,
                part='statistics,snippet'
            ).execute()

            if not video_response['items']:
                return None

            video = video_response['items'][0]
            stats = video['statistics']
            snippet = video['snippet']

            # 動画タイトルとチャンネル名を取得
            video_title = snippet.get('title', '')
            channel_title = snippet.get('channelTitle', '')

            published_at = snippet['publishedAt']
            published_date = datetime.datetime.fromisoformat(published_at.replace('Z', '+00:00'))

            now = datetime.datetime.now(datetime.timezone.utc)
            days_since_published = (now - published_date).days
            if days_since_published == 0:
                days_since_published = 1

            view_count = int(stats.get('viewCount', 0))
            like_count = int(stats.get('likeCount', 0))
            comment_count = int(stats.get('commentCount', 0))

            support_rate = (like_count / view_count * 100) if view_count > 0 else 0
            growth_rate = view_count / days_since_published

            return {
                'video_id': video_id,
                'video_title': video_title,
                'channel_title': channel_title,
                'view_count': view_count,
                'like_count': like_count,
                'comment_count': comment_count,
                'support_rate': support_rate,
                'growth_rate': growth_rate,
                'days_since_published': days_since_published,
                'published_date': published_at,
                'fetched_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
        except HttpError as e:
            # クオータエラーをチェック
            if e.resp.status == 403 and 'quotaExceeded' in str(e):
                print(f"  - ⚠ APIクオータ制限に達しました")
                # 次のAPIキーに切り替え
                if switch_to_next_api_key():
                    print(f"  - リトライします...")
                    continue  # 同じ動画で再試行
                else:
                    print(f"  - ✗ 全てのAPIキーを使い切りました")
                    raise  # クオータエラーを上位に伝播

            print(f"  - 動画統計取得エラー ({video_id}): {e}")
            if attempt < max_retries - 1:
                print(f"  - リトライ {attempt + 1}/{max_retries - 1}...")
                time.sleep(2)
            else:
                return None
        except Exception as e:
            print(f"  - ネットワークエラー ({video_id}): {type(e).__name__}: {e}")
            if attempt < max_retries - 1:
                print(f"  - リトライ {attempt + 1}/{max_retries - 1}...")
                time.sleep(2)
            else:
                print(f"  - 最大リトライ回数に達しました。スキップします。")
                return None

    return None


def process_songs_from_csv(csv_file, use_cache=True, force_refresh=False):
    """CSVファイルから曲名を読み込み、YouTubeデータを取得

    Args:
        csv_file: CSVファイルのパス
        use_cache: キャッシュを使用するか
        force_refresh: Trueの場合、キャッシュを無視して再取得
    """
    songs_data = []
    cache = {item['song_name']: item for item in load_cache()} if (use_cache and not force_refresh) else {}

    # 処理中に保存する間隔（曲数）
    SAVE_INTERVAL = 10
    processed_count = 0

    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # TaikoGameのCSV形式に対応 (song_name列を使用)
                song_name = row.get('song_name', '').strip()
                release_date = row.get('release_date', '').strip()  # ML/RLスケジューリング用
                if not song_name:
                    continue

                print(f"処理中: {song_name}")

                # キャッシュチェック（force_refreshがTrueの場合はスキップ）
                if use_cache and not force_refresh and song_name in cache:
                    cached_item = cache[song_name]
                    if 'fetched_at' in cached_item and is_cache_valid(cached_item['fetched_at']):
                        print(f"  - キャッシュを使用")
                        songs_data.append(cached_item)
                        continue

                try:
                    # YouTube動画を検索
                    video_id, search_title = search_youtube_video(song_name)
                    if not video_id:
                        print(f"  - 動画が見つかりませんでした")
                        continue

                    # 動画統計を取得
                    stats = get_video_stats(video_id)
                    if not stats:
                        print(f"  - 統計情報を取得できませんでした")
                        continue

                except HttpError as e:
                    # YouTube APIのクオータエラーをチェック
                    if e.resp.status == 403 and 'quotaExceeded' in str(e):
                        print(f"\n⚠ 全てのYouTube APIキー（{len(YOUTUBE_API_KEYS)}個）のクオータ制限に達しました")
                        print(f"✓ ここまでに取得した {len(songs_data)} 曲のデータを保存します...")
                        save_cache(songs_data)
                        print(f"✓ データを保存しました: {CACHE_FILE}")
                        print(f"\n💡 ヒント: 翌日になるとクオータがリセットされます")
                        return songs_data
                    else:
                        print(f"  - YouTube APIエラー: {e}")
                        continue
                except Exception as e:
                    print(f"  - エラーが発生しました: {e}")
                    continue

                # アーティスト名取得の優先順位:
                # 1. iTunes Search API (exactマッチのみ)
                # 2. 動画タイトルから抽出
                # 3. iTunes Search API (candidateも使用)
                # 4. チャンネル名から抽出

                video_title = stats.get('video_title', search_title or '')
                channel_title = stats.get('channel_title', '')

                # 1. iTunes Search APIで検索（動画情報を渡して精度向上）
                itunes_artist, itunes_confidence = get_artist_from_itunes(song_name, video_title, channel_title)

                # exactマッチの場合はそのまま使用
                if itunes_confidence == "exact":
                    artist_name = itunes_artist
                else:
                    # 2. タイトルから抽出を試みる
                    print(f"  📺 タイトルから抽出を試みます")
                    artist_name = extract_artist_from_title(video_title, song_name)

                    # 3. タイトルから抽出できず、iTunesに候補がある場合は候補を使用
                    if not artist_name and itunes_confidence == "candidate":
                        artist_name = itunes_artist

                # アーティスト名に日本語とアルファベットが混在している場合、日本語のみ抽出
                if artist_name and re.search(r'[ぁ-んァ-ヶー一-龯]', artist_name):
                    # 末尾のアルファベットを削除
                    japanese_artist = re.sub(r'\s*[A-Za-z\s]+$', '', artist_name).strip()
                    # 先頭のアルファベットも削除
                    japanese_artist = re.sub(r'^[A-Za-z\s]+\s*', '', japanese_artist).strip()
                    if japanese_artist:
                        artist_name = japanese_artist

                # 3. タイトルから抽出できない場合は、チャンネル名を使用
                # ただし、チャンネル名が曲名と同じ場合は使用しない
                if not artist_name and channel_title:
                    print(f"  📢 チャンネル名から抽出を試みます")
                    # チャンネル名が曲名と違う場合のみ使用
                    if channel_title.lower() != song_name.lower():
                        # 「チャンネル」や「channel」が含まれている場合、その前の部分を抽出
                        cleaned_channel = channel_title
                        if 'チャンネル' in channel_title:
                            cleaned_channel = channel_title.split('チャンネル')[0].strip()
                        elif 'channel' in channel_title.lower():
                            # 大文字小文字を区別せずに分割
                            match = re.search(r'(.+?)\s*channel', channel_title, re.IGNORECASE)
                            if match:
                                cleaned_channel = match.group(1).strip()

                        # 日本語とアルファベットが混在している場合、日本語部分のみを抽出
                        # 例: "米津玄師  Kenshi Yonezu" -> "米津玄師"
                        # 例: "Kenshi Yonezu  米津玄師" -> "米津玄師"
                        if re.search(r'[ぁ-んァ-ヶー一-龯]', cleaned_channel):  # 日本語が含まれているか
                            # 日本語とアルファベットが混在している場合
                            # 末尾のアルファベットを削除
                            japanese_part = re.sub(r'\s*[A-Za-z\s]+$', '', cleaned_channel).strip()
                            # 先頭のアルファベットも削除
                            japanese_part = re.sub(r'^[A-Za-z\s]+\s*', '', japanese_part).strip()
                            if japanese_part:
                                cleaned_channel = japanese_part

                        # クリーン後のチャンネル名が空でない場合のみ使用
                        if cleaned_channel:
                            artist_name = cleaned_channel

                song_data = {
                    'song_name': song_name,
                    'artist_name': artist_name,
                    'release_date': release_date,  # ML/RLスケジューリング用
                    'video_id': video_id,
                    **stats
                }
                songs_data.append(song_data)
                processed_count += 1

                print(f"  - 完了: アーティスト={artist_name or '(不明)'}, チャンネル={channel_title}, 再生数={stats['view_count']:,}, 支持率={stats['support_rate']:.2f}%")

                # 定期的にデータを保存（SAVE_INTERVAL曲ごと）
                if processed_count % SAVE_INTERVAL == 0:
                    print(f"\n💾 {processed_count}曲処理完了。中間データを保存中...")
                    save_cache(songs_data)
                    print(f"✓ 保存完了: {CACHE_FILE}\n")

    except KeyboardInterrupt:
        print(f"\n\n⚠ 処理が中断されました")
        print(f"✓ ここまでに取得した {len(songs_data)} 曲のデータを保存します...")
        save_cache(songs_data)
        print(f"✓ データを保存しました: {CACHE_FILE}")
        return songs_data
    except Exception as e:
        print(f"\n\n⚠ 予期しないエラーが発生しました: {e}")
        print(f"✓ ここまでに取得した {len(songs_data)} 曲のデータを保存します...")
        save_cache(songs_data)
        print(f"✓ データを保存しました: {CACHE_FILE}")
        return songs_data

    return songs_data


def create_rankings(songs_data):
    """各メトリックごとのランキングと総合ランキングを作成"""
    if not songs_data:
        return {}

    rankings = {
        'popularity': sorted(songs_data, key=lambda x: x['view_count'], reverse=True),
        'support_rate': sorted(songs_data, key=lambda x: x['support_rate'], reverse=True),
        'engagement': sorted(songs_data, key=lambda x: x['comment_count'], reverse=True),
        'growth_rate': sorted(songs_data, key=lambda x: x['growth_rate'], reverse=True)
    }

    song_scores = {}
    for song in songs_data:
        song_name = song['song_name']
        total_rank = 0
        for metric_name, ranked_songs in rankings.items():
            rank = next(i for i, s in enumerate(ranked_songs) if s['song_name'] == song_name)
            total_rank += rank
        song_scores[song_name] = total_rank

    overall_ranking = sorted(songs_data, key=lambda x: song_scores[x['song_name']])
    rankings['overall'] = overall_ranking

    return rankings


def get_artist_from_itunes(song_name, video_title="", channel_title=""):
    """iTunes Search APIからアーティスト名を取得

    Args:
        song_name: 曲名
        video_title: 動画タイトル（オプション、マッチング精度向上に使用）
        channel_title: チャンネル名（オプション、マッチング精度向上に使用）

    Returns:
        tuple: (アーティスト名, 確度) - 確度は "exact" または "candidate" または ""
    """
    try:
        # 曲名をURLエンコード
        encoded_song = urllib.parse.quote(song_name)
        url = f"https://itunes.apple.com/search?term={encoded_song}&country=jp&media=music&limit=10"

        print(f"  🎵 iTunes APIで検索中: {song_name}")
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])

            if results:
                # 動画タイトルやチャンネル名に含まれるアーティストを優先
                matched_artists = []
                for result in results:
                    artist = result.get('artistName', '')
                    track = result.get('trackName', '')

                    # 曲名が一致しない場合はスキップ
                    if not (song_name.lower() in track.lower() or track.lower() in song_name.lower()):
                        continue

                    # アーティスト名と曲名が同じ場合はスキップ（誤検出）
                    if not artist or artist.lower() == song_name.lower():
                        continue

                    # 動画タイトルやチャンネル名にアーティスト名が含まれているかチェック
                    artist_in_video = video_title and artist.lower() in video_title.lower()
                    artist_in_channel = channel_title and artist.lower() in channel_title.lower()

                    if artist_in_video or artist_in_channel:
                        print(f"  ✅ iTunes APIで発見（動画情報と一致）: {artist}")
                        return artist, "exact"

                    matched_artists.append(artist)

                # 動画情報との一致がない場合、最初の一致したアーティストを返す
                if matched_artists:
                    print(f"  ✅ iTunes APIで発見: {matched_artists[0]}")
                    return matched_artists[0], "exact"

                # 部分一致もない場合は最初の結果を候補として返す
                first_artist = results[0].get('artistName', '')
                if first_artist and first_artist.lower() != song_name.lower():
                    print(f"  ℹ️  iTunes APIで候補発見（確度低）: {first_artist}")
                    return first_artist, "candidate"

        print(f"  ❌ iTunes APIで見つかりませんでした")
        return "", ""

    except Exception as e:
        print(f"  ⚠️  iTunes API エラー: {e}")
        return "", ""


def extract_artist_from_title(video_title, song_name):
    """動画タイトルからアーティスト名を抽出

    様々なパターンに対応:
    - "アーティスト名 - 曲名"
    - "アーティスト名「曲名」"
    - "アーティスト名の「曲名」"
    - "アーティスト名 / 曲名"
    - "【アーティスト名】曲名"
    - "曲名 / アーティスト名"
    """
    import re

    # 不要な接尾辞を除去するリスト
    suffixes_to_remove = ['弾いてみた', '歌ってみた', 'を弾いてみた', 'を歌ってみた',
                          'cover', 'Cover', 'COVER', 'Piano', 'piano', 'ピアノ',
                          '(ノンテロップver)', 'ノンテロップver', 'ノンテロップ']

    # タイトルをクリーンアップ
    clean_title = video_title
    for suffix in suffixes_to_remove:
        clean_title = clean_title.replace(suffix, '')

    # パターン1: "アーティスト名 - 曲名"
    if ' - ' in clean_title:
        parts = clean_title.split(' - ', 1)
        artist = parts[0].strip()
        # 【】を除去
        artist = re.sub(r'【.*?】', '', artist).strip()
        if artist and artist not in ['MV', 'Official', 'official']:
            return artist

    # パターン2: "アーティスト名「曲名」" または "アーティスト名の「曲名」"
    if '「' in clean_title:
        parts = clean_title.split('「', 1)
        artist = parts[0].strip()
        # "の" で終わる場合は除去
        if artist.endswith('の'):
            artist = artist[:-1].strip()
        # 【】を除去
        artist = re.sub(r'【.*?】', '', artist).strip()
        if artist:
            return artist

    # パターン2-2: "アーティスト名『曲名』" (全角の引用符)
    if '『' in clean_title:
        parts = clean_title.split('『', 1)
        artist = parts[0].strip()
        # "の" で終わる場合は除去
        if artist.endswith('の'):
            artist = artist[:-1].strip()
        # 【】を除去
        artist = re.sub(r'【.*?】', '', artist).strip()
        if artist and artist not in ['MV', 'Official', 'official']:
            return artist

    # パターン3: "【MV】グループ名『曲名』"
    mv_pattern = re.search(r'【MV】\s*([^『]+)『', clean_title)
    if mv_pattern:
        artist = mv_pattern.group(1).strip()
        if artist and artist not in ['MV', 'Official', 'official']:
            return artist

    # パターン4: "アーティスト名 / 曲名"
    if ' / ' in clean_title:
        parts = clean_title.split(' / ')
        # 最初の部分がアーティスト名の可能性が高い
        artist = parts[0].strip()
        artist = re.sub(r'【.*?】', '', artist).strip()
        if artist and artist not in ['MV', 'Official', 'official']:
            return artist

    # パターン5: "【アーティスト名】曲名"
    bracket_match = re.search(r'【([^】]+)】', clean_title)
    if bracket_match:
        artist = bracket_match.group(1).strip()
        if artist and artist not in ['MV', 'Official', 'official', 'Cover', 'cover']:
            return artist

    # パターン6: "曲名 / アーティスト名" (逆パターン)
    if ' / ' in clean_title:
        parts = clean_title.split(' / ')
        if len(parts) >= 2:
            # 2番目の部分をチェック
            artist = parts[1].strip()
            artist = re.sub(r'【.*?】', '', artist).strip()
            if artist:
                return artist

    # パターン7: タイトルが曲名と同じ場合、何もしない（アーティスト名なし）
    if clean_title.strip() == song_name:
        return ""

    # 抽出できない場合は空文字列
    return ""


def save_rankings(rankings):
    """ランキングをJSON形式で保存"""
    rankings_output = {}
    for metric_key, ranked_songs in rankings.items():
        rankings_output[metric_key] = [
            {
                'rank': i + 1,
                'song_name': song['song_name'],
                'artist_name': song.get('artist_name', ''),
                'video_id': song['video_id'],
                'video_title': song.get('video_title', ''),
                'release_date': song.get('release_date', ''),  # ML/RL用
                'metrics': {
                    'view_count': song['view_count'],
                    'like_count': song['like_count'],
                    'support_rate': round(song['support_rate'], 2),
                    'comment_count': song['comment_count'],
                    'growth_rate': round(song['growth_rate'], 1),
                    'days_since_published': song['days_since_published']
                },
                'ml_predictions': {  # ML/RL予測結果
                    'optimal_posting_datetime': song.get('optimal_posting_datetime', ''),
                    'predicted_view_count': song.get('predicted_view_count', 0),
                    'confidence_score': round(song.get('confidence_score', 0.0), 3)
                }
            }
            for i, song in enumerate(ranked_songs)
        ]

    with open(RANKINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(rankings_output, f, ensure_ascii=False, indent=2)


def fetch_new_videos():
    """1. 新動画fetch"""
    global current_api_key_index, youtube

    # APIキーインデックスをリセット
    current_api_key_index = 0
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEYS[current_api_key_index])

    print("\n" + "="*60)
    print("新動画データを取得します")
    print("="*60)
    print(f"使用可能なAPIキー数: {len(YOUTUBE_API_KEYS)}")

    # 手動再取得オプション
    print("\n取得方法:")
    print("1. キャッシュを使用（1日以内のデータは再利用）")
    print("2. 全て再取得（キャッシュを無視）")
    choice = input("\n選択 (1/2, デフォルト=1): ").strip()

    force_refresh = (choice == '2')
    if force_refresh:
        print("\n⚠ 全ての曲を再取得します（API使用量に注意）")

        # 既存のキャッシュファイルを削除
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
            print(f"✓ 既存のキャッシュファイルを削除しました: {CACHE_FILE}")

        # 古いyoutube_stats.jsonも削除（互換性のため）
        old_cache_file = 'youtube_stats.json'
        if os.path.exists(old_cache_file):
            os.remove(old_cache_file)
            print(f"✓ 古いキャッシュファイルを削除しました: {old_cache_file}")

    # 未投稿フィルター済みCSVを使用
    csv_file = 'filtered data/taiko_server_未投稿_filtered.csv'
    print(f"\n使用するCSV: {csv_file}")

    if not os.path.exists(csv_file):
        print(f"\nエラー: {csv_file} が見つかりません")
        print("先にYouTubeチャンネルフィルタリングを実行してください:")
        print("  python3 filter_youtube_channel.py")
        return

    songs_data = process_songs_from_csv(csv_file, use_cache=True, force_refresh=force_refresh)

    if not songs_data:
        print("データが取得できませんでした。")
        return

    # 動画タイトルからアーティスト名を抽出して更新
    print("\n" + "="*60)
    print("動画タイトルからアーティスト名を抽出中...")
    print("="*60)
    songs_data = update_artist_names_in_data(songs_data)

    save_cache(songs_data)
    print(f"\nデータをキャッシュに保存しました（{len(songs_data)}曲）")

    rankings = create_rankings(songs_data)
    save_rankings(rankings)
    print(f"ランキングを保存しました")


def manage_tasks():
    """2. タスク管理"""
    if not os.path.exists(RANKINGS_FILE):
        print("\nエラー: ランキングデータがありません。先に「1. 新動画fetch」を実行してください。")
        return

    with open(RANKINGS_FILE, 'r', encoding='utf-8') as f:
        rankings = json.load(f)

    overall = rankings.get('overall', [])
    if not overall:
        print("\n総合ランキングが空です。")
        return

    # タスクファイルを読み込み
    tasks = load_tasks()

    while True:
        print("\n" + "="*60)
        print("タスク管理 - 総合ランキング")
        print("="*60)

        for i, item in enumerate(overall[:10], 1):
            song_name = item['song_name']
            task_status = tasks.get(song_name, {})
            recording = "✓" if task_status.get('recording') else "　"
            editing = "✓" if task_status.get('editing') else "　"
            posting = "✓" if task_status.get('posting') else "　"

            print(f"{i:2d}. {song_name}")
            print(f"    [{recording}] 画面収録  [{editing}] 編集  [{posting}] 投稿")

        print("\n操作:")
        print("曲番号を入力してタスクを更新 (例: 1)")
        print("0: 戻る")

        choice = input("\n選択: ").strip()

        if choice == '0':
            break

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(overall):
                update_task(overall[idx]['song_name'], tasks)
        except ValueError:
            print("無効な入力です")


def load_tasks():
    """タスクを読み込む"""
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_tasks(tasks):
    """タスクを保存"""
    with open(TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


def update_task(song_name, tasks):
    """タスクを更新"""
    if song_name not in tasks:
        tasks[song_name] = {'recording': False, 'editing': False, 'posting': False}

    task = tasks[song_name]

    print(f"\n{song_name} のタスク:")
    print(f"1. 画面収録 [{'✓' if task['recording'] else ' '}]")
    print(f"2. 編集 [{'✓' if task['editing'] else ' '}]")
    print(f"3. 投稿 [{'✓' if task['posting'] else ' '}]")
    print("4. 全てクリア")

    choice = input("トグルする項目 (1-4): ").strip()

    if choice == '1':
        task['recording'] = not task['recording']
    elif choice == '2':
        task['editing'] = not task['editing']
    elif choice == '3':
        task['posting'] = not task['posting']
    elif choice == '4':
        task['recording'] = False
        task['editing'] = False
        task['posting'] = False

    save_tasks(tasks)
    print("タスクを更新しました")


def export_csv():
    """3. CSV出力"""
    if not os.path.exists(RANKINGS_FILE):
        print("\nエラー: ランキングデータがありません。先に「1. 新動画fetch」を実行してください。")
        return

    print("\n" + "="*60)
    print("CSV出力")
    print("="*60)
    print("1. Overall (総合ランキング)")
    print("2. Popularity (人気度)")
    print("3. Support Rate (支持率)")
    print("4. Engagement (エンゲージメント)")
    print("5. Growth Rate (急上昇度)")
    print("6. All (統合版)")
    print("7. 🔄 全て更新してCSV出力（ランキング再計算）")
    print("0. 戻る")

    choice = input("\n選択: ").strip()

    ranking_types = {
        '1': 'overall',
        '2': 'popularity',
        '3': 'support_rate',
        '4': 'engagement',
        '5': 'growth_rate'
    }

    if choice in ranking_types:
        export_single_ranking(ranking_types[choice])
    elif choice == '6':
        export_all_rankings()
    elif choice == '7':
        update_and_export_all()
    elif choice != '0':
        print("無効な選択です")


def export_single_ranking(ranking_type):
    """個別ランキングをCSVに出力"""
    with open(RANKINGS_FILE, 'r', encoding='utf-8') as f:
        rankings = json.load(f)

    if ranking_type not in rankings:
        print(f"エラー: {ranking_type} ランキングが見つかりません")
        return

    filename = f"ranking_{ranking_type}.csv"

    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            '順位', 'release_date', 'アーティスト名', '曲名', '動画タイトル', 'Video ID', '再生数', '高評価数',
            '支持率(%)', 'コメント数', '急上昇度(views/day)', '公開日数',
            '最適投稿日時', '予測視聴数', '信頼度スコア'
        ])

        for item in rankings[ranking_type]:
            ml_pred = item.get('ml_predictions', {})
            writer.writerow([
                item['rank'],
                item.get('release_date', ''),
                item.get('artist_name', ''),
                item['song_name'],
                item.get('video_title', ''),
                item['video_id'],
                item['metrics']['view_count'],
                item['metrics']['like_count'],
                item['metrics']['support_rate'],
                item['metrics']['comment_count'],
                item['metrics']['growth_rate'],
                item['metrics']['days_since_published'],
                ml_pred.get('optimal_posting_datetime', ''),
                ml_pred.get('predicted_view_count', ''),
                ml_pred.get('confidence_score', '')
            ])

    print(f"\n{filename} を作成しました ({len(rankings[ranking_type])}曲)")


def export_all_rankings():
    """全ランキングを統合してCSVに出力"""
    with open(RANKINGS_FILE, 'r', encoding='utf-8') as f:
        rankings = json.load(f)

    # TaikoGameのID情報を読み込み
    song_id_map = {}
    taiko_csv_path = 'RAW DATA/taiko_server_raw.csv'
    if os.path.exists(taiko_csv_path):
        with open(taiko_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                song_name = row.get('song_name', '').strip()
                song_id = row.get('id', '').strip()
                if song_name and song_id:
                    song_id_map[song_name] = song_id
        print(f"  📝 TaikoGame ID情報: {len(song_id_map)}曲分を読み込みました")
    else:
        print(f"  ⚠ 警告: {taiko_csv_path} が見つかりません。IDカラムは空になります。")

    all_songs = {}

    for metric_key in ['popularity', 'support_rate', 'engagement', 'growth_rate', 'overall']:
        if metric_key not in rankings:
            continue

        for item in rankings[metric_key]:
            song_name = item['song_name']
            if song_name not in all_songs:
                all_songs[song_name] = {
                    'artist_name': item.get('artist_name', ''),
                    'video_title': item.get('video_title', ''),
                    'video_id': item['video_id'],
                    'release_date': item.get('release_date', ''),  # ML/RL用
                    'metrics': item['metrics'],
                    'ml_predictions': item.get('ml_predictions', {}),  # ML/RL予測結果
                    'ranks': {}
                }
            all_songs[song_name]['ranks'][metric_key] = item['rank']

    filename = 'ranking_all.csv'

    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        # IDカラムを先頭に追加、ML/RL列を追加
        writer.writerow([
            'id', 'release_date', 'アーティスト名', '曲名', '動画タイトル', 'Video ID', '再生数', '高評価数', '支持率(%)',
            'コメント数', '急上昇度(views/day)', '公開日数',
            '人気度順位', '支持率順位', 'エンゲージメント順位', '急上昇度順位', '総合順位',
            '最適投稿日時', '予測視聴数', '信頼度スコア'
        ])

        sorted_songs = sorted(
            all_songs.items(),
            key=lambda x: x[1]['ranks'].get('overall', 999)
        )

        matched_count = 0
        for song_name, data in sorted_songs:
            song_id = song_id_map.get(song_name, '')
            if song_id:
                matched_count += 1

            ml_pred = data.get('ml_predictions', {})
            writer.writerow([
                song_id,  # 曲IDを先頭に追加
                data.get('release_date', ''),  # release_date追加
                data.get('artist_name', ''),
                song_name,
                data.get('video_title', ''),
                data['video_id'],
                data['metrics']['view_count'],
                data['metrics']['like_count'],
                data['metrics']['support_rate'],
                data['metrics']['comment_count'],
                data['metrics']['growth_rate'],
                data['metrics']['days_since_published'],
                data['ranks'].get('popularity', '-'),
                data['ranks'].get('support_rate', '-'),
                data['ranks'].get('engagement', '-'),
                data['ranks'].get('growth_rate', '-'),
                data['ranks'].get('overall', '-'),
                ml_pred.get('optimal_posting_datetime', ''),  # ML/RL: 最適投稿日時
                ml_pred.get('predicted_view_count', ''),  # ML/RL: 予測視聴数
                ml_pred.get('confidence_score', '')  # ML/RL: 信頼度スコア
            ])

    print(f"\n{filename} を作成しました (全{len(all_songs)}曲)")
    print(f"  ✓ TaikoGame IDとマッチング: {matched_count}/{len(all_songs)}曲")
    if matched_count < len(all_songs):
        print(f"  ⚠ {len(all_songs) - matched_count}曲のIDが見つかりませんでした")


def update_and_export_all():
    """ランキングを再計算してから全CSVを出力"""
    print("\n" + "="*60)
    print("🔄 ランキング再計算 & 全CSV出力")
    print("="*60)
    print("最新のyoutube_stats.jsonからランキングを再計算し、")
    print("全てのCSVファイルを更新します。")
    print("="*60)

    confirm = input("\n実行しますか？ (yes/no): ").strip().lower()

    if confirm != 'yes':
        print("キャンセルしました")
        return

    # youtube_stats.jsonの存在確認
    if not os.path.exists(CACHE_FILE):
        print(f"\nエラー: {CACHE_FILE} が見つかりません")
        return

    # キャッシュを読み込み
    print(f"\n📂 {CACHE_FILE} を読み込み中...")
    songs_data = load_cache()
    print(f"✓ {len(songs_data)}曲のデータを読み込みました")

    # ランキングを再計算
    print("\n📊 ランキングを再計算中...")
    rankings = create_rankings(songs_data)
    save_rankings(rankings)
    print("✓ ランキングを保存しました")

    # 全てのCSVを出力
    print("\n📝 CSVファイルを生成中...")

    # 各ランキングタイプのCSVを作成
    csv_count = 0
    for ranking_type in ['popularity', 'support_rate', 'engagement', 'growth_rate', 'overall']:
        if ranking_type in rankings:
            export_single_ranking(ranking_type)
            csv_count += 1

    # 統合版CSVを作成
    export_all_rankings()
    csv_count += 1

    print("\n" + "="*60)
    print(f"✅ 完了！ {csv_count}個のCSVファイルを更新しました")
    print("="*60)


def scrape_titles():
    """4. タイトルスクレイピング（API不要）"""
    print("\n" + "="*60)
    print("タイトルスクレイピング")
    print("="*60)
    print("1. 全曲スクレイピング")
    print("2. 指定曲数スクレイピング")
    print("0. 戻る")

    choice = input("\n選択: ").strip()

    if choice == '1':
        import subprocess
        print("\n全曲のタイトルをスクレイピングします...")
        subprocess.run(['python3', 'scrape_titles.py'])
    elif choice == '2':
        limit = input("処理する曲数を入力: ").strip()
        try:
            limit_num = int(limit)
            import subprocess
            print(f"\n最初の{limit_num}曲のタイトルをスクレイピングします...")
            subprocess.run(['python3', 'scrape_titles_limited.py', str(limit_num)])
        except ValueError:
            print("無効な数値です")
    elif choice != '0':
        print("無効な選択です")


def generate_videos():
    """5. 動画生成"""
    print("\n" + "="*60)
    print("動画生成")
    print("="*60)
    print("1. 単一動画生成")
    print("2. バッチ動画生成（CSVから）")
    print("0. 戻る")

    choice = input("\n選択: ").strip()

    if choice == '1':
        from batch_video_generator_layers import LayerBasedBatchVideoGenerator

        artist = input("アーティスト名: ").strip()
        song = input("曲名: ").strip()

        # アーティスト名を含めるか確認
        include_artist_input = input("アーティスト名を含めますか？ (y/n, デフォルト: y): ").strip().lower()
        include_artist = include_artist_input != 'n'

        # ベース動画ファイルを指定
        print("\nベース動画ファイルを指定してください")
        print("（複数指定する場合はカンマ区切り、例: video1.mp4,video2.mp4）")
        print("（デフォルト: output/{曲名}.mp4 または base.mp4）")
        base_video_input = input("ベース動画ファイル: ").strip()

        base_videos = []
        if base_video_input:
            # カンマ区切りで複数のファイルを取得
            base_videos = [v.strip() for v in base_video_input.split(',') if v.strip()]

            # ファイルの存在確認
            for video in base_videos:
                if not os.path.exists(video):
                    print(f"警告: {video} が見つかりません")

        # 出力ディレクトリ
        output_dir = 'output_videos'

        # 動画生成
        generator = LayerBasedBatchVideoGenerator('template.json', 'base.mp4')

        if not base_videos:
            # ベース動画が指定されていない場合、デフォルトの動作
            print(f"\n動画を生成しています...")
            video_path = generator.generate_single_video(
                artist, song, output_dir,
                include_artist=include_artist
            )
            if video_path:
                print(f"\n✓ 動画生成完了: {video_path}")
        else:
            # 複数のベース動画が指定されている場合、それぞれで生成
            print(f"\n{len(base_videos)}個のベース動画で生成します")
            for i, base_video in enumerate(base_videos, 1):
                if not os.path.exists(base_video):
                    print(f"スキップ: {base_video}（ファイルが見つかりません）")
                    continue

                # 出力ファイル名にベース動画名を含める
                base_name = os.path.splitext(os.path.basename(base_video))[0]
                video_name = f"{artist}_{song}_{base_name}.mp4"

                print(f"\n[{i}/{len(base_videos)}] ベース動画: {base_video}")
                video_path = generator.generate_single_video(
                    artist, song, output_dir,
                    video_name=video_name,
                    base_video_override=base_video,
                    include_artist=include_artist
                )
                if video_path:
                    print(f"✓ 動画生成完了: {video_path}")

    elif choice == '2':
        csv_file = input("CSVファイルパス (デフォルト: ranking_all.csv): ").strip()
        if not csv_file:
            csv_file = 'ranking_all.csv'

        if not os.path.exists(csv_file):
            print(f"エラー: {csv_file} が見つかりません")
            return

        import subprocess
        print(f"\n{csv_file}から動画を生成しています...")
        subprocess.run(['python3', 'batch_video_generator_layers.py', csv_file])
    elif choice != '0':
        print("無効な選択です")


def refetch_with_artists():
    """6. アーティスト名のみ更新（API不要）"""
    print("\n" + "="*60)
    print("アーティスト名のみ更新（YouTube API不使用）")
    print("="*60)
    print("既存のデータからアーティスト名のみを更新します")
    print("（動画タイトル、チャンネル名、再生数などは変更されません）")

    confirm = input("\n実行しますか？ (yes/no): ").strip().lower()

    if confirm == 'yes':
        import subprocess
        subprocess.run(['python3', 'update_artists_only.py'])
    else:
        print("キャンセルしました")


def search_artist_itunes():
    """7. iTunes APIで全曲アーティスト更新"""
    print("\n" + "="*60)
    print("iTunes APIで全曲アーティスト更新")
    print("="*60)
    print("⚠️  全ての曲をiTunes APIで検索してアーティスト名を更新します")

    confirm = input("\n実行しますか？ (yes/no): ").strip().lower()

    if confirm == 'yes':
        import subprocess
        subprocess.run(['python3', 'update_artists_itunes.py'])
    else:
        print("キャンセルしました")


def fetch_taikogame_to_csv():
    """8. TaikoGameデータ取得・CSV保存"""
    print("\n" + "="*60)
    print("TaikoGameサーバーから全データ取得")
    print("="*60)

    print("\nTaikoGameサーバーから全ての曲データを取得してCSVに保存します")
    print("（全てのリリース状態の曲を含む）")

    confirm = input("\n実行しますか？ (yes/no): ").strip().lower()

    if confirm != 'yes':
        print("キャンセルしました")
        return

    # TaikoGameから全データを取得
    print("\n" + "="*60)
    taikogame_artists, taikogame_full_data = fetch_taikogame_artists()

    if not taikogame_full_data:
        print("\n⚠ データが取得できませんでした")
        return

    # CSVに保存
    output_file = 'RAW DATA/taiko_server_raw.csv'

    # RAW DATAディレクトリを作成
    os.makedirs('RAW DATA', exist_ok=True)

    fieldnames = [
        'id',
        'release_date',
        'title',
        'furigana',
        'edit',
        'tags',
        'data',
        'jasrac_code',
        'difficulty',
        'youtube',
        'download',
        'release_status',
        'song_name',
        'artist_name'
    ]

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(taikogame_full_data)

    print(f"\n✓ {output_file} に保存しました")
    print(f"  取得曲数: {len(taikogame_full_data)}曲")
    print("="*60)


def ml_rl_schedule_optimization():
    """10. ML/RLスケジュール最適化"""
    print("\n" + "="*60)
    print("🤖 ML/RLスケジュール最適化")
    print("="*60)

    # 必要なモジュールをインポート
    try:
        from feature_engineering import FeatureEngineer
        from ml_scheduler import ViewCountPredictor
        from rl_scheduler import optimize_schedule
    except ImportError as e:
        print(f"\nエラー: 必要なモジュールをインポートできません: {e}")
        print("requirements.txtの依存関係をインストールしてください:")
        print("  pip install -r requirements.txt")
        return

    # 1. データ読み込み
    print("\n" + "-"*60)
    print("ステップ1: データ読み込み")
    print("-"*60)

    if not os.path.exists(RANKINGS_FILE):
        print(f"エラー: {RANKINGS_FILE} が見つかりません")
        print("先にオプション1で新動画fetchを実行してください")
        return

    with open(RANKINGS_FILE, 'r', encoding='utf-8') as f:
        rankings = json.load(f)

    # 全曲データを取得（overallランキングから）
    if 'overall' not in rankings:
        print("エラー: overallランキングが見つかりません")
        return

    songs_data = []
    for item in rankings['overall']:
        song = {
            'song_name': item['song_name'],
            'artist_name': item.get('artist_name', ''),
            'video_id': item['video_id'],
            'release_date': item.get('release_date', ''),
            'view_count': item['metrics']['view_count'],
            'like_count': item['metrics']['like_count'],
            'comment_count': item['metrics']['comment_count'],
            'support_rate': item['metrics']['support_rate'],
            'growth_rate': item['metrics']['growth_rate'],
            'days_since_published': item['metrics']['days_since_published']
        }
        songs_data.append(song)

    print(f"✓ {len(songs_data)}曲のデータを読み込みました")

    # TaikoGameデータを読み込み（タグ情報用）
    taiko_data_map = {}
    taiko_csv = 'filtered data/taiko_server_未投稿_filtered.csv'
    if os.path.exists(taiko_csv):
        try:
            import csv
            with open(taiko_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    song_name = row.get('song_name', '').strip()
                    if song_name:
                        taiko_data_map[song_name] = row
            print(f"✓ TaikoGameデータ {len(taiko_data_map)}曲を読み込みました")
        except Exception as e:
            print(f"警告: TaikoGameデータ読み込みエラー: {e}")

    # 2. 特徴量エンジニアリング
    print("\n" + "-"*60)
    print("ステップ2: 特徴量エンジニアリング")
    print("-"*60)

    engineer = FeatureEngineer()
    target_datetime = datetime.datetime.now()

    try:
        X, y, feature_names = engineer.prepare_training_data(
            songs_data,
            taiko_data_map,
            target_datetime
        )
        print(f"✓ 特徴量を生成しました")
        print(f"  - サンプル数: {len(X)}")
        print(f"  - 特徴量数: {len(feature_names)}")
    except Exception as e:
        print(f"エラー: 特徴量生成に失敗しました: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. ML View Predictor訓練
    print("\n" + "-"*60)
    print("ステップ3: Deep Learning視聴数予測モデル訓練")
    print("-"*60)

    try:
        predictor = ViewCountPredictor(input_dim=X.shape[1])

        # モデル訓練
        predictor.train(
            X, y,
            epochs=100,
            validation_split=0.2,
            use_augmentation=True,
            verbose=1
        )

        # モデル保存
        predictor.save()

        print("\n✓ ML予測モデルの訓練が完了しました")

    except Exception as e:
        print(f"エラー: ML訓練に失敗しました: {e}")
        import traceback
        traceback.print_exc()
        return

    # 4. RLスケジュール最適化
    print("\n" + "-"*60)
    print("ステップ4: Reinforcement Learningスケジュール最適化")
    print("-"*60)

    try:
        # 最適スケジュールを生成
        optimized_schedule = optimize_schedule(
            songs_data=songs_data,
            view_predictor=predictor,
            num_episodes=500
        )

        print(f"\n✓ 最適スケジュールを生成しました: {len(optimized_schedule)}曲")

    except Exception as e:
        print(f"エラー: RL最適化に失敗しました: {e}")
        import traceback
        traceback.print_exc()
        return

    # 5. 結果を反映
    print("\n" + "-"*60)
    print("ステップ5: 結果をrankings.jsonに反映")
    print("-"*60)

    # 曲名 -> ML予測結果のマッピング
    ml_results_map = {}
    for song, posting_datetime, predicted_views, confidence in optimized_schedule:
        ml_results_map[song['song_name']] = {
            'optimal_posting_datetime': posting_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'predicted_view_count': int(predicted_views),
            'confidence_score': float(confidence)
        }

    # rankings.jsonを更新
    updated_count = 0
    for metric_key in rankings:
        for item in rankings[metric_key]:
            song_name = item['song_name']
            if song_name in ml_results_map:
                # ML予測結果を追加
                if 'ml_predictions' not in item:
                    item['ml_predictions'] = {}
                item['ml_predictions'].update(ml_results_map[song_name])

                # song_data自体にも追加（後方互換性のため）
                item['optimal_posting_datetime'] = ml_results_map[song_name]['optimal_posting_datetime']
                item['predicted_view_count'] = ml_results_map[song_name]['predicted_view_count']
                item['confidence_score'] = ml_results_map[song_name]['confidence_score']
                updated_count += 1

    # rankings.jsonを保存
    with open(RANKINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(rankings, f, ensure_ascii=False, indent=2)

    print(f"✓ {RANKINGS_FILE} を更新しました（{updated_count}件）")

    # 6. 結果サマリー表示
    print("\n" + "="*60)
    print("📊 最適化結果サマリー")
    print("="*60)

    total_predicted_views = sum(predicted_views for _, _, predicted_views, _ in optimized_schedule)
    avg_confidence = sum(confidence for _, _, _, confidence in optimized_schedule) / len(optimized_schedule)

    print(f"\n処理曲数: {len(optimized_schedule)}曲")
    print(f"総予測視聴回数: {total_predicted_views:,.0f} views")
    print(f"平均信頼度: {avg_confidence*100:.1f}%")

    # 今週の投稿スケジュール（上位10件）
    print("\n今週の推奨投稿スケジュール（予測視聴数トップ10）:")
    sorted_schedule = sorted(
        optimized_schedule,
        key=lambda x: x[2],  # predicted_views is the 3rd element
        reverse=True
    )[:10]

    for i, (song, posting_datetime, predicted_views, confidence) in enumerate(sorted_schedule, 1):
        print(f"  {i}. {posting_datetime.strftime('%Y-%m-%d %H:%M')} - 「{song['song_name']}」{song.get('artist_name', '')}")
        print(f"     予測: {predicted_views:,.0f} views (信頼度: {confidence*100:.0f}%)")

    # CSV再出力を推奨
    print("\n" + "="*60)
    print("💡 次のステップ:")
    print("  - オプション3でCSVを再出力すると、ML/RL結果が反映されます")
    print("="*60)


def open_template():
    """9. テンプレート編集"""
    import subprocess

    editor_script = 'template_editor_layers.py'

    if not os.path.exists(editor_script):
        print(f"\nエラー: {editor_script} が見つかりません")
        return

    print("\n" + "="*60)
    print("テンプレートエディタを起動します")
    print("="*60)

    try:
        subprocess.run(['python3', editor_script])
    except Exception as e:
        print(f"エラー: エディタを起動できませんでした - {e}")


def main():
    """メインメニュー"""
    while True:
        print("\n" + "="*60)
        print("YouTube曲バイラリティ分析ツール")
        print("="*60)
        print("1. 新動画fetch（YouTube API）")
        print("2. タスク管理")
        print("3. CSV出力")
        print("4. タイトルスクレイピング（API不要）")
        print("5. 動画生成")
        print("6. アーティスト名のみ更新（API不要）")
        print("7. iTunes APIで全曲アーティスト更新")
        print("8. TaikoGameデータ取得・CSV保存")
        print("9. テンプレート編集")
        print("10. 🤖 ML/RLスケジュール最適化")
        print("0. 終了")

        choice = input("\n選択: ").strip()

        if choice == '1':
            fetch_new_videos()
        elif choice == '2':
            manage_tasks()
        elif choice == '3':
            export_csv()
        elif choice == '4':
            scrape_titles()
        elif choice == '5':
            generate_videos()
        elif choice == '6':
            refetch_with_artists()
        elif choice == '7':
            search_artist_itunes()
        elif choice == '8':
            fetch_taikogame_to_csv()
        elif choice == '9':
            open_template()
        elif choice == '10':
            ml_rl_schedule_optimization()
        elif choice == '0':
            print("\n終了します")
            break
        else:
            print("\n無効な選択です。0-10 のいずれかを入力してください。")


if __name__ == '__main__':
    main()
