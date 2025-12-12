#!/usr/bin/env python3
"""Test script to regenerate ranking_all.csv with ID column"""

import sys
import os

# main.pyから関数をインポート
sys.path.insert(0, os.path.dirname(__file__))

from main import export_all_rankings

if __name__ == '__main__':
    print("="*60)
    print("ranking_all.csvを再生成してIDカラムを追加します")
    print("="*60)

    # rankings.jsonが存在するか確認
    if not os.path.exists('rankings.json'):
        print("エラー: rankings.jsonが見つかりません")
        print("先にメインメニューから「1. 新動画fetch」を実行してください")
        sys.exit(1)

    # export_all_rankings()を実行
    export_all_rankings()

    print("\n完了！ranking_all.csvを確認してください。")
