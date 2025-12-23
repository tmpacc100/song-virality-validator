#!/usr/bin/env python3
import json

print("\n=== 保存後のtemplate.json ===")
with open('template.json', 'r', encoding='utf-8') as f:
    after = json.load(f)

print("動画レイヤー:")
for layer in after.get('layers_ordered', []):
    if layer['type'] == 'video':
        print(f"  位置: ({layer['x']}, {layer['y']})")
        print(f"  サイズ: {layer['w']} x {layer['h']}")

print("\nテキストエリア:")
for name, area in after.get('text_areas', {}).items():
    print(f"  {name}: ({area['x']}, {area['y']}) {area['w']}x{area['h']}")
