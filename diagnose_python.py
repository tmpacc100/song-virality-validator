#!/usr/bin/env python3
"""Python環境診断スクリプト"""
import sys
import os

print("=" * 60)
print("Python環境診断")
print("=" * 60)
print(f"実行中のPython: {sys.executable}")
print(f"バージョン: {sys.version}")
print(f"\nPATH順序:")
for i, path in enumerate(os.environ.get('PATH', '').split(':'), 1):
    if 'python' in path.lower():
        print(f"  {i}. {path}")

print(f"\nインストール済みモジュール:")
modules_to_check = ['requests', 'googleapiclient', 'PIL', 'PySide6']
for module_name in modules_to_check:
    try:
        if module_name == 'googleapiclient':
            __import__('googleapiclient.discovery')
        elif module_name == 'PIL':
            __import__('PIL')
        else:
            __import__(module_name)
        print(f"  ✓ {module_name}")
    except ImportError:
        print(f"  ✗ {module_name} (見つかりません)")

print("\n" + "=" * 60)
print("推奨事項:")
print("=" * 60)

missing_any = False
for module_name in modules_to_check:
    try:
        if module_name == 'googleapiclient':
            __import__('googleapiclient.discovery')
        elif module_name == 'PIL':
            __import__('PIL')
        else:
            __import__(module_name)
    except ImportError:
        missing_any = True
        break

if missing_any:
    print(f"このPythonに必要なパッケージをインストール:")
    print(f"  {sys.executable} -m pip install -r requirements.txt")
else:
    print("すべてのモジュールが利用可能です！")
    print(f"\nこのPythonを使用してmain.pyを実行:")
    print(f"  {sys.executable} main.py")
