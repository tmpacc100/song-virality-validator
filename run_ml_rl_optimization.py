#!/usr/bin/env python3
"""
ML/RLスケジュール最適化を直接実行するスクリプト
"""

import sys
import os

# main.pyから必要な関数をインポート
from main import ml_rl_schedule_optimization

if __name__ == '__main__':
    print("=" * 60)
    print("ML/RLスケジュール最適化を開始します")
    print("=" * 60)
    print()

    try:
        ml_rl_schedule_optimization()
        print()
        print("=" * 60)
        print("✅ ML/RLスケジュール最適化が完了しました")
        print("=" * 60)
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ エラーが発生しました: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)
