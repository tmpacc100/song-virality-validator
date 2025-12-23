#!/usr/bin/env python3
"""
既存のYouTubeアナリティクスデータ統合モジュール
youtube anarytics taiko フォルダのCSVデータを読み込み、ML訓練データに統合
"""

import os
import csv
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional


class YouTubeAnalyticsIntegrator:
    """既存のYouTubeアナリティクスCSVデータを統合"""

    def __init__(self, analytics_dir: str = 'youtube anarytics taiko'):
        """
        Args:
            analytics_dir: アナリティクスデータのディレクトリ
        """
        self.analytics_dir = analytics_dir
        self.content_data = None  # コンテンツ別データ
        self.date_data = None  # 日付別データ
        self.traffic_data = None  # トラフィックソース別データ

    def load_all_analytics(self):
        """すべてのアナリティクスCSVを読み込み"""
        print("=" * 60)
        print("YouTubeアナリティクスデータ読み込み")
        print("=" * 60)

        # コンテンツ別データ
        content_path = os.path.join(
            self.analytics_dir,
            'コンテンツ 2023-11-01_2025-12-16 たいこでヒットソング',
            '表データ.csv'
        )
        if os.path.exists(content_path):
            self.content_data = pd.read_csv(content_path)
            # 最初の行（合計）を除外
            self.content_data = self.content_data[self.content_data['コンテンツ'] != '合計']
            print(f"✓ コンテンツデータ: {len(self.content_data)}件")
        else:
            print(f"⚠ コンテンツデータが見つかりません: {content_path}")

        # 日付別データ
        date_path = os.path.join(
            self.analytics_dir,
            '日付 2023-11-01_2025-12-16 たいこでヒットソング',
            '表データ.csv'
        )
        if os.path.exists(date_path):
            self.date_data = pd.read_csv(date_path)
            # 最初の行（合計）を除外
            self.date_data = self.date_data[self.date_data['日付'] != '合計']
            print(f"✓ 日付データ: {len(self.date_data)}件")
        else:
            print(f"⚠ 日付データが見つかりません: {date_path}")

        # トラフィックソース別データ
        traffic_path = os.path.join(
            self.analytics_dir,
            'オーガニック トラフィックと有料のトラフィック 2023-11-01_2025-12-16 たいこでヒットソング',
            '表データ.csv'
        )
        if os.path.exists(traffic_path):
            self.traffic_data = pd.read_csv(traffic_path)
            # 最初の行（合計）を除外
            self.traffic_data = self.traffic_data[self.traffic_data.iloc[:, 0] != '合計']
            print(f"✓ トラフィックデータ: {len(self.traffic_data)}件")
        else:
            print(f"⚠ トラフィックデータが見つかりません: {traffic_path}")

        print()

    def extract_traffic_features(self) -> Dict[str, Dict[str, Any]]:
        """トラフィックソース別データから特徴量を抽出

        Returns:
            全体、有料、オーガニックのトラフィックデータ
        """
        if self.traffic_data is None:
            return {}

        traffic_features = {}

        for _, row in self.traffic_data.iterrows():
            traffic_type = row.iloc[0]  # 最初の列: 有料/オーガニック

            if traffic_type in ['有料', 'オーガニック']:
                traffic_features[traffic_type] = {
                    'views': self._safe_int(row.get('視聴回数', 0)),
                    'watch_time_hours': self._safe_float(row.get('総再生時間（単位: 時間）', 0)),
                    'avg_view_duration': row.get('平均視聴時間', '0:00:00'),
                    'shares': self._safe_int(row.get('共有数', 0)),
                    'likes': self._safe_int(row.get('高評価数', 0)),
                }

        return traffic_features

    def extract_content_features(self) -> List[Dict[str, Any]]:
        """コンテンツ別データから特徴量を抽出

        Returns:
            動画ごとの特徴量リスト
        """
        if self.content_data is None:
            return []

        content_features = []

        # トラフィックデータを取得（チャンネル全体の集計データ）
        traffic_features = self.extract_traffic_features()

        # チャンネル全体のオーガニック比率を計算
        channel_organic_views = traffic_features.get('オーガニック', {}).get('views', 0)
        channel_paid_views = traffic_features.get('有料', {}).get('views', 0)
        channel_total_traffic = channel_organic_views + channel_paid_views

        channel_organic_ratio = 0.0
        if channel_total_traffic > 0:
            channel_organic_ratio = round(channel_organic_views / channel_total_traffic * 100, 2)

        for _, row in self.content_data.iterrows():
            video_id = row['コンテンツ']
            title = row['動画のタイトル']

            # 重要なメトリクスを抽出
            features = {
                'video_id': video_id,
                'title': title,
                'published_at': row.get('動画公開時刻', ''),
                'duration_text': row.get('長さ', ''),

                # エンゲージメント指標（自分のチャンネルの実データ）
                'analytics_views': self._safe_int(row.get('視聴回数', 0)),
                'analytics_watch_time_hours': self._safe_float(row.get('総再生時間（単位: 時間）', 0)),
                'analytics_avg_view_duration': row.get('平均視聴時間', '0:00:00'),
                'analytics_avg_percentage_viewed': self._safe_float(row.get('平均再生率（%） (%)', 0)),
                'analytics_retention_rate': self._safe_float(row.get('視聴を継続 (%)', 0)),

                # ユーザー行動
                'analytics_unique_viewers': self._safe_int(row.get('ユニーク視聴者数', 0)),
                'analytics_views_per_viewer': self._safe_float(row.get('視聴者あたりの平均視聴回数', 0)),

                # エンゲージメント
                'analytics_likes': self._safe_int(row.get('高評価数', 0)),
                'analytics_dislikes': self._safe_int(row.get('低評価数', 0)),
                'analytics_like_rate': self._safe_float(row.get('高評価率（低評価比） (%)', 0)),
                'analytics_shares': self._safe_int(row.get('共有数', 0)),
                'analytics_comments': self._safe_int(row.get('コメントの追加回数', 0)),

                # 登録者
                'analytics_subscribers_gained': self._safe_int(row.get('登録者増加数', 0)),
                'analytics_subscribers_lost': self._safe_int(row.get('登録者減少数', 0)),
                'analytics_net_subscribers': self._safe_int(row.get('登録者増加数', 0)) - self._safe_int(row.get('登録者減少数', 0)),

                # インプレッション
                'analytics_impressions': self._safe_int(row.get('インプレッション数', 0)),
                'analytics_ctr': self._safe_float(row.get('インプレッションのクリック率 (%)', 0)),

                # 終了画面・カード
                'analytics_end_screen_clicks': self._safe_int(row.get('終了画面要素のクリック数', 0)),
                'analytics_end_screen_shown': self._safe_int(row.get('終了画面要素の表示回数', 0)),
                'analytics_card_clicks': self._safe_int(row.get('カードのクリック数', 0)),
                'analytics_card_shown': self._safe_int(row.get('カードの表示回数', 0)),

                # チャンネル全体のオーガニック比率（参考値）
                'channel_organic_ratio': channel_organic_ratio,
            }

            # 平均視聴時間を秒数に変換
            avg_view_duration_seconds = self._parse_duration_to_seconds(features['analytics_avg_view_duration'])
            features['analytics_avg_view_duration_seconds'] = avg_view_duration_seconds

            # 算出メトリクス
            if features['analytics_views'] > 0:
                features['analytics_engagement_rate'] = round(
                    (features['analytics_likes'] + features['analytics_comments']) / features['analytics_views'] * 100, 2
                )
                features['analytics_share_rate'] = round(
                    features['analytics_shares'] / features['analytics_views'] * 100, 4
                )
            else:
                features['analytics_engagement_rate'] = 0
                features['analytics_share_rate'] = 0

            if features['analytics_impressions'] > 0:
                features['analytics_views_per_impression'] = round(
                    features['analytics_views'] / features['analytics_impressions'], 4
                )
            else:
                features['analytics_views_per_impression'] = 0

            content_features.append(features)

        return content_features

    def extract_time_series_features(self) -> Dict[str, List[Dict[str, Any]]]:
        """日付別データから時系列特徴量を抽出

        Returns:
            日付ごとのメトリクス
        """
        if self.date_data is None:
            return {}

        time_series = []

        for _, row in self.date_data.iterrows():
            date_str = row['日付']

            time_series.append({
                'date': date_str,
                'views': self._safe_int(row.get('視聴回数', 0)),
                'watch_time_hours': self._safe_float(row.get('総再生時間（単位: 時間）', 0)),
                'subscribers_gained': self._safe_int(row.get('登録者増加数', 0)),
                'subscribers_lost': self._safe_int(row.get('登録者減少数', 0)),
                'net_subscribers': self._safe_int(row.get('登録者増加数', 0)) - self._safe_int(row.get('登録者減少数', 0)),
                'likes': self._safe_int(row.get('高評価数', 0)),
                'comments': self._safe_int(row.get('コメントの追加回数', 0)),
                'impressions': self._safe_int(row.get('インプレッション数', 0)),
                'ctr': self._safe_float(row.get('インプレッションのクリック率 (%)', 0)),
                'avg_percentage_viewed': self._safe_float(row.get('平均再生率（%） (%)', 0)),
            })

        return {'time_series': time_series}

    def enrich_ml_training_data(self, ml_data: List[Dict[str, Any]],
                               filter_ads: bool = True) -> List[Dict[str, Any]]:
        """ML訓練データにアナリティクスデータを統合

        Args:
            ml_data: 既存のML訓練データ
            filter_ads: 広告動画を除外するか

        Returns:
            エンリッチされたデータ
        """
        print("=" * 60)
        print("アナリティクスデータ統合")
        print("=" * 60)

        # コンテンツ特徴量を抽出
        content_features = self.extract_content_features()

        # video_idでマッピング
        content_map = {item['video_id']: item for item in content_features}

        enriched_count = 0
        ad_filtered_count = 0

        for item in ml_data:
            video_id = item.get('video_id', '')

            if video_id in content_map:
                # アナリティクスデータを追加
                analytics_data = content_map[video_id]

                # 広告フィルタリング
                if filter_ads:
                    title = analytics_data.get('title', '')
                    if self._is_advertisement(title):
                        item['is_advertisement'] = True
                        ad_filtered_count += 1
                        continue

                # YouTube API raw dataの数値は他のチャンネルのデータ
                # → 絶対値は使わず、相対的なバズり度の指標として使用
                youtube_api_views = item.get('view_count', 0)
                youtube_api_likes = item.get('like_count', 0)
                youtube_api_comments = item.get('comment_count', 0)

                # 相対的なバズり度指標を計算
                if youtube_api_views > 0:
                    # YouTube API データの相対的な評価指標
                    item['relative_engagement_score'] = round(
                        (youtube_api_likes + youtube_api_comments) / youtube_api_views * 100, 4
                    )
                    item['relative_like_rate'] = round(
                        youtube_api_likes / youtube_api_views * 100, 4
                    )
                    item['relative_comment_rate'] = round(
                        youtube_api_comments / youtube_api_views * 100, 4
                    )
                else:
                    item['relative_engagement_score'] = 0.0
                    item['relative_like_rate'] = 0.0
                    item['relative_comment_rate'] = 0.0

                # 自分のチャンネルの実データをview_countとして使用
                analytics_views = analytics_data.get('analytics_views', 0)
                if analytics_views > 0:
                    item['view_count'] = analytics_views  # 実データで上書き
                    item['data_source'] = 'analytics'  # データソースを明記
                else:
                    item['data_source'] = 'youtube_api'  # YouTube APIのデータ

                # すべてのアナリティクスフィールドを追加
                for key, value in analytics_data.items():
                    if key not in ['video_id', 'title']:  # 重複を避ける
                        item[key] = value

                item['is_advertisement'] = False
                enriched_count += 1

        print(f"✓ {enriched_count}/{len(ml_data)}件にアナリティクスデータを統合")
        if filter_ads and ad_filtered_count > 0:
            print(f"⚠ {ad_filtered_count}件の広告動画を除外しました")
        print()

        return ml_data

    @staticmethod
    def _is_advertisement(title: str) -> bool:
        """タイトルから広告動画かどうかを判定

        Args:
            title: 動画タイトル

        Returns:
            広告動画の場合True
        """
        ad_keywords = ['広告', '広告_', '_広告', 'ad_', '_ad']
        title_lower = title.lower()

        for keyword in ad_keywords:
            if keyword in title_lower:
                return True

        return False

    @staticmethod
    def _safe_int(value, default=0) -> int:
        """安全に整数に変換"""
        try:
            if pd.isna(value) or value == '':
                return default
            return int(float(value))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _safe_float(value, default=0.0) -> float:
        """安全に浮動小数点に変換"""
        try:
            if pd.isna(value) or value == '':
                return default
            return float(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _parse_duration_to_seconds(duration_str: str) -> int:
        """時間文字列（0:00:21形式）を秒数に変換

        Args:
            duration_str: 時間文字列（例: "0:00:21", "0:03:45"）

        Returns:
            秒数
        """
        try:
            parts = duration_str.split(':')
            if len(parts) == 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = int(parts[2])
                return hours * 3600 + minutes * 60 + seconds
            elif len(parts) == 2:
                minutes = int(parts[0])
                seconds = int(parts[1])
                return minutes * 60 + seconds
            else:
                return 0
        except (ValueError, AttributeError):
            return 0


def main():
    """テスト実行"""
    print("=" * 60)
    print("YouTubeアナリティクス統合ツール")
    print("=" * 60)
    print()

    integrator = YouTubeAnalyticsIntegrator()

    # アナリティクスデータ読み込み
    integrator.load_all_analytics()

    # コンテンツ特徴量を抽出
    content_features = integrator.extract_content_features()
    print(f"コンテンツ特徴量: {len(content_features)}件")

    # サンプル表示
    if content_features:
        print("\n【サンプル】")
        sample = content_features[0]
        print(f"  Video ID: {sample['video_id']}")
        print(f"  Title: {sample['title']}")
        print(f"  Views: {sample['analytics_views']:,}")
        print(f"  Avg View Duration: {sample['analytics_avg_view_duration_seconds']}秒")
        print(f"  Avg Percentage Viewed: {sample['analytics_avg_percentage_viewed']}%")
        print(f"  Engagement Rate: {sample['analytics_engagement_rate']}%")
        print(f"  CTR: {sample['analytics_ctr']}%")

    # 時系列特徴量を抽出
    time_series = integrator.extract_time_series_features()
    if 'time_series' in time_series:
        print(f"\n時系列データ: {len(time_series['time_series'])}日分")

    # ML訓練データと統合
    print("\n" + "=" * 60)
    print("ML訓練データとの統合")
    print("=" * 60)

    ml_data_path = 'ML_training_data.json'
    if os.path.exists(ml_data_path):
        with open(ml_data_path, 'r', encoding='utf-8') as f:
            ml_data = json.load(f)

        print(f"既存データ: {len(ml_data)}件")

        # 統合
        enriched_data = integrator.enrich_ml_training_data(ml_data)

        # 保存
        output_path = 'ML_training_data_enriched.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(enriched_data, f, ensure_ascii=False, indent=2)

        print(f"✓ エンリッチ済みデータ保存: {output_path}")

        # CSV版も保存
        csv_path = output_path.replace('.json', '.csv')
        if enriched_data:
            all_keys = set()
            for item in enriched_data:
                all_keys.update(item.keys())

            with open(csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
                writer.writeheader()
                writer.writerows(enriched_data)

            print(f"✓ CSV保存: {csv_path}")

    else:
        print(f"⚠ {ml_data_path} が見つかりません")
        print("先に data_integrator.py を実行してください")

    print("\n" + "=" * 60)
    print("✅ 完了")
    print("=" * 60)


if __name__ == '__main__':
    main()
