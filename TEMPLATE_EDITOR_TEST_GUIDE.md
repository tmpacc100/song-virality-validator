# テンプレートエディタ 保存テストガイド

## 問題の症状
- テンプレートエディタで編集した内容が保存されない
- 次回起動時に編集内容が消えている

## テスト方法

### 1. 基本的な保存・読み込みテスト（ファイルレベル）

このテストはJSONファイル自体の読み書きが正常かを確認します。

```bash
python3 test_save_load_cycle.py
```

**期待される結果**: ✓ テスト成功: 保存・読み込みサイクルが正常に動作しています

✅ このテストが成功した場合 → JSONファイルの読み書きは問題なし
❌ このテストが失敗した場合 → ファイルシステムの権限やJSONパーサーの問題

---

### 2. GUIでの保存テスト（推奨）

このテストはGUIで実際に編集→保存→読み込みの流れを確認します。

```bash
python3 debug_template_editor.py
```

**手順**:
1. スクリプトを実行
2. Enterキーを押すとテンプレートエディタが起動
3. エディタで何か変更する（例: 動画レイヤーを少し移動）
4. 「保存」ボタンをクリック
5. 保存ダイアログで`template.json`を選択して保存
6. エディタを閉じる
7. スクリプトが変更を検出して表示

**期待される結果**: ✓ 変更が検出されました！保存が正常に動作しています

✅ このテストが成功した場合 → GUI保存は正常
❌ このテストが失敗した場合 → 以下を確認:
  - 保存ダイアログで正しいファイル名を選択したか
  - エディタのコンソールにエラーが出ていないか

---

### 3. 詳細な手動テスト

**ステップ1: 現在の値を確認**
```bash
python3 test_template_save.py
```

現在のテンプレートの値が表示されます:
```
動画レイヤー:
  位置: (182, 563)
  サイズ: 716 x 1259
```

**ステップ2: テンプレートエディタで編集**
```bash
python3 template_editor_layers.py
```

1. 動画レイヤー（青いボックス）を選択
2. ドラッグして位置を変更（例: 右に50px、下に50px移動）
3. 「保存」ボタンをクリック
4. 保存ダイアログで`template.json`を選択
5. 「保存完了」のメッセージを確認
6. エディタを閉じる

**ステップ3: 保存された値を確認**
```bash
python3 check_template_after_save.py
```

新しい値が表示されます:
```
動画レイヤー:
  位置: (232, 613)  ← 変更されているはず
  サイズ: 716 x 1259
```

**ステップ4: 再度エディタを開いて確認**
```bash
python3 template_editor_layers.py
```

動画レイヤーが新しい位置に配置されているか確認。

---

## よくある問題と解決策

### 問題1: 保存ダイアログで別のファイル名を指定してしまう

**症状**: 保存はできるが、次回起動時に反映されない

**原因**: `template.json`以外のファイル名で保存している

**解決策**:
- 保存時に必ず`template.json`という名前で保存する
- または保存したファイル名をメモして、次回「開く」ボタンから読み込む

### 問題2: 設定ファイルが古いパスを指している

**確認方法**:
```bash
cat .template_editor_config.json
```

**正しい内容**:
```json
{
  "last_template_path": "/Users/shii/Desktop/song virality validator/template.json"
}
```

**修正方法**: ファイルを削除して再作成
```bash
rm .template_editor_config.json
```

### 問題3: 保存時にエラーが出ている

**確認方法**:
- エディタ起動時のターミナル出力を確認
- 保存ボタンクリック後にエラーメッセージが表示されないか確認

**よくあるエラー**:
- `Permission denied` → ファイルの書き込み権限がない
- `JSON encode error` → テンプレートデータに問題がある

### 問題4: int/float変換エラー

**症状**: 小数点の座標値がintに変換できずエラー

**原因**: `widget_to_canvas_pos()`で`int()`を使用しているが、稀に問題が起きる可能性

**確認**: エディタのコンソール出力を見る

---

## デバッグ情報の収集

問題が解決しない場合、以下の情報を収集してください:

```bash
# 1. 現在のtemplate.jsonの内容
cat template.json

# 2. 設定ファイルの内容
cat .template_editor_config.json

# 3. テンプレートエディタを起動してコンソール出力を確認
python3 template_editor_layers.py

# 編集→保存して、コンソールに表示されるメッセージを確認:
# - "テンプレートを読み込みました: ..."
# - "保存完了" のメッセージボックス
```

---

## コードの確認ポイント

もし開発者として問題を調査する場合:

1. **保存フロー**: [template_editor_layers.py:1090](template_editor_layers.py#L1090)
   - `save_template()` → `export_template()` → `json.dump()`

2. **読み込みフロー**: [template_editor_layers.py:949](template_editor_layers.py#L949)
   - `load_template_if_exists()` → `json.load()` → `add_layer()`

3. **Layer.to_dict()**: [template_editor_layers.py:23](template_editor_layers.py#L23)
   - レイヤーの座標を`self.rect.x()`, `self.rect.y()`から取得

4. **ドラッグ処理**: [template_editor_layers.py:290](template_editor_layers.py#L290)
   - `self.selected_layer.layer.rect.translate(delta)` でrectを直接更新
