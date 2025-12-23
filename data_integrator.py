#!/usr/bin/env python3
"""
データ統合スクリプト
ML/RLモデルの学習データを複数のソースから統合
"""

import json
import csv
import pandas as pd
from datetime import datetime
import os


class DataIntegrator:
    """複数のデータソースを統合してML/RL用データセットを作成"""

    def __init__(self):
        self.youtube_api_data = []
        self.channel_history_data = []
        self.taiko_release_data = []
        self.rankings_data = []

    def load_all_sources(self):
        """すべてのデータソースを読み込み"""
        print("="*60)
        print("データソース読み込み")
        print("="*60)

        # 1. YouTube API raw data
        try:
            with open('RAW DATA/Youtube_API_raw.json', 'r', encoding='utf-8') as f:
                self.youtube_api_data = json.load(f)
            print(f"✓ Youtube_API_raw.json: {len(self.youtube_api_data)}件")
        except Exception as e:
            print(f"✗ Youtube_API_raw.json: {e}")

        # 2. Channel history
        try:
            with open('channel_history.json', 'r', encoding='utf-8') as f:
                self.channel_history_data = json.load(f)
            print(f"✓ channel_history.json: {len(self.channel_history_data)}件")
        except Exception as e:
            print(f"✗ channel_history.json: {e}")

        # 3. TaikoGame リリース・開発中データ
        try:
            with open('filtered data/taiko_server_リリース_開発中_filtered.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.taiko_release_data = list(reader)
            print(f"✓ taiko_server_リリース_開発中_filtered.csv: {len(self.taiko_release_data)}件")
        except Exception as e:
            print(f"✗ taiko_server_リリース_開発中_filtered.csv: {e}")

        # 4. 既存rankings.json
        try:
            with open('rankings.json', 'r', encoding='utf-8') as f:
                rankings = json.load(f)
                if 'overall' in rankings:
                    self.rankings_data = rankings['overall']
            print(f"✓ rankings.json: {len(self.rankings_data)}件")
        except Exception as e:
            print(f"✗ rankings.json: {e}")

        print()

    def integrate_data(self):
        """データを統合して訓練用データセットを作成"""
        print("="*60)
        print("データ統合")
        print("="*60)

        integrated_data = []

        # video_idをキーにしてデータをマージ
        video_id_map = {}

        # 1. YouTube API dataをベースに
        for item in self.youtube_api_data:
            video_id = item.get('video_id', '')
            if video_id:
                video_id_map[video_id] = {
                    'video_id': video_id,
                    'song_name': item.get('song_name', ''),
                    'artist_name': item.get('artist_name', ''),
                    'release_date': item.get('release_date', ''),
                    'video_title': item.get('video_title', ''),
                    'channel_title': item.get('channel_title', ''),
                    'view_count': item.get('view_count', 0),
                    'like_count': item.get('like_count', 0),
                    'comment_count': item.get('comment_count', 0),
                    'support_rate': item.get('support_rate', 0),
                    'growth_rate': item.get('growth_rate', 0),
                    'days_since_published': item.get('days_since_published', 0),
                    'source': 'youtube_api'
                }

        print(f"  YouTube API: {len(video_id_map)}件をベースに設定")

        # 2. Channel historyは自分のチャンネルの投稿履歴（別データ）
        # これらは独立したサンプルとして追加
        channel_history_added = 0
        for item in self.channel_history_data:
            video_id = item.get('video_id', '')
            if video_id and video_id not in video_id_map:
                # タイトルから曲名を抽出
                title = item.get('title', '')

                # 新しいエントリとして追加
                video_id_map[video_id] = {
                    'video_id': video_id,
                    'song_name': title,  # タイトルを曲名として使用
                    'artist_name': 'たいこでヒットソング',  # 自分のチャンネル名
                    'release_date': '',
                    'video_title': title,
                    'channel_title': 'たいこでヒットソング',
                    'view_count': item.get('view_count', 0),
                    'like_count': item.get('like_count', 0),
                    'comment_count': item.get('comment_count', 0),
                    'support_rate': 0,
                    'growth_rate': 0,
                    'days_since_published': 0,
                    'published_at': item.get('published_at', ''),
                    'published_date': item.get('published_date', ''),
                    'published_time': item.get('published_time', ''),
                    'published_hour': item.get('published_hour', 0),
                    'published_day_of_week': item.get('published_day_of_week', ''),
                    'published_is_weekend': item.get('published_is_weekend', False),
                    'duration_seconds': item.get('duration_seconds', 0),
                    'is_short': item.get('is_short', False),
                    'tags': item.get('tags', ''),
                    'source': 'channel_history'
                }
                channel_history_added += 1

        print(f"  Channel history: {channel_history_added}件を追加（独立サンプル）")

        # 3. TaikoGameデータからタグ・難易度情報を追加
        # song_nameをキーにマッチング
        song_name_to_taiko = {}
        for item in self.taiko_release_data:
            song_name = item.get('song_name', '').strip()
            if song_name:
                song_name_to_taiko[song_name] = item

        taiko_matched = 0
        for video_id, data in video_id_map.items():
            song_name = data.get('song_name', '')
            if song_name in song_name_to_taiko:
                taiko_item = song_name_to_taiko[song_name]
                data.update({
                    'taiko_id': taiko_item.get('id', ''),
                    'tags': taiko_item.get('tags', ''),
                    'difficulty': taiko_item.get('difficulty', ''),
                    'release_status': taiko_item.get('release_status', ''),
                })
                taiko_matched += 1

        print(f"  TaikoGame data: {taiko_matched}件をマッチング")

        # 4. rankings.jsonから追加のメトリクスを統合
        rankings_matched = 0
        for item in self.rankings_data:
            video_id = item.get('video_id', '')
            if video_id in video_id_map:
                # 既存データを更新（より新しいデータがある場合）
                if 'metrics' in item:
                    video_id_map[video_id].update({
                        'view_count': item['metrics'].get('view_count', video_id_map[video_id]['view_count']),
                        'like_count': item['metrics'].get('like_count', video_id_map[video_id]['like_count']),
                        'comment_count': item['metrics'].get('comment_count', video_id_map[video_id]['comment_count']),
                        'support_rate': item['metrics'].get('support_rate', video_id_map[video_id]['support_rate']),
                        'growth_rate': item['metrics'].get('growth_rate', video_id_map[video_id]['growth_rate']),
                    })
                rankings_matched += 1

        print(f"  Rankings.json: {rankings_matched}件をマッチング")

        # リストに変換
        integrated_data = list(video_id_map.values())

        print()
        print(f"✓ 統合完了: {len(integrated_data)}件")
        print()

        return integrated_data

    def save_integrated_data(self, data, output_path='ML_training_data.json'):
        """統合データを保存"""
        print("="*60)
        print("統合データ保存")
        print("="*60)

        # JSON形式で保存
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✓ JSON保存: {output_path} ({len(data)}件)")

        # CSV形式でも保存
        csv_path = output_path.replace('.json', '.csv')
        if data:
            # 全てのキーを収集（データによってフィールドが異なる場合があるため）
            all_keys = set()
            for item in data:
                all_keys.update(item.keys())

            with open(csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
                writer.writeheader()
                writer.writerows(data)

            print(f"✓ CSV保存: {csv_path}")

        print()

    def analyze_integrated_data(self, data):
        """統合データの統計情報を表示"""
        print("="*60)
        print("統合データ分析")
        print("="*60)

        if not data:
            print("データがありません")
            return

        # 基本統計
        print(f"\n総件数: {len(data)}件\n")

        # 投稿日時データの有無
        has_published_at = sum(1 for item in data if item.get('published_at'))
        print(f"投稿日時データ: {has_published_at}件 ({has_published_at/len(data)*100:.1f}%)")

        # タグデータの有無
        has_tags = sum(1 for item in data if item.get('tags'))
        print(f"タグデータ: {has_tags}件 ({has_tags/len(data)*100:.1f}%)")

        # release_dateの有無
        has_release_date = sum(1 for item in data if item.get('release_date'))
        print(f"release_date: {has_release_date}件 ({has_release_date/len(data)*100:.1f}%)")

        # 視聴数統計
        view_counts = [item.get('view_count', 0) for item in data if item.get('view_count')]
        if view_counts:
            import statistics
            print(f"\n視聴数統計:")
            print(f"  平均: {statistics.mean(view_counts):,.0f}")
            print(f"  中央値: {statistics.median(view_counts):,.0f}")
            print(f"  最小: {min(view_counts):,.0f}")
            print(f"  最大: {max(view_counts):,.0f}")

        print()


def main():
    """メイン実行"""
    import sys

    integrator = DataIntegrator()

    # データ読み込み
    integrator.load_all_sources()

    # データ統合
    integrated_data = integrator.integrate_data()

    # YouTube API エンリッチメント（オプション）
    print("="*60)
    print("YouTube API エンリッチメント")
    print("="*60)
    user_input = input("YouTube APIでデータを補強しますか？ (y/n): ").strip().lower()

    if user_input == 'y':
        try:
            # YouTube API Enricherをインポート
            from youtube_api_enricher import YouTubeAPIEnricher
            from main import YOUTUBE_API_KEYS

            enricher = YouTubeAPIEnricher(YOUTUBE_API_KEYS)

            print("\n📊 エンリッチメント設定:")
            print("  - 動画詳細データ: ON")
            print("  - チャンネルデータ: ON")
            print("  - 関連動画データ: OFF")
            print()

            # エンリッチメント実行
            integrated_data = enricher.enrich_dataset(
                integrated_data,
                include_channel=True,
                include_related=False,
                verbose=True
            )

            print("✅ YouTube APIエンリッチメント完了")
            print()

        except ImportError as e:
            print(f"⚠ youtube_api_enricher.py のインポートに失敗: {e}")
            print("  エンリッチメントなしで続行します")
        except Exception as e:
            print(f"⚠ エンリッチメント中にエラー: {e}")
            print("  エンリッチメントなしで続行します")
    else:
        print("⏭ エンリッチメントをスキップ")
        print()

    # YouTubeアナリティクス統合（オプション）
    print("="*60)
    print("YouTubeアナリティクス統合")
    print("="*60)
    analytics_input = input("YouTubeアナリティクスデータを統合しますか？ (y/n): ").strip().lower()

    if analytics_input == 'y':
        try:
            from youtube_analytics_integrator import YouTubeAnalyticsIntegrator

            analytics_integrator = YouTubeAnalyticsIntegrator()
            analytics_integrator.load_all_analytics()

            # 広告フィルタリング
            filter_ads_input = input("広告動画を除外しますか？ (y/n, デフォルト: y): ").strip().lower() or 'y'
            filter_ads = (filter_ads_input == 'y')

            integrated_data = analytics_integrator.enrich_ml_training_data(
                integrated_data,
                filter_ads=filter_ads
            )

            print("✅ YouTubeアナリティクス統合完了")
            print()

        except ImportError as e:
            print(f"⚠ youtube_analytics_integrator.py のインポートに失敗: {e}")
            print("  アナリティクス統合なしで続行します")
        except Exception as e:
            print(f"⚠ アナリティクス統合中にエラー: {e}")
            print("  アナリティクス統合なしで続行します")
    else:
        print("⏭ アナリティクス統合をスキップ")
        print()

    # 統計分析
    integrator.analyze_integrated_data(integrated_data)

    # 保存
    integrator.save_integrated_data(integrated_data)

    print("="*60)
    print("✅ 完了")
    print("="*60)
    print()
    print("次のステップ:")
    print("  1. ML_training_data.json を確認")
    print("  2. main.py でオプション10を実行してML/RL訓練")
    print()


if __name__ == '__main__':
    main()
