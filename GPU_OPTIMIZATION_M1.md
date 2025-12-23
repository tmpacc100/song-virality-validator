# M1 GPU最適化完了

## 実装内容

### 1. video_compositor.py の最適化

#### M1 VideoToolbox エンコーディング設定
- **リアルタイムエンコーディング**: `-realtime 1` フラグを追加
- **プロファイル設定**: H.264 High Profile, Level 4.1（互換性重視）
- **3段階のプリセット対応**:
  - `fast`: ビットレート 8M, 最大 10M, バッファ 16M（最速・品質やや低）
  - `medium`: ビットレート 6M, 最大 8M, バッファ 12M（バランス型・デフォルト）
  - `slow`: ビットレート 5M, 最大 7M, バッファ 10M（高品質・低速）

#### CPU最適化（フォールバック用）
- **プリセット**: `veryfast`（fast から変更）
- **マルチスレッド**: `-threads 0`（全CPUコア使用）
- **CRF**: 23（品質と速度のバランス）

### 2. batch_video_generator_layers.py の更新
- GPU プリセット `fast` を指定（最速設定）
- M1 VideoToolbox を優先使用
- GPU失敗時は自動的にCPUエンコードにフォールバック

### 3. パフォーマンス改善

#### 最適化前
- 平均処理時間: 34.1秒/曲

#### 最適化後の期待値
- M1 GPU（fast プリセット）: 約20-25秒/曲（推定30%高速化）
- 381曲の総処理時間: 約2-2.5時間（従来比 約1時間短縮）

## 使用方法

### 基本的な使用
```python
# batch_video_with_color_rotation.py が自動的に fast プリセットを使用
python3 test_color_rotation.py
```

### プリセット変更（必要に応じて）
```python
# video_compositor.py を直接呼び出す場合
compositor.compose_video(
    base_video=video,
    background_image_path=bg,
    png_overlay_path=png,
    text_overlay_path=text,
    output_path=output,
    use_gpu=True,
    codec='h264_videotoolbox',
    gpu_preset='fast'  # 'fast', 'medium', 'slow' から選択
)
```

## 技術詳細

### M1 VideoToolbox の利点
1. **ハードウェアアクセラレーション**: Apple Silicon の専用エンコーダを使用
2. **省電力**: CPUエンコードより大幅に消費電力削減
3. **発熱低減**: GPU専用回路使用により発熱が少ない
4. **並列処理**: 複数の動画を同時処理可能

### エンコードパラメータ解説
- **bitrate (-b:v)**: 平均ビットレート（高いほど品質向上、ファイルサイズ増加）
- **maxrate**: 最大ビットレート上限
- **bufsize**: ビットレートバッファサイズ
- **realtime**: リアルタイムエンコード優先（速度重視）
- **profile:v high**: H.264 High Profile（高圧縮率）
- **level 4.1**: YouTubeなど主要プラットフォーム互換

## トラブルシューティング

### GPU エンコード失敗時
自動的にCPUエンコードにフォールバックします。エラーメッセージ例:
```
GPU合成失敗、CPU合成を試行: ...
```

### FFmpeg not found エラー
```bash
# Homebrew で FFmpeg をインストール
brew install ffmpeg
```

### VideoToolbox not available
M1/M2/M3 Mac でのみ使用可能です。Intel Mac では自動的にCPUエンコードを使用します。

## 次のステップ

1. **テスト実行**: 2曲でテストして速度を確認
   ```bash
   python3 test_color_rotation.py
   ```

2. **全曲生成**: 問題なければ max_videos=None に変更して全曲生成

3. **品質確認**: fast プリセットで品質が不十分な場合は medium に変更

## ファイル変更履歴
- `video_compositor.py`: M1 GPU最適化設定追加
- `batch_video_generator_layers.py`: gpu_preset='fast' 指定
- 従来の CPU 最適化も維持（veryfast, threads=0）
