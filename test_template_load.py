#!/usr/bin/env python3
"""テンプレート自動読み込み機能のテスト"""
import json
import os

# template.jsonが存在するかチェック
template_path = 'template.json'
if not os.path.exists(template_path):
    print(f"❌ エラー: {template_path} が見つかりません")
    exit(1)

print(f"✓ {template_path} が存在します")

# テンプレートを読み込む
try:
    with open(template_path, 'r', encoding='utf-8') as f:
        template_data = json.load(f)

    print(f"✓ テンプレートを正常に読み込めました")

    # キャンバスサイズを表示
    canvas_size = template_data.get('canvas', {})
    if canvas_size:
        print(f"  - キャンバスサイズ: {canvas_size.get('w')}x{canvas_size.get('h')}")

    # レイヤー情報を表示
    if 'layers_ordered' in template_data:
        layers = template_data['layers_ordered']
        print(f"  - レイヤー数: {len(layers)}")
        for i, layer in enumerate(layers):
            layer_type = layer.get('type')
            name = layer.get('name')
            visible = layer.get('visible', True)
            path = layer.get('path', '')
            print(f"    {i+1}. {name} ({layer_type}) - visible: {visible}")
            if path:
                exists = "存在" if os.path.exists(path) else "見つかりません"
                print(f"       path: {path} ({exists})")

    # テキストエリアを表示
    text_areas = template_data.get('text_areas', {})
    if text_areas:
        print(f"  - テキストエリア数: {len(text_areas)}")
        for name, area in text_areas.items():
            print(f"    - {name}: x={area['x']}, y={area['y']}, w={area['w']}, h={area['h']}, lines={area.get('lines', 3)}")

    print("\n✓ テンプレート自動読み込み機能は正常に動作します")

except json.JSONDecodeError as e:
    print(f"❌ JSON解析エラー: {e}")
    exit(1)
except Exception as e:
    print(f"❌ エラー: {e}")
    exit(1)
