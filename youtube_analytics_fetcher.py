#!/usr/bin/env python3
"""
YouTube Analytics API データ取得スクリプト
自分のチャンネルの詳細な時系列データを取得してML精度向上

必要な設定:
1. Google Cloud Console でプロジェクト作成
2. YouTube Analytics API を有効化
3. OAuth 2.0 クライアントID作成（デスクトップアプリ）
4. credentials.json をダウンロードしてこのスクリプトと同じフォルダに配置

初回実行時にブラウザで認証が必要です。
認証後は token.json が作成され、次回以降は自動認証されます。
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# OAuth 2.0 スコープ
SCOPES = [
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/yt-analytics.readonly'
]


class YouTubeAnalyticsFetcher:
    """YouTube Analytics API でチャンネルの詳細データを取得"""

    def __init__(self, credentials_path: str = 'credentials.json',
                 token_path: str = 'token.json'):
        """
        Args:
            credentials_path: OAuth 2.0 クライアントID JSONファイルパス
            token_path: 認証トークン保存先
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.youtube = None
        self.youtube_analytics = None
        self.channel_id = None

    def authenticate(self):
        """OAuth 2.0 認証を実行"""
        creds = None

        # 保存されたトークンを読み込み
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

        # トークンが無効または存在しない場合、新規認証
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("🔄 トークンを更新中...")
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    print("❌ credentials.json が見つかりません")
                    print("\n【設定手順】")
                    print("1. https://console.cloud.google.com/ にアクセス")
                    print("2. プロジェクトを作成")
                    print("3. YouTube Analytics API を有効化")
                    print("4. 認証情報 → OAuth 2.0 クライアントID 作成（デスクトップアプリ）")
                    print("5. credentials.json をダウンロードしてこのフォルダに配置")
                    print()
                    return False

                print("🔐 初回認証を開始...")
                print("ブラウザが開きます。Googleアカウントでログインしてください。")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # トークンを保存
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
            print("✅ 認証成功")

        # YouTube Data API クライアント
        self.youtube = build('youtube', 'v3', credentials=creds)

        # YouTube Analytics API クライアント
        self.youtube_analytics = build('youtubeAnalytics', 'v2', credentials=creds)

        # 自分のチャンネルIDを取得
        self._get_channel_id()

        return True

    def _get_channel_id(self):
        """自分のチャンネルIDを取得"""
        try:
            request = self.youtube.channels().list(
                part='id,snippet',
                mine=True
            )
            response = request.execute()

            if response['items']:
                self.channel_id = response['items'][0]['id']
                channel_title = response['items'][0]['snippet']['title']
                print(f"✅ チャンネル認識: {channel_title} (ID: {self.channel_id})")
            else:
                print("⚠ チャンネルが見つかりません")

        except HttpError as e:
            print(f"❌ チャンネルID取得エラー: {e}")

    def fetch_channel_videos(self, max_results: int = 500) -> List[Dict[str, Any]]:
        """自分のチャンネルの全動画を取得

        Args:
            max_results: 取得する最大動画数

        Returns:
            動画情報のリスト
        """
        if not self.channel_id:
            print("⚠ チャンネルIDが取得できていません")
            return []

        print("\n" + "=" * 60)
        print("チャンネル動画一覧を取得中...")
        print("=" * 60)

        videos = []
        next_page_token = None

        while len(videos) < max_results:
            try:
                # 自分のアップロード動画を検索
                request = self.youtube.search().list(
                    part='id,snippet',
                    channelId=self.channel_id,
                    type='video',
                    order='date',
                    maxResults=min(50, max_results - len(videos)),
                    pageToken=next_page_token
                )
                response = request.execute()

                for item in response['items']:
                    video_id = item['id']['videoId']
                    snippet = item['snippet']

                    videos.append({
                        'video_id': video_id,
                        'title': snippet['title'],
                        'published_at': snippet['publishedAt'],
                        'description': snippet['description'],
                        'thumbnail_url': snippet['thumbnails'].get('high', {}).get('url', ''),
                    })

                next_page_token = response.get('nextPageToken')

                if not next_page_token:
                    break

                print(f"  取得済み: {len(videos)}件")

            except HttpError as e:
                print(f"❌ 動画取得エラー: {e}")
                break

        print(f"✅ 合計 {len(videos)}件の動画を取得")
        return videos

    def fetch_time_series_data(self, video_id: str,
                               days_back: int = 30) -> Dict[str, Any]:
        """1つの動画の時系列データを取得

        Args:
            video_id: YouTube動画ID
            days_back: 何日前までのデータを取得するか

        Returns:
            時系列データ（日別の再生数、高評価数等）
        """
        if not self.channel_id:
            return {}

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)

        try:
            # Analytics API でレポートを取得
            request = self.youtube_analytics.reports().query(
                ids=f'channel=={self.channel_id}',
                startDate=start_date.isoformat(),
                endDate=end_date.isoformat(),
                metrics='views,likes,comments,estimatedMinutesWatched,averageViewDuration',
                dimensions='day',
                filters=f'video=={video_id}',
                sort='day'
            )
            response = request.execute()

            # データを整形
            time_series = {
                'video_id': video_id,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'daily_data': []
            }

            if 'rows' in response:
                for row in response['rows']:
                    time_series['daily_data'].append({
                        'date': row[0],
                        'views': row[1],
                        'likes': row[2],
                        'comments': row[3],
                        'watch_time_minutes': row[4],
                        'average_view_duration': row[5],
                    })

            return time_series

        except HttpError as e:
            print(f"⚠ {video_id}: 時系列データ取得エラー: {e}")
            return {}

    def fetch_traffic_source_data(self, video_id: str,
                                  days_back: int = 30) -> Dict[str, Any]:
        """トラフィックソース（流入元）データを取得

        Args:
            video_id: YouTube動画ID
            days_back: 何日前までのデータを取得するか

        Returns:
            トラフィックソース別の再生数
        """
        if not self.channel_id:
            return {}

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)

        try:
            request = self.youtube_analytics.reports().query(
                ids=f'channel=={self.channel_id}',
                startDate=start_date.isoformat(),
                endDate=end_date.isoformat(),
                metrics='views',
                dimensions='insightTrafficSourceType',
                filters=f'video=={video_id}',
                sort='-views'
            )
            response = request.execute()

            traffic_sources = {
                'video_id': video_id,
                'sources': {}
            }

            if 'rows' in response:
                total_views = sum(row[1] for row in response['rows'])
                for row in response['rows']:
                    source_type = row[0]
                    views = row[1]
                    percentage = round(views / total_views * 100, 2) if total_views > 0 else 0

                    traffic_sources['sources'][source_type] = {
                        'views': views,
                        'percentage': percentage
                    }

            return traffic_sources

        except HttpError as e:
            print(f"⚠ {video_id}: トラフィックソース取得エラー: {e}")
            return {}

    def fetch_all_analytics(self, max_videos: int = 500,
                           days_back: int = 90,
                           include_traffic_sources: bool = True) -> List[Dict[str, Any]]:
        """チャンネルの全動画の詳細アナリティクスを取得

        Args:
            max_videos: 取得する最大動画数
            days_back: 何日前までのデータを取得するか
            include_traffic_sources: トラフィックソースデータも取得するか

        Returns:
            全動画の詳細データリスト
        """
        # まず動画一覧を取得
        videos = self.fetch_channel_videos(max_videos)

        if not videos:
            return []

        print("\n" + "=" * 60)
        print("詳細アナリティクスを取得中...")
        print("=" * 60)

        analytics_data = []

        for idx, video in enumerate(videos, 1):
            video_id = video['video_id']
            title = video['title']

            if idx % 10 == 0:
                print(f"[{idx}/{len(videos)}] 処理中...")

            # 時系列データを取得
            time_series = self.fetch_time_series_data(video_id, days_back)

            # トラフィックソースを取得
            traffic_sources = {}
            if include_traffic_sources:
                traffic_sources = self.fetch_traffic_source_data(video_id, days_back)

            # 統合
            analytics_item = {
                **video,
                'time_series': time_series,
                'traffic_sources': traffic_sources
            }

            analytics_data.append(analytics_item)

        print(f"\n✅ {len(analytics_data)}件のアナリティクスデータを取得完了")

        return analytics_data

    def save_analytics_data(self, data: List[Dict[str, Any]],
                           output_path: str = 'youtube_analytics_data.json'):
        """アナリティクスデータをJSONファイルに保存

        Args:
            data: アナリティクスデータ
            output_path: 保存先ファイルパス
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n✅ データ保存: {output_path}")
        print(f"   {len(data)}件のアナリティクスデータ")


def main():
    """メイン実行"""
    print("=" * 60)
    print("YouTube Analytics データ取得ツール")
    print("=" * 60)
    print()

    fetcher = YouTubeAnalyticsFetcher()

    # 認証
    if not fetcher.authenticate():
        print("❌ 認証に失敗しました。credentials.json を確認してください。")
        return

    print()
    print("=" * 60)
    print("データ取得設定")
    print("=" * 60)

    # 設定入力
    try:
        max_videos = int(input("取得する動画数（デフォルト: 500）: ").strip() or "500")
        days_back = int(input("何日前までのデータを取得？（デフォルト: 90）: ").strip() or "90")
        include_traffic = input("トラフィックソースも取得？ (y/n, デフォルト: y): ").strip().lower() or "y"
        include_traffic_sources = (include_traffic == 'y')
    except ValueError:
        print("⚠ 入力エラー。デフォルト設定を使用します。")
        max_videos = 500
        days_back = 90
        include_traffic_sources = True

    print()
    print("=" * 60)
    print("データ取得開始")
    print("=" * 60)
    print(f"  対象動画数: {max_videos}件")
    print(f"  取得期間: 過去{days_back}日")
    print(f"  トラフィックソース: {'ON' if include_traffic_sources else 'OFF'}")
    print()

    # アナリティクス取得
    analytics_data = fetcher.fetch_all_analytics(
        max_videos=max_videos,
        days_back=days_back,
        include_traffic_sources=include_traffic_sources
    )

    # 保存
    if analytics_data:
        output_path = 'RAW DATA/youtube_analytics_data.json'
        os.makedirs('RAW DATA', exist_ok=True)
        fetcher.save_analytics_data(analytics_data, output_path)

        print()
        print("=" * 60)
        print("✅ 完了")
        print("=" * 60)
        print()
        print("次のステップ:")
        print("  1. RAW DATA/youtube_analytics_data.json を確認")
        print("  2. data_integrator.py でML_training_data.json に統合")
        print("  3. feature_engineering.py に時系列特徴量を追加")
        print("  4. ml_scheduler.py でLSTMモデルを訓練")
    else:
        print("⚠ データが取得できませんでした")


if __name__ == '__main__':
    main()
