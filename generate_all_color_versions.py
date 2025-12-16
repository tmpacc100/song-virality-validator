#!/usr/bin/env python3
"""
1つの曲に対して7色すべての背景バージョンを生成
"""

import json
import os
import sys
from batch_video_generator_layers import LayerBasedBatchVideoGenerator

BACKGROUND_DIR = '/Users/shii/Desktop/song virality validator/MEDIA/background_different_color'
TEMPLATE_PATH = 'template.json'

COLORS = {
    'red': '赤',
    'pink': 'ピンク',
    'orange': 'オレンジ',
    'yellow': '黄色',
    'blue': '青',
    'turquoise': 'ターコイズ',
    'black': '黒'
}

def update_template_background(color_name):
    """テンプレートの背景を更新"""
    background_path = os.path.join(BACKGROUND_DIR, f'{color_name}.png')

    # テンプレート読み込み
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template = json.load(f)

    # 背景レイヤーを更新
    if 'layers_ordered' in template:
        for layer in template['layers_ordered']:
            if layer['type'] == 'background':
                layer['path'] = background_path
                break

    # 保存
    with open(TEMPLATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(template, f, ensure_ascii=False, indent=2)

    return background_path

def backup_template():
    """テンプレートをバックアップ"""
    backup_path = f"{TEMPLATE_PATH}.backup_original"
    if not os.path.exists(backup_path):
        with open(TEMPLATE_PATH, 'r') as src:
            with open(backup_path, 'w') as dst:
                dst.write(src.read())
        print(f"✓ テンプレートバックアップ: {backup_path}")

def restore_template():
    """テンプレートを復元"""
    backup_path = f"{TEMPLATE_PATH}.backup_original"
    if os.path.exists(backup_path):
        with open(backup_path, 'r') as src:
            with open(TEMPLATE_PATH, 'w') as dst:
                dst.write(src.read())
        print(f"✓ テンプレートを復元しました")

def generate_all_color_versions(artist, song, output_dir='output', base_video='base.mp4', song_id=None):
    """7色すべてのバージョンを生成

    Args:
        artist: アーティスト名
        song: 曲名
        output_dir: 出力ディレクトリ
        base_video: ベース動画
        song_id: 曲ID（オプション）
    """
    print(f"\n{'='*60}")
    print(f"7色バージョン生成: {artist} - {song}")
    print(f"{'='*60}\n")

    # テンプレートをバックアップ
    backup_template()

    generated_videos = []

    # 各色ごとに生成
    for color_name, color_jp in COLORS.items():
        print(f"\n{'='*60}")
        print(f"[{len(generated_videos) + 1}/7] {color_jp}バージョンを生成中...")
        print(f"{'='*60}")

        # テンプレートの背景を更新
        background_path = update_template_background(color_name)
        print(f"背景: {os.path.basename(background_path)}")

        # 動画名に色を追加
        if song_id:
            video_name = f"{artist}_{song}_{song_id}_{color_name}.mp4"
        else:
            video_name = f"{artist}_{song}_{color_name}.mp4"

        # 動画を生成
        try:
            generator = LayerBasedBatchVideoGenerator(TEMPLATE_PATH, base_video)

            # song_idがある場合はrowとして渡す
            row = {'id': song_id} if song_id else None

            video_path = generator.generate_single_video(
                artist, song, output_dir,
                video_name=video_name,
                include_artist=True,
                row=row
            )

            if video_path:
                generated_videos.append((color_jp, video_path))
                print(f"✓ {color_jp}バージョン完成: {video_path}")
            else:
                print(f"✗ {color_jp}バージョン失敗")

        except Exception as e:
            print(f"✗ エラー ({color_jp}): {e}")
            import traceback
            traceback.print_exc()

    # テンプレートを復元
    restore_template()

    # 結果サマリー
    print(f"\n{'='*60}")
    print(f"生成完了")
    print(f"{'='*60}")
    print(f"成功: {len(generated_videos)}/7バージョン\n")

    for color_jp, video_path in generated_videos:
        print(f"  ✓ {color_jp}: {os.path.basename(video_path)}")

    return generated_videos

def main():
    """メイン実行"""
    if len(sys.argv) < 3:
        print("使用方法:")
        print("  python generate_all_color_versions.py <アーティスト名> <曲名> [曲ID] [出力ディレクトリ]")
        print()
        print("例:")
        print("  python generate_all_color_versions.py 米津玄師 Lemon")
        print("  python generate_all_color_versions.py 米津玄師 Lemon 12345 output")
        sys.exit(1)

    artist = sys.argv[1]
    song = sys.argv[2]
    song_id = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('output') else None
    output_dir = sys.argv[4] if len(sys.argv) > 4 else (sys.argv[3] if len(sys.argv) > 3 and sys.argv[3].startswith('output') else 'output')

    # 動画を生成
    videos = generate_all_color_versions(artist, song, output_dir, song_id=song_id)

    print(f"\n✅ 完了: {len(videos)}個の動画を生成しました")

if __name__ == '__main__':
    main()
