# バッチ動画生成システム

YouTube Shorts用の動画を大量に自動生成するシステムです。

## 🎯 システム構成

```
① テンプレートエディタ (template_editor.py)
   ↓ template.json 出力

② CSVデータ (sample_songs.csv)
   ↓ アーティスト名・曲名

③ テキスト画像生成 (text_generator.py)
   ↓ artist.png, song.png, full_title.png

④ 動画合成 (video_compositor.py)
   ↓ FFmpegでオーバーレイ合成

⑤ バッチ生成 (batch_video_generator.py)
   ↓ 複数動画を一括生成
```

---

## 📦 必要なもの

### Pythonパッケージ
```bash
pip3 install PySide6 Pillow
```

### FFmpeg（動画合成用）
```bash
# macOS
brew install ffmpeg

# GPU対応（videotoolbox）は自動検出
```

---

## 🚀 使い方

### ステップ1: テンプレート作成（初回のみ）

```bash
python3 template_editor.py
```

**操作:**
1. 背景画像を読み込む（オプション）
2. 赤い枠をドラッグして位置調整
3. 角をドラッグしてサイズ調整
4. 各テキストエリアの最大行数を設定
   - artist: 1行
   - song: 2行
   - full_title: 3行
5. 「template.json を保存」をクリック

**出力:**
- `template.json` - レイアウト設定ファイル

---

### ステップ2: CSVデータ準備

**フォーマット:**
```csv
artist_name,music_name
Ado,うっせぇわ
King Gnu,白日
YOASOBI,アイドル
```

**自動生成されるテキスト:**
- artist: `Ado`
- song: `うっせぇわ`
- full_title: `Adoの「うっせぇわ」弾いてみた`

---

### ステップ3: バッチ動画生成

```bash
python3 batch_video_generator.py sample_songs.csv base.mp4
```

**処理内容:**
1. CSVから曲情報を読み込み
2. 各曲ごとに
   - テキスト画像を生成（自動フォントサイズ調整）
   - ベース動画とテキストを合成
   - GPU加速エンコード（videotoolbox）
3. `output_videos/` に保存

**オプション:**
- マルチプロセス処理で高速化可能
- GPU利用不可の場合は自動的にCPUフォールバック

---

## 📁 ディレクトリ構成

```
song virality validator/
├── template_editor.py          # ① UIエディタ
├── text_generator.py           # ③ テキスト画像生成
├── video_compositor.py         # ④ 動画合成
├── batch_video_generator.py    # ⑤ バッチ処理
├── template.json               # レイアウト設定
├── sample_songs.csv            # サンプルCSV
├── base.mp4                    # ベース動画
├── fonts/                      # フォントフォルダ（オプション）
│   ├── NotoSans-Bold.otf
│   └── HiraginoSans-W6.otf
├── assets/                     # 背景画像（オプション）
│   └── bg.png
└── output_videos/              # 出力先
    ├── Ado_うっせぇわ.mp4
    ├── King Gnu_白日.mp4
    └── ...
```

---

## 🎨 template.json の例

```json
{
  "canvas": {"w": 1080, "h": 1920},
  "text_areas": {
    "artist": {"x": 120, "y": 200, "w": 840, "h": 160, "lines": 1},
    "song": {"x": 120, "y": 380, "w": 840, "h": 180, "lines": 2},
    "full_title": {"x": 120, "y": 600, "w": 840, "h": 300, "lines": 3}
  },
  "fonts": {
    "primary": "fonts/NotoSans-Bold.otf",
    "secondary": "fonts/HiraginoSans-W6.otf"
  },
  "images": [
    {"id": "background", "path": "assets/bg.png", "x": 0, "y": 0}
  ]
}
```

---

## 🔧 個別コマンド

### テキスト画像のみ生成
```bash
python3 text_generator.py "Ado" "うっせぇわ"
# → output/artist.png, song.png, full_title.png
```

### 動画合成のみ
```bash
python3 video_compositor.py base.mp4 output.mp4
# → テキスト画像を使って合成
```

---

## ⚡ パフォーマンス

### GPU加速（macOS）
- コーデック: `h264_videotoolbox`
- 約10倍高速化
- 自動検出・フォールバック対応

### マルチプロセス
- CPU数に応じて並列処理
- 100曲でも数分で完了

---

## 🎬 ワークフロー例

```bash
# 1. テンプレート作成（初回のみ）
python3 template_editor.py

# 2. ランキングCSVを使用して動画生成
python3 batch_video_generator.py ranking_overall.csv base.mp4

# 3. 出力確認
ls output_videos/
```

---

## 💡 カスタマイズ

### フォントの変更
`template.json` の `fonts` セクションを編集

### テキストの縁取り調整
`text_generator.py` の `outline_width` を変更

### エンコード品質
`video_compositor.py` の `-b:v` や `-crf` を調整

---

## 🐛 トラブルシューティング

### フォントが見つからない
→ システムフォントを使用（自動フォールバック）

### GPU合成失敗
→ 自動的にCPU合成に切り替わります

### FFmpegが見つからない
```bash
brew install ffmpeg
```

---

## 📊 統合ワークフロー

YouTubeランキング分析 → CSV出力 → 動画生成

```bash
# 1. ランキング取得
python3 main.py
# → メニューから「1. 新動画fetch」「3. CSV出力」

# 2. 動画生成
python3 batch_video_generator.py ranking_overall.csv base.mp4

# 3. タスク管理
python3 main.py
# → メニューから「2. タスク管理」
```

---

## 🎉 完成！

これで100本でも1000本でも自動生成できます！
