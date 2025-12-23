#!/usr/bin/env python3
"""
包括的スケジューリングシステムの統合テスト
実際のML_training_data.jsonを使用してエンドツーエンドでテスト
"""

import json
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def test_comprehensive_system():
    """包括的スケジューリングシステムの統合テスト"""
    print("=" * 60)
    print("包括的スケジューリングシステム - 統合テスト")
    print("=" * 60)
    print()

    # ステップ1: データ読み込み
    print("【ステップ1: データ読み込み】")
    ml_data_path = 'ML_training_data.json'

    if not os.path.exists(ml_data_path):
        print(f"⚠ {ml_data_path} が見つかりません")
        print("先に data_integrator.py を実行してください")
        return

    with open(ml_data_path, 'r', encoding='utf-8') as f:
        songs_data = json.load(f)

    print(f"✓ {len(songs_data)}件のデータを読み込みました")

    # アナリティクスデータの有無をチェック
    with_analytics = sum(1 for s in songs_data if 'analytics_views' in s)
    print(f"  - アナリティクスデータあり: {with_analytics}件 ({with_analytics/len(songs_data)*100:.1f}%)")

    with_release_date = sum(1 for s in songs_data if s.get('release_date'))
    print(f"  - release_dateあり: {with_release_date}件")
    print()

    # ステップ2: 特徴量エンジニアリング
    print("【ステップ2: 特徴量エンジニアリング】")

    try:
        from feature_engineering import FeatureEngineer

        engineer = FeatureEngineer()
        X, feature_names = engineer.engineer_features(songs_data)

        print(f"✓ 特徴量生成完了: {len(feature_names)}次元")
        print(f"  サンプル特徴量: {feature_names[:10]}")
        print()

    except Exception as e:
        print(f"⚠ 特徴量エンジニアリング失敗: {e}")
        print("  ダミー特徴量を使用します")

        # ダミー特徴量
        X = pd.DataFrame({
            'hour': [18] * len(songs_data),
            'is_weekend': [0] * len(songs_data),
            'view_count': [s.get('view_count', 0) for s in songs_data],
        })
        feature_names = list(X.columns)
        print()

    # ステップ3: ML予測モデル訓練
    print("【ステップ3: ML視聴数予測モデル訓練】")

    try:
        from ml_scheduler import ViewCountPredictor

        y = np.array([s.get('view_count', 0) for s in songs_data])

        predictor = ViewCountPredictor(input_dim=len(feature_names))
        predictor.train(X, y, epochs=20, use_augmentation=True, verbose=1)

        # 予測実行
        predicted_views, confidence = predictor.predict(X)

        # songs_dataに予測結果を追加
        for idx, song in enumerate(songs_data):
            song['predicted_view_count'] = int(predicted_views[idx])
            song['confidence_score'] = float(confidence[idx])

        print(f"\n✓ {len(songs_data)}曲の視聴数を予測")
        print(f"  平均予測視聴数: {np.mean(predicted_views):,.0f}")
        print(f"  平均信頼度: {np.mean(confidence):.2%}")
        print()

    except Exception as e:
        print(f"⚠ ML予測モデル訓練失敗: {e}")
        print("  既存のview_countを予測値として使用します")

        for song in songs_data:
            song['predicted_view_count'] = song.get('view_count', 10000)
            song['confidence_score'] = 0.5

        print()

    # ステップ4: 包括的スケジューリング最適化
    print("【ステップ4: 包括的スケジューリング最適化】")

    try:
        from comprehensive_rl_scheduler import ComprehensiveScheduler

        # テスト用に最初の50曲のみ使用
        test_songs = songs_data[:50]

        scheduler = ComprehensiveScheduler(ml_predictor=predictor if 'predictor' in locals() else None)

        # カスタム制約
        custom_constraints = {
            'min_interval_hours': 6,
            'max_posts_per_day': 2,
            'max_days_ahead': 90,
            'preferred_hours': [18, 19, 20, 21],
            'avoid_hours': [0, 1, 2, 3, 4, 5],
        }

        optimized_schedule = scheduler.optimize_schedule(
            test_songs,
            optimization_mode='comprehensive',
            constraints=custom_constraints,
            verbose=True
        )

        print(f"\n✓ {len(optimized_schedule)}曲のスケジュールを最適化")
        print()

    except Exception as e:
        print(f"⚠ スケジューリング最適化失敗: {e}")
        import traceback
        traceback.print_exc()
        return

    # ステップ5: 結果分析
    print("【ステップ5: 結果分析】")

    # スケジューリングモード別の統計
    free_count = sum(1 for s in optimized_schedule if s.get('scheduling_mode') == 'free')
    date_fixed_count = sum(1 for s in optimized_schedule if s.get('scheduling_mode') == 'date_fixed')

    print(f"スケジューリングモード:")
    print(f"  - 自由スケジュール: {free_count}曲")
    print(f"  - 日付固定（時間最適化）: {date_fixed_count}曲")
    print()

    # 投稿日の分布
    posting_dates = {}
    for song in optimized_schedule:
        posting_datetime = datetime.fromisoformat(song['optimal_posting_datetime'])
        date_str = posting_datetime.date().isoformat()

        if date_str not in posting_dates:
            posting_dates[date_str] = 0
        posting_dates[date_str] += 1

    print(f"投稿日の分布:")
    for date_str in sorted(posting_dates.keys())[:10]:
        count = posting_dates[date_str]
        print(f"  {date_str}: {count}曲")

    if len(posting_dates) > 10:
        print(f"  ... （他{len(posting_dates) - 10}日）")

    print()

    # 総予測視聴数
    total_predicted_views = sum(s.get('predicted_view_count', 0) for s in optimized_schedule)
    print(f"総予測視聴数: {total_predicted_views:,}")
    print()

    # ステップ6: 結果保存
    print("【ステップ6: 結果保存】")

    output_json = 'test_optimized_schedule.json'
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(optimized_schedule, f, ensure_ascii=False, indent=2)

    print(f"✓ JSON保存: {output_json}")

    # CSV保存
    output_csv = 'test_optimized_schedule.csv'
    schedule_for_csv = []

    for song in optimized_schedule:
        csv_row = {
            '投稿日時': song.get('optimal_posting_datetime', ''),
            '曲名': song.get('song_name', ''),
            'アーティスト名': song.get('artist_name', ''),
            '予測視聴数': song.get('predicted_view_count', 0),
            '信頼度': round(song.get('confidence_score', 0), 3),
            'スケジュールモード': song.get('scheduling_mode', ''),
            'release_date': song.get('release_date', ''),
            '優先スコア': round(song.get('_priority_score', 0), 1),
            '間隔調整': '有' if song.get('interval_adjusted', False) else '無',
            '既存視聴数': song.get('view_count', 0),
            'アナリティクス視聴数': song.get('analytics_views', 0),
            'アナリティクス高評価率': round(song.get('analytics_like_rate', 0), 2),
            'アナリティクス視聴維持率': round(song.get('analytics_retention_rate', 0), 2),
        }
        schedule_for_csv.append(csv_row)

    import csv
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        if schedule_for_csv:
            writer = csv.DictWriter(f, fieldnames=schedule_for_csv[0].keys())
            writer.writeheader()
            writer.writerows(schedule_for_csv)

    print(f"✓ CSV保存: {output_csv}")
    print()

    # ステップ7: サマリー表示
    print("=" * 60)
    print("✅ 統合テスト完了")
    print("=" * 60)
    print()
    print("【サマリー】")
    print(f"  対象曲数: {len(optimized_schedule)}曲")
    print(f"  総予測視聴数: {total_predicted_views:,}")
    print(f"  平均予測視聴数: {total_predicted_views/len(optimized_schedule):,.0f}")
    print(f"  投稿期間: {min(posting_dates.keys())} 〜 {max(posting_dates.keys())}")
    print(f"  投稿日数: {len(posting_dates)}日")
    print()
    print("次のステップ:")
    print(f"  1. {output_csv} をExcelで開いて確認")
    print("  2. 必要に応じて制約条件を調整")
    print("  3. main.py にオプション10として統合")
    print()


if __name__ == '__main__':
    test_comprehensive_system()
