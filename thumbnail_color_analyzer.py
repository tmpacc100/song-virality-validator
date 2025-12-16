#!/usr/bin/env python3
"""
YouTubeサムネイルの色分析システム
曲のカテゴリーに基づいて最適な背景色を選択
"""

import requests
from PIL import Image
from io import BytesIO
import numpy as np
from sklearn.cluster import KMeans
from collections import Counter
import colorsys
import os


class ThumbnailColorAnalyzer:
    """YouTubeサムネイルの主要色を分析"""

    # 利用可能な背景色
    AVAILABLE_COLORS = {
        'red': (220, 53, 69),      # 赤
        'pink': (255, 105, 180),   # ピンク
        'orange': (255, 159, 64),  # オレンジ
        'yellow': (255, 205, 86),  # 黄色
        'blue': (54, 162, 235),    # 青
        'turquoise': (64, 224, 208), # ターコイズ
        'black': (40, 40, 40)      # 黒
    }

    def __init__(self, background_dir='/Users/shii/Desktop/song virality validator/MEDIA/background_different_color'):
        self.background_dir = background_dir

    def get_youtube_thumbnail_url(self, video_id):
        """YouTube動画IDからサムネイルURLを取得

        Args:
            video_id: YouTube動画ID

        Returns:
            サムネイルURL
        """
        # 高解像度サムネイルを優先
        return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

    def download_thumbnail(self, video_id):
        """サムネイルをダウンロード

        Args:
            video_id: YouTube動画ID

        Returns:
            PIL Image オブジェクト
        """
        url = self.get_youtube_thumbnail_url(video_id)

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))
            return img.convert('RGB')
        except Exception as e:
            print(f"警告: サムネイルのダウンロードに失敗 ({video_id}): {e}")
            # フォールバック: 低解像度サムネイル
            fallback_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
            try:
                response = requests.get(fallback_url, timeout=10)
                img = Image.open(BytesIO(response.content))
                return img.convert('RGB')
            except:
                return None

    def get_dominant_colors(self, image, n_colors=5):
        """画像の主要色をK-meansで抽出

        Args:
            image: PIL Image
            n_colors: 抽出する色数

        Returns:
            主要色のリスト [(R, G, B), ...]
        """
        if image is None:
            return []

        # 画像をリサイズして処理を高速化
        image = image.resize((150, 150))

        # 画像を配列に変換
        pixels = np.array(image).reshape(-1, 3)

        # K-meansクラスタリング
        kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
        kmeans.fit(pixels)

        # クラスタ中心（主要色）
        colors = kmeans.cluster_centers_.astype(int)

        # 各色の出現頻度
        labels = kmeans.labels_
        label_counts = Counter(labels)

        # 頻度順にソート
        sorted_colors = [colors[i] for i, _ in label_counts.most_common()]

        return [tuple(color) for color in sorted_colors]

    def color_distance(self, color1, color2):
        """2つの色の距離を計算（ユークリッド距離）

        Args:
            color1: (R, G, B)
            color2: (R, G, B)

        Returns:
            距離
        """
        return np.sqrt(sum((c1 - c2) ** 2 for c1, c2 in zip(color1, color2)))

    def find_closest_background_color(self, thumbnail_colors):
        """サムネイル色に最も近い背景色を見つける

        Args:
            thumbnail_colors: サムネイルの主要色リスト

        Returns:
            最も近い背景色の名前
        """
        if not thumbnail_colors:
            return 'black'  # デフォルト

        # 最も支配的な色（1番目）を使用
        dominant_color = thumbnail_colors[0]

        # 各背景色との距離を計算
        distances = {}
        for name, bg_color in self.AVAILABLE_COLORS.items():
            distance = self.color_distance(dominant_color, bg_color)
            distances[name] = distance

        # 最小距離の色を返す
        closest_color = min(distances, key=distances.get)

        print(f"  サムネイル主要色: RGB{dominant_color}")
        print(f"  選択された背景色: {closest_color} (距離: {distances[closest_color]:.1f})")

        return closest_color

    def analyze_video_thumbnail(self, video_id):
        """動画のサムネイルを分析して最適な背景色を返す

        Args:
            video_id: YouTube動画ID

        Returns:
            背景色ファイルのパス
        """
        print(f"\nサムネイル分析: {video_id}")

        # サムネイルをダウンロード
        thumbnail = self.download_thumbnail(video_id)
        if thumbnail is None:
            print("  ⚠ サムネイル取得失敗、デフォルト色を使用")
            return os.path.join(self.background_dir, 'black.png')

        # 主要色を抽出
        dominant_colors = self.get_dominant_colors(thumbnail)

        # 最も近い背景色を見つける
        color_name = self.find_closest_background_color(dominant_colors)

        # 背景ファイルパスを返す
        background_path = os.path.join(self.background_dir, f'{color_name}.png')

        if os.path.exists(background_path):
            print(f"  ✓ 背景色ファイル: {color_name}.png")
            return background_path
        else:
            print(f"  ⚠ 背景ファイルが見つかりません: {background_path}")
            return os.path.join(self.background_dir, 'black.png')

    def get_category_default_color(self, tags):
        """曲のカテゴリー（タグ）から推奨背景色を取得

        Args:
            tags: タグのリスト

        Returns:
            背景色の名前
        """
        # カテゴリーごとの推奨色
        category_colors = {
            'ボカロ': 'turquoise',
            'アニメ': 'blue',
            'ポップス': 'pink',
            'ロック': 'red',
            'バラード': 'blue',
            'ゲーム': 'orange',
            'J-POP': 'yellow',
            'アイドル': 'pink'
        }

        # タグに一致する色を探す
        for tag in tags:
            for category, color in category_colors.items():
                if category in tag:
                    return color

        # デフォルト
        return 'black'


def main():
    """テスト実行"""
    analyzer = ThumbnailColorAnalyzer()

    # テストケース: 有名な曲のビデオID
    test_videos = [
        ('dQw4w9WgXcQ', 'Rick Astley - Never Gonna Give You Up'),  # ポップス
        ('9bZkp7q19f0', 'PSY - GANGNAM STYLE'),  # K-POP
    ]

    print("=" * 60)
    print("YouTubeサムネイル色分析テスト")
    print("=" * 60)

    for video_id, title in test_videos:
        print(f"\n【{title}】")
        background_path = analyzer.analyze_video_thumbnail(video_id)
        print(f"推奨背景: {background_path}")

    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)


if __name__ == '__main__':
    main()
