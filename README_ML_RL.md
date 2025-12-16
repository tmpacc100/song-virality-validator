# ML/RLスケジュール最適化システム

## 概要

Deep Learning（TensorFlow）とReinforcement Learning（PyTorch PPO）を使用して、YouTube動画の最適な投稿日時を予測するシステムです。

## セットアップ完了

✅ Python 3.12.12がインストールされました
✅ 仮想環境 `venv312` が作成されました
✅ すべてのML/DL依存関係がインストールされました

## 使用方法

### 1. 仮想環境の有効化

```bash
cd "/Users/shii/Desktop/song virality validator"
source venv312/bin/activate
```

### 2. メインプログラムの実行

```bash
python main.py
```

メニューから **10. 🤖 ML/RLスケジュール最適化** を選択してください。

### 3. スタンドアロン実行（推奨）

```bash
python run_ml_rl_optimization.py
```

このスクリプトは直接ML/RL最適化を実行します。

## システム構成

### 実装ファイル

1. **feature_engineering.py** (380行)
   - 時間的特徴抽出（hour, day_of_week, season など）
   - コンテンツ特徴抽出（tags, difficulty, artist）
   - エンゲージメント特徴（like_rate, engagement_rate）
   - 交互作用特徴（anime × evening など）

2. **ml_scheduler.py** (400行)
   - TensorFlowニューラルネットワーク
   - アーキテクチャ: Input(45) → Dense(128) → Dense(64) → Dense(32) → Output(views, confidence)
   - データ拡張: 372サンプル → 1,860サンプル (5倍増)
   - 正則化: Dropout, BatchNormalization, L2, Early Stopping

3. **rl_scheduler.py** (450行)
   - PPO (Proximal Policy Optimization) アルゴリズム
   - Actor-Critic Network
   - release_date制約の自動ハンドリング
   - 報酬関数: predicted_views - penalties

## 最適化結果（直近実行）

- **処理曲数**: 373曲
- **総予測視聴回数**: 13,457,661,991 views
- **平均信頼度**: 75.0%
- **ML訓練**: 100エポック、Validation MAE: 0.2632
- **RL訓練**: 500エピソード、Best Reward: 132,432.68

### 推奨投稿スケジュール（トップ10）

1. 2025-12-22 00:00 - 「Lemon」米津玄師 → 761,988,865 views
2. 2025-12-17 00:00 - 「廻廻奇譚」Eve → 354,077,631 views
3. 2025-12-18 00:00 - 「Bling-Bang-Bang-Born」Creepy Nuts → 347,898,027 views
4. 2025-12-17 00:00 - 「うっせぇわ」Ado → 317,883,288 views
5. 2025-12-16 00:00 - 「アイネクライネ」米津玄師 → 293,574,404 views

## 出力データ

### rankings.json

各曲に以下のML予測結果が追加されます：

```json
{
  "song_name": "Lemon",
  "artist_name": "米津玄師",
  "ml_predictions": {
    "optimal_posting_datetime": "2025-12-22 00:00:00",
    "predicted_view_count": 761988865,
    "confidence_score": 0.75
  }
}
```

### CSV出力

メインプログラムのオプション3でCSVを再出力すると、以下の列が追加されます：
- 最適投稿日時
- 予測視聴数
- 信頼度スコア

## トラブルシューティング

### ImportError: No module named 'tensorflow'

仮想環境が有効化されているか確認してください：
```bash
which python3
# Should show: /Users/shii/Desktop/song virality validator/venv312/bin/python3
```

### Python 3.14を使いたい場合

Python 3.14ではTensorFlow/PyTorchがまだサポートされていません。Python 3.12の使用を推奨します。

## 技術詳細

### モデルアーキテクチャ

**ML View Predictor:**
- Input: 45次元特徴量
- Hidden: [128 → 64 → 32]
- Output: views (regression) + confidence (classification)
- Loss: MSLE (views) + BCE (confidence)

**RL PPO Agent:**
- State: 10次元 (曲特徴 + スケジュール状態)
- Action: [date_offset(0-90), hour(0-23)]
- Reward: predicted_views - interval_penalty - fatigue_penalty - constraint_penalty
- Network: Shared(256 → 128) → Actor/Critic heads

### release_date制約ロジック

```python
if release_date >= today:
    # 日付固定、時間のみ最適化
    posting_datetime = release_date.replace(hour=optimized_hour)
else:
    # 完全自由
    posting_datetime = today + timedelta(days=offset, hours=hour)
```

## パフォーマンス

- ML訓練時間: 約2分（100エポック、1,865サンプル）
- RL訓練時間: 約1分（500エピソード、373曲）
- 総実行時間: 約3-4分

## 次のステップ

1. メインプログラムでオプション3を実行してCSVを出力
2. CSV内の「最適投稿日時」「予測視聴数」を確認
3. 実際の投稿結果と比較して精度を評価
4. 必要に応じてハイパーパラメータを調整
