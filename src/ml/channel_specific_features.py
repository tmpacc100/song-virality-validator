#!/usr/bin/env python3
"""
チャンネル固有のパターンを活用した特徴量エンジニアリング拡張

YouTube API から取得したチャンネル履歴データ (@taiko_de_hit_song) に基づいて
最適な投稿時間を学習する追加特徴量モジュール
"""

import pandas as pd
import numpy as np
from datetime import datetime


class ChannelSpecificFeatureEngineer:
    """
    @taiko_de_hit_song チャンネル特有のパターンを特徴量化

    channel_history.csv から抽出されたパターン:
    - 曜日別平均視聴数
    - 時間帯別平均視聴数
    - ショート動画の特性
    """

    def __init__(self, channel_history_path='channel_history_clean.csv'):
        """
        Args:
            channel_history_path: チャンネル履歴CSVのパス（デフォルト: 広告除外版）
        """
        self.channel_history_path = channel_history_path
        self.channel_data = None
        self.day_of_week_stats = None
        self.hour_stats = None

        # データ読み込みと統計計算
        self._load_channel_history()
        self._calculate_statistics()

    def _load_channel_history(self):
        """チャンネル履歴データを読み込み"""
        try:
            self.channel_data = pd.read_csv(self.channel_history_path)
            print(f"✓ チャンネル履歴データ読み込み完了: {len(self.channel_data)}件")
        except FileNotFoundError:
            print(f"⚠ {self.channel_history_path} が見つかりません。デフォルト統計を使用します。")
            self.channel_data = None

    def _calculate_statistics(self):
        """曜日別・時間帯別の統計を計算"""
        if self.channel_data is None:
            # デフォルト統計（実測値ベース）
            self.day_of_week_stats = {
                0: 1870,  # 月曜
                1: 1672,  # 火曜
                2: 1711,  # 水曜
                3: 3203,  # 木曜 (最高)
                4: 1533,  # 金曜
                5: 1981,  # 土曜
                6: 2157   # 日曜
            }

            self.hour_stats = {
                1: 1859, 2: 1343, 3: 1813, 4: 1049, 5: 2174,
                6: 2413, 7: 1345, 8: 2125, 9: 1985, 12: 681,
                13: 1405, 15: 1391
            }
        else:
            # Shorts のみをフィルタ
            shorts = self.channel_data[self.channel_data['is_short'] == True]

            # 曜日別平均視聴数
            self.day_of_week_stats = shorts.groupby('published_day_of_week')['view_count'].mean().to_dict()

            # 時間帯別平均視聴数
            self.hour_stats = shorts.groupby('published_hour')['view_count'].mean().to_dict()

        # 全体平均
        all_views = list(self.day_of_week_stats.values())
        self.overall_avg = np.mean(all_views) if all_views else 2000

        # 時間帯の全体平均
        hour_views = list(self.hour_stats.values())
        self.hour_avg = np.mean(hour_views) if hour_views else 1800

    def extract_channel_performance_features(self, datetime_obj):
        """
        チャンネル固有のパフォーマンス特徴量を抽出

        Args:
            datetime_obj: datetime オブジェクト

        Returns:
            dict: チャンネル固有特徴量
        """
        features = {}

        dow = datetime_obj.weekday()
        hour = datetime_obj.hour

        # 曜日別パフォーマンス
        expected_views_dow = self.day_of_week_stats.get(dow, self.overall_avg)
        features['channel_day_performance'] = expected_views_dow / self.overall_avg  # 正規化

        # 時間帯別パフォーマンス
        expected_views_hour = self.hour_stats.get(hour, self.hour_avg)
        features['channel_hour_performance'] = expected_views_hour / self.hour_avg  # 正規化

        # 複合パフォーマンススコア
        features['channel_combined_score'] = (
            features['channel_day_performance'] * 0.6 +
            features['channel_hour_performance'] * 0.4
        )

        # ベストタイミングフラグ
        features['is_best_day'] = 1 if dow == 3 else 0  # 木曜日
        features['is_best_hour'] = 1 if hour == 6 else 0  # 6時台
        features['is_second_best_hour'] = 1 if hour == 8 else 0  # 8時台

        # 最適時間帯（6-9時）
        features['is_morning_peak'] = 1 if 6 <= hour <= 9 else 0

        # 週末効果
        features['is_weekend_boost'] = 1 if dow in [5, 6] else 0

        # ハイブリッドパターン（木曜朝6-9時が最強）
        features['is_golden_timeslot'] = 1 if (dow == 3 and 6 <= hour <= 9) else 0

        return features

    def get_optimal_posting_times(self, top_n=10):
        """
        過去データに基づく最適投稿時間トップN

        Returns:
            list: [(day_of_week, hour, expected_views), ...]
        """
        recommendations = []

        for dow, dow_views in self.day_of_week_stats.items():
            for hour, hour_views in self.hour_stats.items():
                # 簡易推定: 曜日と時間の平均
                estimated_views = (dow_views + hour_views) / 2
                recommendations.append((dow, hour, estimated_views))

        # 期待視聴数でソート
        recommendations.sort(key=lambda x: x[2], reverse=True)

        return recommendations[:top_n]

    def print_recommendations(self):
        """最適投稿時間の推奨を表示"""
        print("\n" + "="*60)
        print("📊 チャンネル固有の最適投稿時間分析")
        print("="*60)

        print(f"\n【曜日別パフォーマンス】")
        day_names = ['月曜', '火曜', '水曜', '木曜', '金曜', '土曜', '日曜']
        sorted_days = sorted(self.day_of_week_stats.items(), key=lambda x: x[1], reverse=True)
        for i, (dow, avg_views) in enumerate(sorted_days, 1):
            boost = (avg_views / self.overall_avg - 1) * 100
            print(f"  {i}. {day_names[dow]}: {avg_views:,.0f} views ({boost:+.0f}%)")

        print(f"\n【時間帯別パフォーマンス】")
        sorted_hours = sorted(self.hour_stats.items(), key=lambda x: x[1], reverse=True)
        for i, (hour, avg_views) in enumerate(sorted_hours[:5], 1):
            boost = (avg_views / self.hour_avg - 1) * 100
            print(f"  {i}. {hour:02d}時台: {avg_views:,.0f} views ({boost:+.0f}%)")

        print(f"\n【推奨投稿スケジュール TOP 10】")
        optimal = self.get_optimal_posting_times(10)
        for i, (dow, hour, expected) in enumerate(optimal, 1):
            print(f"  {i}. {day_names[dow]} {hour:02d}時 - 期待視聴数: {expected:,.0f} views")

        print("\n" + "="*60)


