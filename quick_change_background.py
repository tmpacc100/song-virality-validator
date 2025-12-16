#!/usr/bin/env python3
"""
テンプレートの背景を素早く変更するツール
"""

import json
import sys
import os

BACKGROUND_DIR = '/Users/shii/Desktop/song virality validator/MEDIA/background_different_color'
TEMPLATE_PATH = 'template.json'

COLORS = {
    '1': 'red',
    '2': 'pink',
    '3': 'orange',
    '4': 'yellow',
    '5': 'blue',
    '6': 'turquoise',
    '7': 'black'
}

def change_background(color_name):
    """背景色を変更"""
    background_path = os.path.join(BACKGROUND_DIR, f'{color_name}.png')

    if not os.path.exists(background_path):
        print(f"エラー: 背景ファイルが見つかりません: {background_path}")
        return False

    # テンプレート読み込み
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template = json.load(f)

    # 背景レイヤーを更新
    updated = False
    if 'layers_ordered' in template:
        for layer in template['layers_ordered']:
            if layer['type'] == 'background':
                old_path = layer.get('path', '')
                layer['path'] = background_path
                print(f"背景を変更しました:")
                print(f"  変更前: {os.path.basename(old_path)}")
                print(f"  変更後: {os.path.basename(background_path)}")
                updated = True
                break

    if not updated:
        print("エラー: 背景レイヤーが見つかりませんでした")
        return False

    # 保存
    with open(TEMPLATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(template, f, ensure_ascii=False, indent=2)

    print(f"✓ {TEMPLATE_PATH} を更新しました")
    return True

def main():
    print("=" * 60)
    print("背景色変更ツール")
    print("=" * 60)
    print("\n利用可能な背景色:")
    print("  1. 赤 (red)")
    print("  2. ピンク (pink)")
    print("  3. オレンジ (orange)")
    print("  4. 黄色 (yellow)")
    print("  5. 青 (blue)")
    print("  6. ターコイズ (turquoise)")
    print("  7. 黒 (black)")
    print()

    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("番号を選択 (1-7): ").strip()

    if choice in COLORS:
        color_name = COLORS[choice]
        change_background(color_name)
    else:
        print("エラー: 無効な選択です")
        sys.exit(1)

if __name__ == '__main__':
    main()
