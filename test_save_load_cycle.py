#!/usr/bin/env python3
"""
テンプレートの保存・読み込みサイクルをテスト
"""
import json
import os
import shutil

def test_save_load_cycle():
    """保存・読み込みサイクルをテスト"""

    template_path = 'template.json'
    backup_path = 'template.json.backup'

    # バックアップを作成
    if os.path.exists(template_path):
        shutil.copy(template_path, backup_path)
        print(f"✓ バックアップ作成: {backup_path}")

    # 現在のテンプレートを読み込む
    with open(template_path, 'r', encoding='utf-8') as f:
        template = json.load(f)

    print("\n=== 変更前 ===")
    print(f"動画レイヤー位置: ({template['layers_ordered'][1]['x']}, {template['layers_ordered'][1]['y']})")
    print(f"動画レイヤーサイズ: {template['layers_ordered'][1]['w']} x {template['layers_ordered'][1]['h']}")

    # 動画レイヤーの位置を変更（テスト用）
    original_x = template['layers_ordered'][1]['x']
    original_y = template['layers_ordered'][1]['y']
    test_x = 200
    test_y = 600

    template['layers_ordered'][1]['x'] = test_x
    template['layers_ordered'][1]['y'] = test_y

    # 保存
    with open(template_path, 'w', encoding='utf-8') as f:
        json.dump(template, f, ensure_ascii=False, indent=2)

    print("\n=== 変更後（保存） ===")
    print(f"動画レイヤー位置: ({test_x}, {test_y})")

    # もう一度読み込んで確認
    with open(template_path, 'r', encoding='utf-8') as f:
        loaded_template = json.load(f)

    loaded_x = loaded_template['layers_ordered'][1]['x']
    loaded_y = loaded_template['layers_ordered'][1]['y']

    print("\n=== 読み込み確認 ===")
    print(f"動画レイヤー位置: ({loaded_x}, {loaded_y})")

    # 検証
    if loaded_x == test_x and loaded_y == test_y:
        print("\n✓ テスト成功: 保存・読み込みサイクルが正常に動作しています")
    else:
        print(f"\n✗ テスト失敗: 期待値 ({test_x}, {test_y}), 実際の値 ({loaded_x}, {loaded_y})")

    # 元に戻す
    template['layers_ordered'][1]['x'] = original_x
    template['layers_ordered'][1]['y'] = original_y
    with open(template_path, 'w', encoding='utf-8') as f:
        json.dump(template, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 元の値に戻しました: ({original_x}, {original_y})")
    print(f"\nバックアップファイル: {backup_path}")

if __name__ == '__main__':
    test_save_load_cycle()
