#!/usr/bin/env python3
"""
包括的RLスケジューリング最適化モジュール
バイラリティ最大化 + 公開順序最適化 + 投稿間隔最適化

目標:
A. バイラリティ最大化: 最も多くの再生数・エンゲージメントを得られる時間帯を予測
B. 公開順序最適化: どの曲を先に公開すべきか、曲の組み合わせを最適化
C. 投稿間隔最適化: 曲と曲の間隔をどれくらい空けるべきか
D. 総合最適化: 上記すべてを考慮

release_dateルール:
- release_date < 今日 → ML/RLで日時を完全に自由決定
- release_date ≥ 今日 → その日付固定、時間のみML/RLで最適化
"""

import numpy as np
import datetime
from typing import Dict, List, Tuple, Any, Optional
import pandas as pd
import json


class ComprehensiveScheduler:
    """包括的スケジューリング最適化"""

    def __init__(self, ml_predictor=None):
        """
        Args:
            ml_predictor: ML視聴数予測モデル（src.ml.scheduler.ViewCountPredictor）
        """
        self.ml_predictor = ml_predictor
        self.today = datetime.datetime.now().date()

    def optimize_schedule(self, songs_data: List[Dict[str, Any]],
                         optimization_mode: str = 'comprehensive',
                         constraints: Optional[Dict[str, Any]] = None,
                         verbose: bool = True) -> List[Dict[str, Any]]:
        """スケジュール最適化のメイン関数

        Args:
            songs_data: 曲データのリスト
            optimization_mode: 最適化モード
                - 'virality': バイラリティ最大化のみ
                - 'order': 公開順序最適化のみ
                - 'interval': 投稿間隔最適化のみ
                - 'comprehensive': 総合最適化（デフォルト）
            constraints: 制約条件
            verbose: 進捗表示

        Returns:
            最適化されたスケジュール
        """
        if constraints is None:
            constraints = self._get_default_constraints()

        if verbose:
            print("=" * 60)
            print("包括的スケジューリング最適化")
            print("=" * 60)
            print(f"対象曲数: {len(songs_data)}曲")
            print(f"最適化モード: {optimization_mode}")
            print(f"制約条件: {json.dumps(constraints, indent=2, ensure_ascii=False)}")
            print()

        # ステップ1: 曲を分類
        categorized_songs = self._categorize_songs_by_release_date(songs_data)

        if verbose:
            print("=" * 60)
            print("曲の分類")
            print("=" * 60)
            print(f"  自由スケジュール可能: {len(categorized_songs['free'])}曲")
            print(f"  日付固定（時間最適化）: {len(categorized_songs['date_fixed'])}曲")
            print()

        # ステップ2: 優先順位付け（公開順序最適化）
        if optimization_mode in ['order', 'comprehensive']:
            prioritized_songs = self._prioritize_songs(songs_data, verbose=verbose)
        else:
            prioritized_songs = songs_data

        # ステップ3: 時間帯最適化（バイラリティ最大化）
        if optimization_mode in ['virality', 'comprehensive']:
            optimized_schedule = self._optimize_posting_times(
                prioritized_songs,
                categorized_songs,
                constraints,
                verbose=verbose
            )
        else:
            optimized_schedule = prioritized_songs

        # ステップ4: 投稿間隔最適化
        if optimization_mode in ['interval', 'comprehensive']:
            final_schedule = self._optimize_intervals(
                optimized_schedule,
                constraints,
                verbose=verbose
            )
        else:
            final_schedule = optimized_schedule

        # ステップ5: スケジュール検証
        validated_schedule = self._validate_schedule(final_schedule, constraints, verbose=verbose)

        if verbose:
            print()
            print("=" * 60)
            print("✅ スケジュール最適化完了")
            print("=" * 60)
            self._print_schedule_summary(validated_schedule)

        return validated_schedule

    def _categorize_songs_by_release_date(self, songs_data: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """release_dateによって曲を分類

        Returns:
            {
                'free': [完全に自由にスケジュール可能な曲],
                'date_fixed': [日付固定、時間のみ最適化可能な曲]
            }
        """
        free_songs = []
        date_fixed_songs = []

        for song in songs_data:
            release_date_str = song.get('release_date', '')

            if not release_date_str:
                # release_dateがない = 自由
                free_songs.append(song)
                continue

            try:
                release_date = datetime.datetime.fromisoformat(release_date_str).date()

                if release_date < self.today:
                    # 過去のrelease_date = 自由
                    free_songs.append(song)
                else:
                    # 未来のrelease_date = 日付固定
                    song['_fixed_date'] = release_date
                    date_fixed_songs.append(song)

            except ValueError:
                # パースエラー = 自由扱い
                free_songs.append(song)

        return {
            'free': free_songs,
            'date_fixed': date_fixed_songs
        }

    def _prioritize_songs(self, songs_data: List[Dict[str, Any]], verbose: bool = True) -> List[Dict[str, Any]]:
        """公開順序最適化: どの曲を先に公開すべきかを決定

        優先順位要素:
        1. release_dateが近い曲（締め切り優先）
        2. 予測視聴数が高い曲（バイラル可能性高）
        3. 既存の高評価率が高い曲（品質保証）
        4. チャンネル登録者増加が多い曲（成長促進）

        Args:
            songs_data: 曲データ
            verbose: 進捗表示

        Returns:
            優先順位順にソートされた曲リスト
        """
        if verbose:
            print("=" * 60)
            print("公開順序最適化")
            print("=" * 60)

        scored_songs = []

        for song in songs_data:
            score = 0

            # 1. release_date優先度（近いほど高）
            release_date_str = song.get('release_date', '')
            if release_date_str:
                try:
                    release_date = datetime.datetime.fromisoformat(release_date_str).date()
                    days_until_release = (release_date - self.today).days

                    if days_until_release >= 0:
                        # 未来のrelease_date: 近いほど高スコア
                        score += max(0, 1000 - days_until_release * 10)
                except ValueError:
                    pass

            # 2. ML予測視聴数（高いほど良い）
            predicted_views = song.get('predicted_view_count', 0)
            if predicted_views > 0:
                # 対数スケールで正規化（1万〜100万の範囲を想定）
                score += np.log1p(predicted_views) * 50

            # 3. YouTube API raw dataの相対的バズり度（他チャンネルとの比較指標）
            relative_engagement_score = song.get('relative_engagement_score', 0)
            if relative_engagement_score > 0:
                # 相対的なエンゲージメントスコア（高いほどバズりやすい）
                score += relative_engagement_score * 10

            relative_like_rate = song.get('relative_like_rate', 0)
            if relative_like_rate > 0:
                # 相対的な高評価率（品質指標）
                score += relative_like_rate * 5

            # 4. 既存のsupport_rate（品質指標）
            support_rate = song.get('support_rate', 0)
            if support_rate > 0:
                score += support_rate * 3

            # 5. アナリティクスデータがある場合（自分のチャンネルの実データ）
            analytics_like_rate = song.get('analytics_like_rate', 0)
            if analytics_like_rate > 0:
                score += analytics_like_rate * 5  # 実データは重視

            analytics_retention = song.get('analytics_retention_rate', 0)
            if analytics_retention > 0:
                score += analytics_retention * 2

            # 6. チャンネル全体のオーガニック比率（高いほど自然なバズり）
            channel_organic_ratio = song.get('channel_organic_ratio', 0)
            if channel_organic_ratio > 0:
                # オーガニック比率が高いほど自然なバズり
                score += channel_organic_ratio * 1  # 参考値なので重みは小さめ

            # 7. CTR（クリック率、高いほど魅力的）
            ctr = song.get('analytics_ctr', 0)
            if ctr > 0:
                score += ctr * 20  # CTR 5%なら100ポイント

            # 8. チャンネル登録者純増
            net_subscribers = song.get('analytics_net_subscribers', 0)
            if net_subscribers > 0:
                score += net_subscribers * 0.5

            song['_priority_score'] = score
            scored_songs.append(song)

        # スコア順にソート（降順）
        prioritized = sorted(scored_songs, key=lambda x: x['_priority_score'], reverse=True)

        if verbose:
            print("優先順位トップ10:")
            for idx, song in enumerate(prioritized[:10], 1):
                song_name = song.get('song_name', 'Unknown')
                artist = song.get('artist_name', 'Unknown')
                score = song['_priority_score']
                predicted_views = song.get('predicted_view_count', 0)
                release_date = song.get('release_date', 'なし')

                print(f"  {idx}. {song_name} - {artist}")
                print(f"     スコア: {score:.1f}, 予測視聴数: {predicted_views:,.0f}, release_date: {release_date}")

            print()

        return prioritized

    def _optimize_posting_times(self, songs_data: List[Dict[str, Any]],
                               categorized: Dict[str, List],
                               constraints: Dict[str, Any],
                               verbose: bool = True) -> List[Dict[str, Any]]:
        """投稿時間帯の最適化（バイラリティ最大化）

        Args:
            songs_data: 曲データ（優先順位順）
            categorized: 分類済み曲データ
            constraints: 制約条件
            verbose: 進捗表示

        Returns:
            投稿時間が決定された曲リスト
        """
        if verbose:
            print("=" * 60)
            print("投稿時間帯最適化")
            print("=" * 60)

        optimized_songs = []
        current_date = self.today

        for song in songs_data:
            # release_date制約をチェック
            if '_fixed_date' in song:
                # 日付固定 → 時間のみ最適化
                fixed_date = song['_fixed_date']
                optimal_hour = self._find_optimal_hour(song, fixed_date, constraints)
                optimal_datetime = datetime.datetime.combine(fixed_date, datetime.time(hour=optimal_hour))

                song['optimal_posting_datetime'] = optimal_datetime.isoformat()
                song['scheduling_mode'] = 'date_fixed'

            else:
                # 完全自由 → ML/RLで日時を決定
                optimal_date, optimal_hour = self._find_optimal_datetime(
                    song, current_date, constraints
                )
                optimal_datetime = datetime.datetime.combine(optimal_date, datetime.time(hour=optimal_hour))

                song['optimal_posting_datetime'] = optimal_datetime.isoformat()
                song['scheduling_mode'] = 'free'

                # 次の投稿は最低でも翌日以降
                current_date = optimal_date + datetime.timedelta(days=1)

            optimized_songs.append(song)

        if verbose:
            print(f"✓ {len(optimized_songs)}曲の投稿時間を最適化")
            print()

        return optimized_songs

    def _find_optimal_hour(self, song: Dict[str, Any],
                          date: datetime.date,
                          constraints: Dict[str, Any]) -> int:
        """特定の日付で最適な投稿時間（時）を見つける

        Args:
            song: 曲データ
            date: 投稿日
            constraints: 制約条件

        Returns:
            最適な時（0-23）
        """
        # ML予測がある場合は、各時間帯でシミュレーション
        if self.ml_predictor:
            best_hour = None
            best_predicted_views = 0

            candidate_hours = self._get_candidate_hours(constraints)

            for hour in candidate_hours:
                # 特徴量を生成
                features = self._create_features_for_prediction(song, date, hour)

                # 視聴数予測
                try:
                    predicted_views, confidence = self.ml_predictor.predict(features)
                    predicted_views = predicted_views[0] if isinstance(predicted_views, np.ndarray) else predicted_views

                    if predicted_views > best_predicted_views:
                        best_predicted_views = predicted_views
                        best_hour = hour
                except:
                    pass

            if best_hour is not None:
                return best_hour

        # フォールバック: ヒューリスティックな最適時間
        # 統計的に最も効果的な時間帯
        preferred_hours = constraints.get('preferred_hours', [18, 19, 20, 21])
        day_of_week = date.weekday()  # 0=月曜, 6=日曜

        if day_of_week >= 5:  # 土日
            # 週末は午後8時が最適
            return 20
        else:  # 平日
            # 平日は午後6-7時が最適
            return 18

    def _find_optimal_datetime(self, song: Dict[str, Any],
                              start_date: datetime.date,
                              constraints: Dict[str, Any]) -> Tuple[datetime.date, int]:
        """完全に自由な曲の最適な投稿日時を見つける

        Args:
            song: 曲データ
            start_date: 検索開始日
            constraints: 制約条件

        Returns:
            (最適な日付, 最適な時)
        """
        max_days_ahead = constraints.get('max_days_ahead', 90)
        best_date = start_date
        best_hour = 18
        best_predicted_views = 0

        # 今後90日間でスキャン
        for days_offset in range(max_days_ahead):
            candidate_date = start_date + datetime.timedelta(days=days_offset)

            # 曜日制約チェック
            if not self._is_allowed_day_of_week(candidate_date, constraints):
                continue

            # 最適時間を探索
            optimal_hour = self._find_optimal_hour(song, candidate_date, constraints)

            # 予測視聴数を取得
            if self.ml_predictor:
                features = self._create_features_for_prediction(song, candidate_date, optimal_hour)
                try:
                    predicted_views, confidence = self.ml_predictor.predict(features)
                    predicted_views = predicted_views[0] if isinstance(predicted_views, np.ndarray) else predicted_views

                    if predicted_views > best_predicted_views:
                        best_predicted_views = predicted_views
                        best_date = candidate_date
                        best_hour = optimal_hour
                except:
                    pass

        return best_date, best_hour

    def _optimize_intervals(self, songs_data: List[Dict[str, Any]],
                           constraints: Dict[str, Any],
                           verbose: bool = True) -> List[Dict[str, Any]]:
        """投稿間隔の最適化

        目標:
        - 視聴者疲労を避ける（連続投稿による効果減衰）
        - チャンネルアルゴリズムを最適化（適度な投稿頻度）
        - 視聴者の期待値を維持

        Args:
            songs_data: スケジュール済み曲データ
            constraints: 制約条件
            verbose: 進捗表示

        Returns:
            間隔調整後のスケジュール
        """
        if verbose:
            print("=" * 60)
            print("投稿間隔最適化")
            print("=" * 60)

        min_interval_hours = constraints.get('min_interval_hours', 6)
        max_posts_per_day = constraints.get('max_posts_per_day', 2)

        # 投稿時間でソート
        sorted_songs = sorted(
            songs_data,
            key=lambda x: datetime.datetime.fromisoformat(x['optimal_posting_datetime'])
        )

        adjusted_songs = []
        previous_datetime = None
        posts_on_current_day = 0
        current_day = None

        for song in sorted_songs:
            optimal_datetime = datetime.datetime.fromisoformat(song['optimal_posting_datetime'])

            # 日付が変わったらカウントリセット
            if current_day != optimal_datetime.date():
                current_day = optimal_datetime.date()
                posts_on_current_day = 0

            # 前回投稿からの間隔をチェック
            if previous_datetime:
                interval_hours = (optimal_datetime - previous_datetime).total_seconds() / 3600

                if interval_hours < min_interval_hours:
                    # 間隔が短すぎる → 調整
                    adjusted_datetime = previous_datetime + datetime.timedelta(hours=min_interval_hours)
                    song['optimal_posting_datetime'] = adjusted_datetime.isoformat()
                    song['interval_adjusted'] = True
                    optimal_datetime = adjusted_datetime

            # 1日あたりの投稿数制限
            if posts_on_current_day >= max_posts_per_day:
                # 翌日に延期
                next_day = current_day + datetime.timedelta(days=1)
                adjusted_datetime = datetime.datetime.combine(next_day, datetime.time(hour=18))
                song['optimal_posting_datetime'] = adjusted_datetime.isoformat()
                song['interval_adjusted'] = True
                optimal_datetime = adjusted_datetime

                current_day = next_day
                posts_on_current_day = 1
            else:
                posts_on_current_day += 1

            adjusted_songs.append(song)
            previous_datetime = optimal_datetime

        if verbose:
            adjusted_count = sum(1 for s in adjusted_songs if s.get('interval_adjusted', False))
            print(f"✓ {adjusted_count}曲の投稿時間を間隔調整")
            print()

        return adjusted_songs

    def _validate_schedule(self, songs_data: List[Dict[str, Any]],
                          constraints: Dict[str, Any],
                          verbose: bool = True) -> List[Dict[str, Any]]:
        """スケジュールの検証

        制約違反をチェックし、警告を出力

        Args:
            songs_data: スケジュール済み曲データ
            constraints: 制約条件
            verbose: 進捗表示

        Returns:
            検証済みスケジュール
        """
        if verbose:
            print("=" * 60)
            print("スケジュール検証")
            print("=" * 60)

        violations = []

        # 投稿時間でソート
        sorted_songs = sorted(
            songs_data,
            key=lambda x: datetime.datetime.fromisoformat(x['optimal_posting_datetime'])
        )

        previous_datetime = None

        for song in sorted_songs:
            optimal_datetime = datetime.datetime.fromisoformat(song['optimal_posting_datetime'])

            # 間隔チェック
            if previous_datetime:
                interval_hours = (optimal_datetime - previous_datetime).total_seconds() / 3600
                min_interval = constraints.get('min_interval_hours', 6)

                if interval_hours < min_interval:
                    violations.append(f"⚠ 間隔違反: {song.get('song_name')} ({interval_hours:.1f}時間 < {min_interval}時間)")

            previous_datetime = optimal_datetime

        if verbose:
            if violations:
                print("制約違反が検出されました:")
                for violation in violations:
                    print(f"  {violation}")
            else:
                print("✓ すべての制約を満たしています")

            print()

        return sorted_songs

    def _create_features_for_prediction(self, song: Dict[str, Any],
                                       date: datetime.date,
                                       hour: int) -> pd.DataFrame:
        """ML予測用の特徴量を生成

        Args:
            song: 曲データ
            date: 投稿日
            hour: 投稿時

        Returns:
            特徴量DataFrame
        """
        features = {
            'hour': hour,
            'day_of_week': date.weekday(),
            'is_weekend': 1 if date.weekday() >= 5 else 0,
            'month': date.month,
        }

        # 曲の既存特徴量を追加
        for key in ['view_count', 'like_count', 'comment_count', 'support_rate',
                   'growth_rate', 'analytics_avg_percentage_viewed', 'analytics_retention_rate',
                   'analytics_engagement_rate', 'analytics_ctr']:
            if key in song:
                features[key] = song[key]
            else:
                features[key] = 0

        return pd.DataFrame([features])

    @staticmethod
    def _get_default_constraints() -> Dict[str, Any]:
        """デフォルトの制約条件を取得"""
        return {
            'min_interval_hours': 6,  # 最低投稿間隔（時間）
            'max_posts_per_day': 2,  # 1日あたり最大投稿数
            'max_days_ahead': 90,  # 何日先までスケジュール可能か
            'preferred_hours': [18, 19, 20, 21],  # 推奨投稿時間帯
            'avoid_hours': [0, 1, 2, 3, 4, 5],  # 避けるべき時間帯
            'preferred_days': [0, 1, 2, 3, 4, 5, 6],  # 推奨曜日（0=月曜）
        }

    @staticmethod
    def _get_candidate_hours(constraints: Dict[str, Any]) -> List[int]:
        """候補となる投稿時間のリストを取得"""
        avoid_hours = set(constraints.get('avoid_hours', []))
        return [h for h in range(24) if h not in avoid_hours]

    @staticmethod
    def _is_allowed_day_of_week(date: datetime.date, constraints: Dict[str, Any]) -> bool:
        """曜日が許可されているかチェック"""
        preferred_days = constraints.get('preferred_days', [0, 1, 2, 3, 4, 5, 6])
        return date.weekday() in preferred_days

    @staticmethod
    def _print_schedule_summary(schedule: List[Dict[str, Any]]):
        """スケジュールのサマリーを表示"""
        print()
        print("【今後の投稿スケジュール（最初の20曲）】")
        print()

        for idx, song in enumerate(schedule[:20], 1):
            song_name = song.get('song_name', 'Unknown')
            artist = song.get('artist_name', 'Unknown')
            optimal_datetime = datetime.datetime.fromisoformat(song['optimal_posting_datetime'])
            predicted_views = song.get('predicted_view_count', 0)
            scheduling_mode = song.get('scheduling_mode', 'unknown')

            mode_icon = "🔒" if scheduling_mode == 'date_fixed' else "🆓"
            interval_icon = "⚙" if song.get('interval_adjusted', False) else ""

            print(f"{idx:2}. {optimal_datetime.strftime('%Y/%m/%d %H:%M')} {mode_icon}{interval_icon}")
            print(f"    {song_name} - {artist}")
            print(f"    予測視聴数: {predicted_views:,.0f}")
            print()

        total_predicted_views = sum(s.get('predicted_view_count', 0) for s in schedule)
        print(f"総予測視聴数: {total_predicted_views:,.0f}")


def main():
    """テスト実行"""
    print("=" * 60)
    print("包括的RLスケジューリング - テスト")
    print("=" * 60)
    print()

    # サンプルデータ
    sample_songs = [
        {
            'song_name': '曲A（人気）',
            'artist_name': 'アーティストX',
            'release_date': '',
            'predicted_view_count': 150000,
            'support_rate': 95,
            'view_count': 50000,
        },
        {
            'song_name': '曲B（締め切り近）',
            'artist_name': 'アーティストY',
            'release_date': (datetime.date.today() + datetime.timedelta(days=3)).isoformat(),
            'predicted_view_count': 80000,
            'support_rate': 90,
            'view_count': 30000,
        },
        {
            'song_name': '曲C（通常）',
            'artist_name': 'アーティストZ',
            'release_date': '',
            'predicted_view_count': 60000,
            'support_rate': 85,
            'view_count': 20000,
        },
    ]

    # スケジューラー初期化
    scheduler = ComprehensiveScheduler()

    # 最適化実行
    optimized_schedule = scheduler.optimize_schedule(
        sample_songs,
        optimization_mode='comprehensive',
        verbose=True
    )

    print()
    print("=" * 60)
    print("✅ テスト完了")
    print("=" * 60)


if __name__ == '__main__':
    main()
