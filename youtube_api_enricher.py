#!/usr/bin/env python3
"""
YouTube API データエンリッチメントモジュール
既存のデータをYouTube API v3で補強し、ML精度を向上
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class YouTubeAPIEnricher:
    """YouTube API v3を使用してデータを補強"""

    def __init__(self, api_keys: List[str]):
        """
        Args:
            api_keys: YouTube API キーのリスト
        """
        self.api_keys = api_keys
        self.current_key_index = 0
        self.youtube = build('youtube', 'v3', developerKey=api_keys[0])
        self.request_count = 0
        self.max_requests_per_key = 10000  # 1日あたりの割り当て

    def _switch_api_key(self) -> bool:
        """次のAPIキーに切り替え

        Returns:
            切り替え成功時True、全キー使用済みの場合False
        """
        self.current_key_index += 1

        if self.current_key_index >= len(self.api_keys):
            print("⚠ 全てのAPIキーを使い切りました")
            return False

        self.youtube = build('youtube', 'v3',
                           developerKey=self.api_keys[self.current_key_index])
        self.request_count = 0
        print(f"🔑 APIキー切り替え: {self.current_key_index + 1}/{len(self.api_keys)}")
        return True

    def _make_api_request(self, request_func, max_retries: int = 3) -> Optional[Dict]:
        """APIリクエストを実行（リトライ・キー切り替え対応）

        Args:
            request_func: APIリクエスト関数
            max_retries: 最大リトライ回数

        Returns:
            APIレスポンス、失敗時None
        """
        for attempt in range(max_retries):
            try:
                response = request_func().execute()
                self.request_count += 1
                return response

            except HttpError as e:
                error_reason = e.resp.get('reason', '')

                # 割り当て超過エラー
                if e.resp.status == 403 and 'quota' in error_reason.lower():
                    print(f"⚠ API割り当て超過（キー{self.current_key_index + 1}）")
                    if not self._switch_api_key():
                        return None
                    continue

                # レート制限
                elif e.resp.status == 429:
                    wait_time = 2 ** attempt
                    print(f"⏳ レート制限: {wait_time}秒待機")
                    time.sleep(wait_time)
                    continue

                else:
                    print(f"❌ API Error: {e}")
                    return None

            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                return None

        return None

    def enrich_video_data(self, video_id: str) -> Optional[Dict[str, Any]]:
        """1つの動画IDから詳細データを取得

        取得データ:
        - snippet: タイトル、説明、タグ、カテゴリー、サムネイル
        - contentDetails: 動画時間、定義（HD/SD）
        - statistics: 再生数、高評価数、コメント数
        - status: 公開状態

        Args:
            video_id: YouTube動画ID

        Returns:
            エンリッチされたデータ辞書
        """
        request = lambda: self.youtube.videos().list(
            part='snippet,contentDetails,statistics,status',
            id=video_id
        )

        response = self._make_api_request(request)

        if not response or not response.get('items'):
            return None

        item = response['items'][0]
        snippet = item.get('snippet', {})
        content_details = item.get('contentDetails', {})
        statistics = item.get('statistics', {})
        status = item.get('status', {})

        # ISO 8601 duration (PT#M#S) をパース
        duration_str = content_details.get('duration', 'PT0S')
        duration_seconds = self._parse_duration(duration_str)

        # タグをリスト化
        tags = snippet.get('tags', [])

        # カテゴリーIDから名前を推定
        category_id = snippet.get('categoryId', '')
        category_name = self._get_category_name(category_id)

        # サムネイルの最高品質URLを取得
        thumbnails = snippet.get('thumbnails', {})
        thumbnail_url = (
            thumbnails.get('maxres', {}).get('url') or
            thumbnails.get('high', {}).get('url') or
            thumbnails.get('medium', {}).get('url') or
            thumbnails.get('default', {}).get('url')
        )

        enriched_data = {
            # 基本情報
            'video_id': video_id,
            'title': snippet.get('title', ''),
            'description': snippet.get('description', ''),
            'channel_id': snippet.get('channelId', ''),
            'channel_title': snippet.get('channelTitle', ''),
            'published_at': snippet.get('publishedAt', ''),

            # カテゴリー・タグ
            'category_id': category_id,
            'category_name': category_name,
            'tags': tags,
            'tag_count': len(tags),

            # コンテンツ詳細
            'duration_seconds': duration_seconds,
            'duration_minutes': round(duration_seconds / 60, 2),
            'is_short': duration_seconds < 60,  # 60秒未満はShorts
            'definition': content_details.get('definition', 'sd'),  # hd or sd
            'caption': content_details.get('caption', 'false'),

            # 統計
            'view_count': int(statistics.get('viewCount', 0)),
            'like_count': int(statistics.get('likeCount', 0)),
            'comment_count': int(statistics.get('commentCount', 0)),

            # 算出メトリクス
            'engagement_rate': self._calculate_engagement_rate(statistics),
            'like_rate': self._calculate_like_rate(statistics),
            'comment_rate': self._calculate_comment_rate(statistics),

            # サムネイル
            'thumbnail_url': thumbnail_url,

            # ステータス
            'privacy_status': status.get('privacyStatus', ''),
            'license': status.get('license', ''),
            'embeddable': status.get('embeddable', False),
            'made_for_kids': status.get('madeForKids', False),
        }

        return enriched_data

    def enrich_channel_data(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """チャンネルの詳細データを取得

        取得データ:
        - snippet: タイトル、説明、カスタムURL
        - statistics: チャンネル登録者数、動画数、総再生回数
        - contentDetails: アップロードプレイリストID

        Args:
            channel_id: YouTubeチャンネルID

        Returns:
            チャンネルデータ辞書
        """
        request = lambda: self.youtube.channels().list(
            part='snippet,statistics,contentDetails',
            id=channel_id
        )

        response = self._make_api_request(request)

        if not response or not response.get('items'):
            return None

        item = response['items'][0]
        snippet = item.get('snippet', {})
        statistics = item.get('statistics', {})
        content_details = item.get('contentDetails', {})

        channel_data = {
            'channel_id': channel_id,
            'channel_title': snippet.get('title', ''),
            'channel_description': snippet.get('description', ''),
            'custom_url': snippet.get('customUrl', ''),
            'published_at': snippet.get('publishedAt', ''),

            # 統計
            'subscriber_count': int(statistics.get('subscriberCount', 0)),
            'video_count': int(statistics.get('videoCount', 0)),
            'view_count': int(statistics.get('viewCount', 0)),

            # 関連プレイリスト
            'uploads_playlist_id': content_details.get('relatedPlaylists', {}).get('uploads', ''),
        }

        return channel_data

    def find_related_videos(self, video_id: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """関連動画を検索（競合分析用）

        Args:
            video_id: 基準となる動画ID
            max_results: 取得する関連動画数

        Returns:
            関連動画IDとタイトルのリスト
        """
        request = lambda: self.youtube.search().list(
            part='snippet',
            relatedToVideoId=video_id,
            type='video',
            maxResults=max_results
        )

        response = self._make_api_request(request)

        if not response or not response.get('items'):
            return []

        related_videos = []
        for item in response['items']:
            related_videos.append({
                'video_id': item['id']['videoId'],
                'title': item['snippet']['title'],
                'channel_title': item['snippet']['channelTitle'],
            })

        return related_videos

    def enrich_dataset(self, data: List[Dict[str, Any]],
                      include_channel: bool = True,
                      include_related: bool = False,
                      verbose: bool = True) -> List[Dict[str, Any]]:
        """データセット全体をエンリッチ

        Args:
            data: エンリッチ対象のデータリスト（video_id含む）
            include_channel: チャンネルデータを追加するか
            include_related: 関連動画データを追加するか
            verbose: 進捗を表示するか

        Returns:
            エンリッチされたデータリスト
        """
        enriched_data = []
        total = len(data)

        if verbose:
            print("=" * 60)
            print("YouTube API データエンリッチメント")
            print("=" * 60)
            print(f"対象件数: {total}件")
            print()

        for idx, item in enumerate(data, 1):
            video_id = item.get('video_id', '')

            if not video_id:
                if verbose:
                    print(f"[{idx}/{total}] ⚠ video_id不明 - スキップ")
                enriched_data.append(item)
                continue

            if verbose and idx % 10 == 0:
                print(f"[{idx}/{total}] 処理中... (API requests: {self.request_count})")

            # 既存データをコピー
            enriched_item = item.copy()

            # 動画データを取得
            video_data = self.enrich_video_data(video_id)
            if video_data:
                enriched_item.update(video_data)

                # チャンネルデータを取得
                if include_channel:
                    channel_id = video_data.get('channel_id', '')
                    if channel_id:
                        channel_data = self.enrich_channel_data(channel_id)
                        if channel_data:
                            # チャンネルデータにプレフィックスを付けて追加
                            for key, value in channel_data.items():
                                enriched_item[f'channel_{key}'] = value

                # 関連動画を取得
                if include_related:
                    related = self.find_related_videos(video_id, max_results=5)
                    enriched_item['related_videos'] = related
                    enriched_item['related_video_count'] = len(related)

            else:
                if verbose:
                    print(f"[{idx}/{total}] ⚠ {video_id} - データ取得失敗")

            enriched_data.append(enriched_item)

            # レート制限対策（少し待機）
            time.sleep(0.1)

        if verbose:
            print()
            print("=" * 60)
            print(f"✅ エンリッチメント完了: {len(enriched_data)}件")
            print(f"   API リクエスト数: {self.request_count}")
            print("=" * 60)
            print()

        return enriched_data

    @staticmethod
    def _parse_duration(duration_str: str) -> int:
        """ISO 8601 duration (PT#H#M#S) を秒数に変換

        Args:
            duration_str: PT1H23M45S のような文字列

        Returns:
            秒数
        """
        import re

        # PT1H23M45S → 1時間23分45秒
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, duration_str)

        if not match:
            return 0

        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)

        return hours * 3600 + minutes * 60 + seconds

    @staticmethod
    def _get_category_name(category_id: str) -> str:
        """カテゴリーIDから名前を取得

        Args:
            category_id: YouTubeカテゴリーID

        Returns:
            カテゴリー名
        """
        categories = {
            '1': 'Film & Animation',
            '2': 'Autos & Vehicles',
            '10': 'Music',
            '15': 'Pets & Animals',
            '17': 'Sports',
            '19': 'Travel & Events',
            '20': 'Gaming',
            '22': 'People & Blogs',
            '23': 'Comedy',
            '24': 'Entertainment',
            '25': 'News & Politics',
            '26': 'Howto & Style',
            '27': 'Education',
            '28': 'Science & Technology',
            '29': 'Nonprofits & Activism',
        }
        return categories.get(category_id, 'Unknown')

    @staticmethod
    def _calculate_engagement_rate(statistics: Dict) -> float:
        """エンゲージメント率を計算

        (like_count + comment_count) / view_count * 100

        Args:
            statistics: 統計データ

        Returns:
            エンゲージメント率（%）
        """
        view_count = int(statistics.get('viewCount', 0))
        like_count = int(statistics.get('likeCount', 0))
        comment_count = int(statistics.get('commentCount', 0))

        if view_count == 0:
            return 0.0

        return round((like_count + comment_count) / view_count * 100, 2)

    @staticmethod
    def _calculate_like_rate(statistics: Dict) -> float:
        """高評価率を計算

        like_count / view_count * 100

        Args:
            statistics: 統計データ

        Returns:
            高評価率（%）
        """
        view_count = int(statistics.get('viewCount', 0))
        like_count = int(statistics.get('likeCount', 0))

        if view_count == 0:
            return 0.0

        return round(like_count / view_count * 100, 2)

    @staticmethod
    def _calculate_comment_rate(statistics: Dict) -> float:
        """コメント率を計算

        comment_count / view_count * 100

        Args:
            statistics: 統計データ

        Returns:
            コメント率（%）
        """
        view_count = int(statistics.get('viewCount', 0))
        comment_count = int(statistics.get('commentCount', 0))

        if view_count == 0:
            return 0.0

        return round(comment_count / view_count * 100, 2)


def main():
    """テスト実行"""
    # main.pyからAPIキーをインポート
    import sys
    sys.path.append('/Users/shii/Desktop/song virality validator')
    from main import YOUTUBE_API_KEYS

    enricher = YouTubeAPIEnricher(YOUTUBE_API_KEYS)

    # テストデータ
    test_data = [
        {'video_id': 'dQw4w9WgXcQ', 'song_name': 'Never Gonna Give You Up'},
        {'video_id': '9bZkp7q19f0', 'song_name': 'Gangnam Style'},
    ]

    print("=" * 60)
    print("YouTube API Enricher - テスト")
    print("=" * 60)
    print()

    # エンリッチメント実行
    enriched = enricher.enrich_dataset(
        test_data,
        include_channel=True,
        include_related=False,
        verbose=True
    )

    # 結果表示
    for item in enriched:
        print(f"\n【{item.get('song_name')}】")
        print(f"  動画ID: {item.get('video_id')}")
        print(f"  タイトル: {item.get('title', 'N/A')}")
        print(f"  カテゴリー: {item.get('category_name', 'N/A')}")
        print(f"  時間: {item.get('duration_minutes', 0)}分")
        print(f"  再生数: {item.get('view_count', 0):,}")
        print(f"  高評価数: {item.get('like_count', 0):,}")
        print(f"  エンゲージメント率: {item.get('engagement_rate', 0)}%")
        print(f"  チャンネル登録者数: {item.get('channel_subscriber_count', 0):,}")


if __name__ == '__main__':
    main()
