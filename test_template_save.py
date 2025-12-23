#!/usr/bin/env python3
"""
テンプレートエディタの保存機能をテスト
"""
import json
import os
import sys

# テンプレートを読み込む
print("=== 保存前のtemplate.json ===")
with open('template.json', 'r', encoding='utf-8') as f:
    before = json.load(f)

print("動画レイヤー:")
for layer in before.get('layers_ordered', []):
    if layer['type'] == 'video':
        print(f"  位置: ({layer['x']}, {layer['y']})")
        print(f"  サイズ: {layer['w']} x {layer['h']}")

print("\nテキストエリア:")
for name, area in before.get('text_areas', {}).items():
    print(f"  {name}: ({area['x']}, {area['y']}) {area['w']}x{area['h']}")

print("\n" + "="*60)
print("テンプレートエディタでレイヤーを編集して保存してください")
print("保存したら、このスクリプトを再度実行してください")
print("="*60)

# 保存後の確認用スクリプトを作成
check_script = """#!/usr/bin/env python3
import json

print("\\n=== 保存後のtemplate.json ===")
with open('template.json', 'r', encoding='utf-8') as f:
    after = json.load(f)

print("動画レイヤー:")
for layer in after.get('layers_ordered', []):
    if layer['type'] == 'video':
        print(f"  位置: ({layer['x']}, {layer['y']})")
        print(f"  サイズ: {layer['w']} x {layer['h']}")

print("\\nテキストエリア:")
for name, area in after.get('text_areas', {}).items():
    print(f"  {name}: ({area['x']}, {area['y']}) {area['w']}x{area['h']}")
"""

with open('check_template_after_save.py', 'w', encoding='utf-8') as f:
    f.write(check_script)

print("\n保存後、以下を実行してください:")
print("  python3 check_template_after_save.py")
