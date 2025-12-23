#!/usr/bin/env python3
"""
background_different_color フォルダの PNG ファイルに透明度を追加
元のファイルは .bak として保存
"""

import os
from PIL import Image

BACKGROUND_DIR = '/Users/shii/Desktop/song virality validator/MEDIA/background_different_color'
OPACITY = 1.0  # 100% の不透明度（透明度なし）

def make_transparent(image_path, opacity=0.3):
    """画像に透明度を適用"""
    # 画像を開く
    img = Image.open(image_path).convert('RGBA')

    # 新しい透明度を適用
    alpha = img.split()[3]  # 元のアルファチャンネル
    alpha = alpha.point(lambda p: int(p * opacity))

    # RGBA チャンネルを結合
    r, g, b, _ = img.split()
    img = Image.merge('RGBA', (r, g, b, alpha))

    return img

def main():
    colors = ['red', 'pink', 'orange', 'yellow', 'blue', 'turcoise', 'green', 'lightblue', 'lightgreen', 'purple']

    print("=" * 60)
    print("背景画像透明度調整")
    print("=" * 60)
    print(f"不透明度: {int(OPACITY * 100)}%")
    print()

    for color in colors:
        png_path = os.path.join(BACKGROUND_DIR, f'{color}.png')

        if not os.path.exists(png_path):
            print(f"⚠ スキップ: {color}.png が見つかりません")
            continue

        # バックアップ作成
        backup_path = os.path.join(BACKGROUND_DIR, f'{color}_original.png')
        if not os.path.exists(backup_path):
            img = Image.open(png_path)
            img.save(backup_path, 'PNG')
            print(f"✓ バックアップ作成: {color}_original.png")

        # 透明度を適用
        transparent_img = make_transparent(png_path, OPACITY)
        transparent_img.save(png_path)
        print(f"✓ 透明度適用: {color}.png ({int(OPACITY * 100)}% 不透明)")

    print()
    print("=" * 60)
    print("✅ 完了")
    print("=" * 60)
    print()
    print("元に戻すには:")
    print(f"  cd '{BACKGROUND_DIR}'")
    print(f"  cp red_original.png red.png")
    print(f"  (他の色も同様に)")

if __name__ == '__main__':
    main()
