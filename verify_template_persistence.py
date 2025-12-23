#!/usr/bin/env python3
"""
テンプレートの永続性を完全に検証
"""
import json
import os
import sys

def check_template_state():
    """テンプレートファイルと設定ファイルの状態を確認"""

    print("=" * 70)
    print("テンプレート永続性チェック")
    print("=" * 70)

    # 1. template.jsonの存在確認
    template_path = 'template.json'
    if not os.path.exists(template_path):
        print(f"❌ {template_path} が見つかりません")
        return False

    print(f"✓ {template_path} が存在します")

    # 2. template.jsonの読み込み
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = json.load(f)
        print(f"✓ {template_path} の読み込みに成功")
    except Exception as e:
        print(f"❌ {template_path} の読み込みに失敗: {e}")
        return False

    # 3. template.jsonの構造確認
    if 'layers_ordered' not in template:
        print("❌ template.jsonに'layers_ordered'が見つかりません")
        return False

    print(f"✓ layers_ordered: {len(template['layers_ordered'])} レイヤー")

    # 4. 各レイヤーの詳細表示
    print("\n" + "-" * 70)
    print("レイヤー詳細:")
    print("-" * 70)

    for i, layer in enumerate(template['layers_ordered'], 1):
        layer_type = layer.get('type', 'unknown')
        name = layer.get('name', 'unnamed')
        x = layer.get('x', 0)
        y = layer.get('y', 0)
        w = layer.get('w', 0)
        h = layer.get('h', 0)
        visible = layer.get('visible', True)
        path = layer.get('path', '')

        print(f"\n{i}. {layer_type.upper()} レイヤー: {name}")
        print(f"   位置: ({x}, {y})")
        print(f"   サイズ: {w} x {h}")
        print(f"   表示: {'ON' if visible else 'OFF'}")
        if path:
            path_display = path if len(path) < 50 else "..." + path[-47:]
            print(f"   ファイル: {path_display}")

    # 5. テキストエリアの確認
    if 'text_areas' in template and template['text_areas']:
        print("\n" + "-" * 70)
        print("テキストエリア:")
        print("-" * 70)

        for name, area in template['text_areas'].items():
            x = area.get('x', 0)
            y = area.get('y', 0)
            w = area.get('w', 0)
            h = area.get('h', 0)
            lines = area.get('lines', 1)
            font = area.get('font', 'デフォルト')

            print(f"\n{name}:")
            print(f"   位置: ({x}, {y})")
            print(f"   サイズ: {w} x {h}")
            print(f"   行数: {lines}")
            print(f"   フォント: {font}")

    # 6. 設定ファイルの確認
    config_path = '.template_editor_config.json'
    print("\n" + "-" * 70)
    print("設定ファイル:")
    print("-" * 70)

    if not os.path.exists(config_path):
        print(f"⚠ {config_path} が見つかりません（初回起動時は正常）")
    else:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            last_path = config.get('last_template_path', '')
            last_path_abs = os.path.abspath(template_path)

            print(f"✓ 設定ファイルが存在します")
            print(f"   保存されたパス: {last_path}")
            print(f"   現在のパス:     {last_path_abs}")

            if last_path == last_path_abs:
                print("   ✓ パスが一致しています")
            else:
                print("   ⚠ パスが一致していません")

        except Exception as e:
            print(f"❌ 設定ファイルの読み込みに失敗: {e}")

    # 7. ファイル権限の確認
    print("\n" + "-" * 70)
    print("ファイル権限:")
    print("-" * 70)

    import stat

    template_stat = os.stat(template_path)
    mode = template_stat.st_mode

    readable = bool(mode & stat.S_IRUSR)
    writable = bool(mode & stat.S_IWUSR)

    print(f"   読み取り: {'✓ 可能' if readable else '❌ 不可'}")
    print(f"   書き込み: {'✓ 可能' if writable else '❌ 不可'}")

    if not writable:
        print("\n   ❌ 警告: ファイルに書き込み権限がありません！")
        print("   以下のコマンドで権限を付与してください:")
        print(f"   chmod u+w {template_path}")

    # 8. 最終チェック
    print("\n" + "=" * 70)

    if readable and writable:
        print("✓ すべてのチェックに合格しました")
        print("\nテンプレートエディタで編集→保存→再起動の流れを試してください。")
        print("編集した内容が保持されない場合は、以下を確認してください:")
        print("  1. 保存時に必ず'template.json'という名前で保存")
        print("  2. 保存完了のメッセージボックスが表示されることを確認")
        print("  3. エディタのコンソール出力にエラーがないことを確認")
        return True
    else:
        print("❌ 問題が検出されました")
        return False

    print("=" * 70)

if __name__ == '__main__':
    success = check_template_state()
    sys.exit(0 if success else 1)
