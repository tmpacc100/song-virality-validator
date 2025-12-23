#!/usr/bin/env python3
"""
背景色ローテーションのバッチ動画生成
"""
from batch_video_with_color_rotation import ColorRotationBatchGenerator

# ジェネレーターを初期化
generator = ColorRotationBatchGenerator(
    template_path='template.json',
    base_video='MEDIA/base.mp4'
)

# 全曲の動画を生成（M1 GPU最適化済み）
generator.generate_from_csv_with_color_rotation(
    csv_path='/Users/shii/Desktop/song virality validator/filtered data/taiko_server_未投稿_filtered.csv',
    output_dir='/Users/shii/Desktop/song virality validator/output_videos',
    include_artist=True,
    max_videos=None  # 全曲生成
)

print("\n✓ 背景色ローテーション動画生成完了")
