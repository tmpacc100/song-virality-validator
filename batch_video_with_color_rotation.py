#!/usr/bin/env python3
"""
背景色を回転させながらバッチ動画生成
各曲に異なる背景色の画像を割り当てて動画を生成
"""

import csv
import json
import os
import shutil
import time
from batch_video_generator_layers import LayerBasedBatchVideoGenerator

class ColorRotationBatchGenerator:
    """背景色ローテーション機能付きバッチ動画生成"""

    def __init__(self, template_path='template.json', base_video='MEDIA/base.mp4'):
        self.template_path = template_path
        self.base_video = base_video

        # 背景画像フォルダ
        self.background_dir = 'MEDIA/background_different_color'

        # 利用可能な背景色リスト
        self.background_colors = [
            'blue_original', 'green_original', 'lightblue_original', 'lightgreen_original',
            'orange_original', 'pink_original', 'purple_original', 'red_original',
            'turcoise_original', 'yellow_original'
        ]

        # バックアップパス
        self.original_template_path = f"{template_path}.backup"

        # 元のテンプレートをバックアップ（まだなければ）
        if not os.path.exists(self.original_template_path):
            shutil.copy(template_path, self.original_template_path)
            print(f"✓ テンプレートバックアップ作成: {self.original_template_path}")

    def _set_background_color(self, color_name):
        """テンプレートの背景色を変更"""
        # バックアップから復元
        shutil.copy(self.original_template_path, self.template_path)

        # テンプレートを読み込む
        with open(self.template_path, 'r', encoding='utf-8') as f:
            template = json.load(f)

        # IMAGEレイヤーのパスを更新
        background_path = os.path.abspath(
            os.path.join(self.background_dir, f"{color_name}.png")
        )

        for layer in template.get('layers_ordered', []):
            if layer['type'] == 'image' and layer['name'] == 'image_1':
                layer['path'] = background_path
                print(f"  背景色設定: {color_name} -> {background_path}")
                break

        # テンプレートを保存
        with open(self.template_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False, indent=2)

    def _restore_original_template(self):
        """元のテンプレートを復元"""
        if os.path.exists(self.original_template_path):
            shutil.copy(self.original_template_path, self.template_path)
            print("✓ 元のテンプレートを復元しました")

    def generate_from_csv_with_color_rotation(self, csv_path, output_dir='output',
                                                include_artist=True, max_videos=None):
        """CSVから背景色をローテーションしながら動画を生成

        Args:
            csv_path: CSVファイルのパス
            output_dir: 出力ディレクトリ
            include_artist: アーティスト名を含めるか
            max_videos: 最大生成動画数（Noneの場合は全曲）

        Returns:
            生成された動画のリスト
        """
        os.makedirs(output_dir, exist_ok=True)

        # CSVを読み込み
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if max_videos:
            rows = rows[:max_videos]

        print(f"\n{'='*70}")
        print(f"背景色ローテーションバッチ動画生成")
        print(f"{'='*70}")
        print(f"対象曲数: {len(rows)}")
        print(f"背景色数: {len(self.background_colors)}")
        print(f"出力先: {output_dir}")
        print(f"{'='*70}\n")

        generated_videos = []
        color_index = 0
        start_time = time.time()
        success_count = 0
        error_count = 0

        for i, row in enumerate(rows, 1):
            # 曲情報を取得（複数のCSV形式に対応）
            song_id = row.get('id', row.get('Video ID', '')).strip()
            artist = row.get('アーティスト名', row.get('artist_name', '')).strip()
            song = row.get('曲名', row.get('song_name', '')).strip()

            # 曲番号（jasrac_codeまたはCSVの行番号）
            song_number = row.get('jasrac_code', '').strip() or str(i)

            if not song:
                print(f"[{i}/{len(rows)}] スキップ: 曲名なし")
                continue

            # 背景色を選択（ローテーション）
            color = self.background_colors[color_index % len(self.background_colors)]
            color_index += 1

            print(f"\n{'='*70}")
            print(f"[{i}/{len(rows)}] 処理中: {artist} - {song}")
            print(f"背景色: {color}")
            print(f"{'='*70}")

            # 背景色を設定
            self._set_background_color(color)

            # 動画を生成
            try:
                # ジェネレーターを初期化（最新のテンプレートを読み込む）
                generator = LayerBasedBatchVideoGenerator(
                    template_path=self.template_path,
                    base_video=self.base_video
                )

                # 動画ファイル名
                # ファイル名に使えない文字を置換
                safe_artist = artist.replace('/', '_').replace('\\', '_').replace(':', '_').replace('#', '').replace('|', '')
                safe_song = song.replace('/', '_').replace('\\', '_').replace(':', '_').replace('#', '').replace('|', '')

                # フォーマット: 【曲名 - アーティスト名】たいこで叩いてみた｜たいこでヒットソング#shorts #曲名 #アーティスト名#たいこでヒットソング #音ゲー_曲番号.mp4
                video_name = f"【{safe_song} - {safe_artist}】たいこで叩いてみた｜たいこでヒットソング#shorts #{safe_song} #{safe_artist}#たいこでヒットソング #音ゲー_{song_number}.mp4"

                # 曲IDに対応する動画があるか確認
                base_video_override = None
                if song_id:
                    for ext in ['.mp4', '.MP4']:
                        id_video_path = os.path.join(output_dir, f"{song_id}{ext}")
                        if os.path.exists(id_video_path):
                            base_video_override = id_video_path
                            print(f"  ✓ 曲ID動画を使用: {id_video_path}")
                            break

                # 動画生成
                video_path = generator.generate_single_video(
                    artist=artist,
                    song=song,
                    output_dir=output_dir,
                    video_name=video_name,
                    base_video_override=base_video_override,
                    include_artist=include_artist,
                    row=row
                )

                if video_path:
                    generated_videos.append({
                        'video_path': video_path,
                        'artist': artist,
                        'song': song,
                        'color': color,
                        'song_id': song_id
                    })
                    success_count += 1
                    print(f"  ✓ 生成完了: {video_path}")
                else:
                    error_count += 1
                    print(f"  ✗ 生成失敗")

            except Exception as e:
                error_count += 1
                print(f"  ✗ エラー: {e}")
                import traceback
                traceback.print_exc()

        # 元のテンプレートを復元
        self._restore_original_template()

        # 処理時間を計算
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / len(rows) if len(rows) > 0 else 0

        # 結果サマリー
        print(f"\n{'='*70}")
        print(f"生成完了")
        print(f"{'='*70}")
        print(f"成功: {success_count}/{len(rows)}")
        print(f"失敗: {error_count}/{len(rows)}")
        print(f"総処理時間: {total_time:.1f}秒 ({total_time/60:.1f}分)")
        print(f"平均処理時間: {avg_time:.1f}秒/曲")

        if generated_videos:
            print(f"\n生成された動画:")
            for i, video in enumerate(generated_videos, 1):
                print(f"  {i}. {video['artist']} - {video['song']} ({video['color']})")
                print(f"     {video['video_path']}")

        return generated_videos


