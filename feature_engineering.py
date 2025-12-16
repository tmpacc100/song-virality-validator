"""
特徴量エンジニアリングモジュール
YouTube動画の視聴数予測のための特徴量を生成
"""

import datetime
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any
import re

# チャンネル固有特徴量を読み込み
try:
    from channel_specific_features import ChannelSpecificFeatureEngineer
    CHANNEL_FEATURES_AVAILABLE = True
except ImportError:
    CHANNEL_FEATURES_AVAILABLE = False
    print("警告: channel_specific_features.py が見つかりません。チャンネル固有特徴量は使用されません。")


class FeatureEngineer:
    """特徴量エンジニアリングクラス"""

    def __init__(self, use_channel_features=True):
        self.artist_encoder = {}
        self.tag_encoder = {}
        self.use_channel_features = use_channel_features and CHANNEL_FEATURES_AVAILABLE

        # チャンネル固有特徴量エンジニア
        if self.use_channel_features:
            try:
                self.channel_engineer = ChannelSpecificFeatureEngineer()
                print("✓ チャンネル固有特徴量エンジニアを初期化しました")
            except Exception as e:
                print(f"⚠ チャンネル固有特徴量の初期化に失敗: {e}")
                self.use_channel_features = False
                self.channel_engineer = None
        else:
            self.channel_engineer = None

    def extract_temporal_features(self, datetime_obj: datetime.datetime,
                                  release_date_str: str = '') -> Dict[str, float]:
        """時間的特徴を抽出

        Args:
            datetime_obj: 投稿予定日時
            release_date_str: リリース日（YYYY/MM/DD形式）

        Returns:
            時間的特徴の辞書
        """
        features = {}

        # 基本的な時間特徴
        features['hour'] = datetime_obj.hour
        features['day_of_week'] = datetime_obj.weekday()  # 0=月曜
        features['month'] = datetime_obj.month
        features['day_of_month'] = datetime_obj.day

        # 周期性エンコーディング（サイクリック特徴）
        features['hour_sin'] = np.sin(2 * np.pi * datetime_obj.hour / 24)
        features['hour_cos'] = np.cos(2 * np.pi * datetime_obj.hour / 24)
        features['dow_sin'] = np.sin(2 * np.pi * datetime_obj.weekday() / 7)
        features['dow_cos'] = np.cos(2 * np.pi * datetime_obj.weekday() / 7)
        features['month_sin'] = np.sin(2 * np.pi * datetime_obj.month / 12)
        features['month_cos'] = np.cos(2 * np.pi * datetime_obj.month / 12)

        # カテゴリカル特徴
        features['is_weekend'] = 1 if datetime_obj.weekday() >= 5 else 0
        features['is_weekday'] = 1 if datetime_obj.weekday() < 5 else 0

        # 時間帯（0:night, 1:morning, 2:afternoon, 3:evening）
        hour = datetime_obj.hour
        if 0 <= hour < 6:
            time_period = 0  # night
        elif 6 <= hour < 12:
            time_period = 1  # morning
        elif 12 <= hour < 18:
            time_period = 2  # afternoon
        else:
            time_period = 3  # evening

        features['time_period'] = time_period
        features['is_morning'] = 1 if time_period == 1 else 0
        features['is_afternoon'] = 1 if time_period == 2 else 0
        features['is_evening'] = 1 if time_period == 3 else 0
        features['is_night'] = 1 if time_period == 0 else 0

        # ピーク時間（18-21時）
        features['is_peak_hour'] = 1 if 18 <= hour <= 21 else 0

        # 季節（0:冬, 1:春, 2:夏, 3:秋）
        season = (datetime_obj.month % 12) // 3
        features['season'] = season

        # release_dateとの関係
        if release_date_str:
            try:
                release_date = datetime.datetime.strptime(release_date_str, '%Y/%m/%d')
                days_diff = (datetime_obj.date() - release_date.date()).days
                features['days_since_release'] = days_diff
                features['is_past_release'] = 1 if days_diff >= 0 else 0
                features['is_release_day'] = 1 if days_diff == 0 else 0
            except:
                features['days_since_release'] = 0
                features['is_past_release'] = 0
                features['is_release_day'] = 0
        else:
            features['days_since_release'] = 0
            features['is_past_release'] = 0
            features['is_release_day'] = 0

        # チャンネル固有特徴量を追加
        if self.use_channel_features and self.channel_engineer:
            try:
                channel_features = self.channel_engineer.extract_channel_performance_features(datetime_obj)
                features.update(channel_features)
            except Exception as e:
                print(f"⚠ チャンネル固有特徴量の抽出に失敗: {e}")

        return features

    def extract_content_features(self, song_data: Dict[str, Any],
                                taiko_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """コンテンツ特徴を抽出

        Args:
            song_data: 曲データ
            taiko_data: TaikoGameサーバーからの追加データ

        Returns:
            コンテンツ特徴の辞書
        """
        features = {}

        # アーティスト情報
        artist_name = song_data.get('artist_name', '')
        features['artist_name'] = artist_name

        # アーティストの過去の平均視聴数（後で計算）
        features['artist_avg_views'] = 0  # プレースホルダー

        # タグ情報（TaikoGameデータから）
        tags = []
        if taiko_data and 'tags' in taiko_data:
            tags_str = taiko_data.get('tags', '[]')
            try:
                # JSON文字列をパース
                tags = eval(tags_str) if tags_str else []
            except:
                tags = []

        features['tags'] = tags
        features['tag_count'] = len(tags)

        # 特定のタグフラグ
        features['has_vocaloid_tag'] = 1 if 'ボカロ' in tags else 0
        features['has_anime_tag'] = 1 if 'アニメ' in tags else 0
        features['has_pop_tag'] = 1 if 'ポップス' in tags else 0
        features['has_game_tag'] = 1 if 'ゲーム' in tags else 0

        # 難易度（TaikoGameデータから）
        if taiko_data and 'difficulty' in taiko_data:
            difficulty_str = taiko_data.get('difficulty', '')
            difficulty_avg = self._parse_difficulty(difficulty_str)
            features['difficulty_avg'] = difficulty_avg
        else:
            features['difficulty_avg'] = 0

        return features

    def extract_engagement_features(self, song_data: Dict[str, Any]) -> Dict[str, float]:
        """エンゲージメント特徴を抽出

        Args:
            song_data: 曲データ

        Returns:
            エンゲージメント特徴の辞書
        """
        features = {}

        view_count = song_data.get('view_count', 0)
        like_count = song_data.get('like_count', 0)
        comment_count = song_data.get('comment_count', 0)

        # エンゲージメント率
        if view_count > 0:
            features['like_rate'] = like_count / view_count
            features['comment_rate'] = comment_count / view_count
            features['engagement_rate'] = (like_count + comment_count * 10) / view_count
        else:
            features['like_rate'] = 0
            features['comment_rate'] = 0
            features['engagement_rate'] = 0

        # 既存の指標
        features['support_rate'] = song_data.get('support_rate', 0)
        features['growth_rate'] = song_data.get('growth_rate', 0)
        features['days_since_published'] = song_data.get('days_since_published', 0)

        # ログスケール特徴（スケール不変）
        features['log_view_count'] = np.log1p(view_count)
        features['log_like_count'] = np.log1p(like_count)
        features['log_comment_count'] = np.log1p(comment_count)

        return features

    def create_interaction_features(self, temporal_features: Dict[str, float],
                                   content_features: Dict[str, Any]) -> Dict[str, float]:
        """交互作用特徴を作成

        Args:
            temporal_features: 時間的特徴
            content_features: コンテンツ特徴

        Returns:
            交互作用特徴の辞書
        """
        features = {}

        # タグ × 時間帯の交互作用
        features['anime_evening'] = content_features['has_anime_tag'] * temporal_features['is_evening']
        features['vocaloid_night'] = content_features['has_vocaloid_tag'] * temporal_features['is_night']
        features['pop_afternoon'] = content_features['has_pop_tag'] * temporal_features['is_afternoon']

        # 週末 × 難易度
        features['weekend_hard'] = temporal_features['is_weekend'] * content_features['difficulty_avg']

        # ピーク時間 × タグ
        features['peak_anime'] = temporal_features['is_peak_hour'] * content_features['has_anime_tag']
        features['peak_vocaloid'] = temporal_features['is_peak_hour'] * content_features['has_vocaloid_tag']

        return features

    def prepare_training_data(self, songs_data: List[Dict[str, Any]],
                             taiko_data_map: Dict[str, Dict[str, Any]] = None,
                             target_datetime: datetime.datetime = None) -> Tuple[pd.DataFrame, np.ndarray, List[str]]:
        """訓練データを準備

        Args:
            songs_data: 曲データのリスト
            taiko_data_map: 曲名 -> TaikoGameデータのマッピング
            target_datetime: 予測対象の日時（指定しない場合は現在）

        Returns:
            (特徴量DataFrame, ターゲット配列, 特徴量名リスト)
        """
        if target_datetime is None:
            target_datetime = datetime.datetime.now()

        if taiko_data_map is None:
            taiko_data_map = {}

        # アーティストごとの平均視聴数を計算
        artist_stats = self._calculate_artist_stats(songs_data)

        all_features = []
        targets = []

        for song in songs_data:
            # 各特徴量を抽出
            temporal = self.extract_temporal_features(
                target_datetime,
                song.get('release_date', '')
            )

            taiko_data = taiko_data_map.get(song.get('song_name', ''), {})
            content = self.extract_content_features(song, taiko_data)

            # アーティスト統計を追加
            artist_name = content['artist_name']
            content['artist_avg_views'] = artist_stats.get(artist_name, {}).get('avg_views', 0)
            content['artist_video_count'] = artist_stats.get(artist_name, {}).get('count', 0)

            engagement = self.extract_engagement_features(song)
            interaction = self.create_interaction_features(temporal, content)

            # すべての特徴量を結合（数値のみ）
            combined = {}
            combined.update(temporal)
            combined.update({k: v for k, v in content.items() if isinstance(v, (int, float))})
            combined.update(engagement)
            combined.update(interaction)

            all_features.append(combined)
            targets.append(song.get('view_count', 0))

        # DataFrameに変換
        features_df = pd.DataFrame(all_features)
        targets_array = np.array(targets)
        feature_names = features_df.columns.tolist()

        return features_df, targets_array, feature_names

    def _calculate_artist_stats(self, songs_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """アーティストごとの統計を計算

        Args:
            songs_data: 曲データのリスト

        Returns:
            アーティスト名 -> 統計情報の辞書
        """
        artist_stats = {}

        for song in songs_data:
            artist = song.get('artist_name', '')
            if not artist:
                continue

            if artist not in artist_stats:
                artist_stats[artist] = {'views': [], 'count': 0}

            artist_stats[artist]['views'].append(song.get('view_count', 0))
            artist_stats[artist]['count'] += 1

        # 平均を計算
        for artist, stats in artist_stats.items():
            stats['avg_views'] = np.mean(stats['views']) if stats['views'] else 0
            stats['max_views'] = np.max(stats['views']) if stats['views'] else 0
            stats['min_views'] = np.min(stats['views']) if stats['views'] else 0

        return artist_stats

    def _parse_difficulty(self, difficulty_str: str) -> float:
        """難易度文字列から平均難易度を計算

        Args:
            difficulty_str: 難易度文字列（例: "かんたん：1むずかしい：6げきむず：0"）

        Returns:
            平均難易度
        """
        try:
            # 数字を抽出
            numbers = re.findall(r'\d+', difficulty_str)
            if len(numbers) >= 3:
                easy, normal, hard = map(int, numbers[:3])
                # 重み付き平均（1: easy, 5: normal, 10: hard）
                total = easy + normal + hard
                if total > 0:
                    weighted_avg = (easy * 1 + normal * 5 + hard * 10) / total
                    return weighted_avg
        except:
            pass
        return 0.0


def main():
    """テスト用メイン関数"""
    import json

    # サンプルデータで動作確認
    engineer = FeatureEngineer()

    # サンプル曲データ
    sample_song = {
        'song_name': 'マシュマロ',
        'artist_name': 'DECO*27',
        'release_date': '2025/11/22',
        'view_count': 15000000,
        'like_count': 200000,
        'comment_count': 5000,
        'support_rate': 1.33,
        'growth_rate': 75000,
        'days_since_published': 200
    }

    # サンプルTaikoGameデータ
    sample_taiko = {
        'tags': '["ボカロ"]',
        'difficulty': 'かんたん：0むずかしい：0げきむず：0'
    }

    # 特徴量抽出
    temporal = engineer.extract_temporal_features(
        datetime.datetime.now(),
        sample_song['release_date']
    )
    content = engineer.extract_content_features(sample_song, sample_taiko)
    engagement = engineer.extract_engagement_features(sample_song)
    interaction = engineer.create_interaction_features(temporal, content)

    print("="*60)
    print("特徴量エンジニアリング - テスト")
    print("="*60)
    print(f"\n時間的特徴 ({len(temporal)}個):")
    for k, v in list(temporal.items())[:5]:
        print(f"  {k}: {v}")
    print("  ...")

    print(f"\nコンテンツ特徴 ({len(content)}個):")
    for k, v in list(content.items())[:5]:
        print(f"  {k}: {v}")

    print(f"\nエンゲージメント特徴 ({len(engagement)}個):")
    for k, v in list(engagement.items())[:5]:
        print(f"  {k}: {v}")

    print(f"\n交互作用特徴 ({len(interaction)}個):")
    for k, v in interaction.items():
        print(f"  {k}: {v}")

    print(f"\n総特徴量数: {len(temporal) + len(content) + len(engagement) + len(interaction)}")


if __name__ == '__main__':
    main()
