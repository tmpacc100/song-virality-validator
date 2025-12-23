#!/usr/bin/env python3
"""
テンプレートエディタのデバッグツール
GUI起動前後でtemplate.jsonの値を比較
"""
import json
import os
import subprocess
import time

def read_template():
    """テンプレートを読み込んで主要な値を返す"""
    with open('template.json', 'r', encoding='utf-8') as f:
        template = json.load(f)

    video_layer = None
    for layer in template.get('layers_ordered', []):
        if layer['type'] == 'video':
            video_layer = layer
            break

    text_area = template.get('text_areas', {}).get('text_1', {})

    return {
        'video_x': video_layer['x'] if video_layer else None,
        'video_y': video_layer['y'] if video_layer else None,
        'video_w': video_layer['w'] if video_layer else None,
        'video_h': video_layer['h'] if video_layer else None,
        'text_x': text_area.get('x'),
        'text_y': text_area.get('y'),
        'text_w': text_area.get('w'),
        'text_h': text_area.get('h'),
    }

def print_values(label, values):
    """値を見やすく表示"""
    print(f"\n{label}")
    print("=" * 60)
    print(f"動画レイヤー: 位置({values['video_x']}, {values['video_y']}) サイズ{values['video_w']}x{values['video_h']}")
    print(f"テキストエリア: 位置({values['text_x']}, {values['text_y']}) サイズ{values['text_w']}x{values['text_h']}")

def compare_values(before, after):
    """変更を検出"""
    print("\n変更の検出:")
    print("=" * 60)

    changed = False

    for key in before:
        if before[key] != after[key]:
            print(f"  {key}: {before[key]} → {after[key]}")
            changed = True

    if not changed:
        print("  変更なし")

    return changed

def main():
    """メイン関数"""

    print("=" * 60)
    print("テンプレートエディタ デバッグツール")
    print("=" * 60)

    # 起動前の値を記録
    before = read_template()
    print_values("起動前の値", before)

    print("\n" + "=" * 60)
    print("これからテンプレートエディタを起動します")
    print("エディタで何か編集して保存してください")
    print("保存したらエディタを閉じてください")
    print("=" * 60)

    input("\nEnterキーを押すとエディタが起動します...")

    # テンプレートエディタを起動（ブロッキング）
    subprocess.run(['python3', 'template_editor_layers.py'])

    # 終了後の値を確認
    time.sleep(0.5)  # ファイルシステムの同期を待つ
    after = read_template()
    print_values("エディタ終了後の値", after)

    # 比較
    changed = compare_values(before, after)

    print("\n" + "=" * 60)
    if changed:
        print("✓ 変更が検出されました！保存が正常に動作しています")
    else:
        print("⚠ 変更が検出されませんでした")
        print("\nデバッグのヒント:")
        print("1. エディタで何か変更しましたか？")
        print("2. 保存ボタンを押しましたか？")
        print("3. 保存ダイアログで'template.json'を選択しましたか？")
        print("4. エディタのコンソール出力にエラーがありませんでしたか？")
    print("=" * 60)

if __name__ == '__main__':
    main()