# 統合特徴量エンジニア
class EnhancedFeatureEngineer:
    """
    元の FeatureEngineer + チャンネル固有特徴量を統合
    """

    def __init__(self, channel_history_path='channel_history.csv'):
        self.channel_engineer = ChannelSpecificFeatureEngineer(channel_history_path)

    def extract_all_features(self, datetime_obj, song_data=None, taiko_data=None):
        """
        全特徴量を抽出（元の特徴量 + チャンネル固有特徴量）

        Args:
            datetime_obj: 投稿予定日時
            song_data: 曲データ（オプション）
            taiko_data: Taikoサーバーデータ（オプション）

        Returns:
            dict: 統合特徴量
        """
        # チャンネル固有特徴量
        features = self.channel_engineer.extract_channel_performance_features(datetime_obj)

        # 基本的な時間特徴量も追加（元のモジュールとの互換性）
        features['hour'] = datetime_obj.hour
        features['day_of_week'] = datetime_obj.weekday()
        features['month'] = datetime_obj.month
        features['is_weekend'] = 1 if datetime_obj.weekday() >= 5 else 0

        # 周期エンコーディング
        features['hour_sin'] = np.sin(2 * np.pi * datetime_obj.hour / 24)
        features['hour_cos'] = np.cos(2 * np.pi * datetime_obj.hour / 24)
        features['day_sin'] = np.sin(2 * np.pi * datetime_obj.weekday() / 7)
        features['day_cos'] = np.cos(2 * np.pi * datetime_obj.weekday() / 7)

        return features


def main():
    """テスト実行"""
    print("="*60)
    print("チャンネル固有特徴量エンジニアリングテスト")
    print("="*60)

    engineer = ChannelSpecificFeatureEngineer()
    engineer.print_recommendations()

    # テストケース
    print("\n【特徴量抽出テスト】")
    test_cases = [
        datetime(2025, 12, 18, 6, 0),   # 木曜 6時 (最強)
        datetime(2025, 12, 18, 8, 0),   # 木曜 8時
        datetime(2025, 12, 16, 15, 0),  # 火曜 15時
    ]

    day_names = ['月曜', '火曜', '水曜', '木曜', '金曜', '土曜', '日曜']

    for dt in test_cases:
        features = engineer.extract_channel_performance_features(dt)
        print(f"\n{day_names[dt.weekday()]} {dt.hour:02d}:00")
        print(f"  曜日スコア: {features['channel_day_performance']:.3f}")
        print(f"  時間スコア: {features['channel_hour_performance']:.3f}")
        print(f"  総合スコア: {features['channel_combined_score']:.3f}")
        print(f"  ゴールデンタイム: {'✓' if features['is_golden_timeslot'] else '✗'}")


if __name__ == '__main__':
    main()