def main():
    """メイン関数"""
    import sys

    print("="*70)
    print("背景色ローテーションバッチ動画生成")
    print("="*70)

    # CSVファイルパス
    csv_path = 'songs.csv'
    if not os.path.exists(csv_path):
        print(f"\nエラー: {csv_path} が見つかりません")
        return

    # 生成する動画数を指定
    print(f"\n何曲分の動画を生成しますか？")
    print(f"  - 数字を入力: 指定した曲数のみ生成")
    print(f"  - Enter: 全曲生成")

    user_input = input("\n生成する曲数: ").strip()

    max_videos = None
    if user_input:
        try:
            max_videos = int(user_input)
            print(f"\n{max_videos}曲分の動画を生成します")
        except ValueError:
            print("\n無効な入力です。全曲生成します")
    else:
        print("\n全曲の動画を生成します")

    # 確認
    confirm = input("\n処理を開始しますか？ (y/n): ").strip().lower()
    if confirm != 'y':
        print("キャンセルしました")
        return

    # ジェネレーターを初期化
    generator = ColorRotationBatchGenerator(
        template_path='template.json',
        base_video='MEDIA/base.mp4'
    )

    # 動画生成
    generator.generate_from_csv_with_color_rotation(
        csv_path=csv_path,
        output_dir='output',
        include_artist=True,
        max_videos=max_videos
    )


if __name__ == '__main__':
    main()
