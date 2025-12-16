#!/usr/bin/env python3
"""
ML/RLスケジュール最適化のテストスクリプト
"""

import sys
import os

# 仮想環境のPythonパスを確認
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print()

# 依存関係のインポートテスト
print("=" * 60)
print("依存関係チェック")
print("=" * 60)

try:
    import numpy as np
    print(f"✓ NumPy: {np.__version__}")
except ImportError as e:
    print(f"✗ NumPy: {e}")

try:
    import pandas as pd
    print(f"✓ Pandas: {pd.__version__}")
except ImportError as e:
    print(f"✗ Pandas: {e}")

try:
    import sklearn
    print(f"✓ scikit-learn: {sklearn.__version__}")
except ImportError as e:
    print(f"✗ scikit-learn: {e}")

try:
    import tensorflow as tf
    print(f"✓ TensorFlow: {tf.__version__}")
except ImportError as e:
    print(f"✗ TensorFlow: {e}")

try:
    import torch
    print(f"✓ PyTorch: {torch.__version__}")
except ImportError as e:
    print(f"✗ PyTorch: {e}")

try:
    import gymnasium
    print(f"✓ Gymnasium: {gymnasium.__version__}")
except ImportError as e:
    print(f"✗ Gymnasium: {e}")

print()

# ML/RLモジュールのインポートテスト
print("=" * 60)
print("ML/RLモジュールチェック")
print("=" * 60)

try:
    from feature_engineering import FeatureEngineer
    print("✓ feature_engineering.py: インポート成功")
except ImportError as e:
    print(f"✗ feature_engineering.py: {e}")

try:
    from ml_scheduler import ViewCountPredictor
    print("✓ ml_scheduler.py: インポート成功")
except ImportError as e:
    print(f"✗ ml_scheduler.py: {e}")

try:
    from rl_scheduler import SchedulingEnvironment, PPOAgent
    print("✓ rl_scheduler.py: インポート成功")
except ImportError as e:
    print(f"✗ rl_scheduler.py: {e}")

print()
print("=" * 60)
print("すべてのチェックが完了しました")
print("=" * 60)
