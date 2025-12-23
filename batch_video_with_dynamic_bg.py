#!/usr/bin/env python3
"""
動的背景選択付きバッチ動画生成
各曲のYouTubeサムネイル色とカテゴリーに基づいて
自動的に最適な背景色を選択して動画を生成
"""

import csv
import os
import json
from batch_video_generator_layers import LayerBasedBatchVideoGenerator
from dynamic_background_selector import DynamicBackgroundSelector


class DynamicBackgroundBatchGenerator:
    """動的背景選択機能付きバッチ動画生成"""

    def __init__(self, template_path='template.json', base_video='base.mp4'):
        self.template_path = template_path
        self.base_video = base_video
        self.background_selector = DynamicBackgroundSelector(template_path)

        # 元のテンプレートをバックアップ
        self.original_template_path = f"{template_path}.backup"
        if not os.path.exists(self.original_template_path):
            with open(template_path, 'r') as src:
                with open(self.original_template_path, 'w') as dst:
                    dst.write(src.read())
            print(f"✓ テンプレートバックアップ作成: {self.original_template_path}")

    def _restore_original_template(self):
        """元のテンプレートを復元"""
        if os.path.exists(self.original_template_path):
            with open(self.original_template_path, 'r') as src:
                with open(self.template_path, 'w') as dst:
                    dst.write(src.read())

    def generate_from_csv_with_dynamic_bg(self, csv_path, output_dir='output',
                                           use_video_analysis=True,
                                           use_category=True,
                                           include_artist=True,
                                           id_match_only=False):
        """CSVから動画を一括生成（動的背景選択付き）

        Args:
            csv_path: CSVファイルのパス
            output_dir: 出力ディレクトリ
            use_video_analysis: YouTubeサムネイル分析を使用するか
            use_category: カテゴリー（タグ）を考慮するか
            include_artist: アーティスト名を含めるか
            id_match_only: Trueの場合、曲IDにマッチする動画がある曲のみ処理

        Returns:
            生成された動画のリスト
        """
        os.makedirs(output_dir, exist_ok=True)

        # CSVを読み込み
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # 曲IDマッチングフィルタリング
        video_source_dir = 'output'
        skipped_count = 0
        filtered_rows = []

        if id_match_only:
            for row in rows:
                song_id = row.get('id', '').strip()
                if song_id:
                    # 曲IDに対応する動画ファイルが存在するかチェック
                    id_video_found = False
                    for ext in ['.mp4', '.MP4']:
                        song_id_video_path = os.path.join(video_source_dir, f"{song_id}{ext}")
                        if os.path.exists(song_id_video_path):
                            id_video_found = True
                            break

                    if id_video_found:
                        filtered_rows.append(row)
                    else:
                        skipped_count += 1
                else:
                    # IDがない場合はスキップ
                    skipped_count += 1

            rows = filtered_rows
            if skipped_count > 0:
                print(f"\n⚠ 曲IDマッチングでスキップされた曲: {skipped_count}曲")

        total = len(rows)
        generated_videos = []

        print(f"\n{'='*60}")
        print(f"動的背景選択付きバッチ動画生成")
        print(f"{'='*60}")
        print(f"総曲数: {total}曲")
        print(f"サムネイル分析: {'有効' if use_video_analysis else '無効'}")
        print(f"カテゴリー考慮: {'有効' if use_category else '無効'}")
        print(f"曲IDマッチング: {'有効' if id_match_only else '無効'}")
        print(f"{'='*60}\n")

        for idx, row in enumerate(rows):
            # 【修正】各曲の処理前に元のテンプレートを復元
            self._restore_original_template()

            artist = row.get('アーティスト名', row.get('artist_name', '')).strip()
            song = row.get('曲名', row.get('song_name', '')).strip()
            video_id = row.get('video_id', '').strip()
            song_id = row.get('id', '').strip()

            if not artist or not song:
                print(f"[{idx + 1}/{total}] スキップ: アーティスト名または曲名が空")
                continue

            print(f"\n{'='*60}")
            print(f"[{idx + 1}/{total}] {artist} - {song}")
            if song_id:
                print(f"曲ID: {song_id}")
            if video_id:
                print(f"動画ID: {video_id}")
            print(f"{'='*60}")

            # タグの取得
            tags = []
            tags_str = row.get('tags', '')
            if tags_str:
                try:
                    tags = eval(tags_str) if tags_str else []
                except:
                    tags = []

            # 背景を動的に選択してテンプレートを更新
            try:
                # ハイブリッド方式: サムネイル分析とカテゴリーの両方を使用
                if use_video_analysis and use_category:
                    if video_id and tags:
                        print("背景選択方式: ハイブリッド（サムネイル分析 + カテゴリー）")
                        self.background_selector.update_background_by_hybrid(
                            video_id, tags, self.template_path
                        )
                    elif video_id:
                        print("背景選択方式: サムネイル分析（タグなし）")
                        self.background_selector.update_background_by_video_id(
                            video_id, self.template_path
                        )
                    elif tags:
                        print("背景選択方式: カテゴリーベース（動画IDなし）")
                        print(f"  タグ: {tags}")
                        self.background_selector.update_background_by_tags(
                            tags, self.template_path
                        )
                    else:
                        print("背景選択方式: デフォルト（動画ID・タグなし）")
                # サムネイル分析のみ
                elif use_video_analysis and video_id:
                    print("背景選択方式: サムネイル分析のみ")
                    self.background_selector.update_background_by_video_id(
                        video_id, self.template_path
                    )
                # カテゴリーのみ
                elif use_category and tags:
                    print("背景選択方式: カテゴリーベースのみ")
                    print(f"  タグ: {tags}")
                    self.background_selector.update_background_by_tags(
                        tags, self.template_path
                    )
                else:
                    print("背景選択方式: デフォルト（機能が無効またはデータなし）")
                    # デフォルト背景を使用（テンプレートを変更しない）

            except Exception as e:
                print(f"⚠ 背景選択エラー: {e}")
                print("デフォルト背景を使用します")

            # 動画を生成
            try:
                generator = LayerBasedBatchVideoGenerator(
                    self.template_path,
                    self.base_video
                )
                video_path = generator.generate_single_video(
                    artist, song, output_dir,
                    include_artist=include_artist,
                    row=row
                )

                if video_path:
                    generated_videos.append(video_path)
                    print(f"✓ 動画生成完了: {video_path}")
                else:
                    print(f"✗ 動画生成失敗: {artist} - {song}")

            except Exception as e:
                print(f"✗ エラー: {artist} - {song}")
                print(f"  {e}")
                import traceback
                traceback.print_exc()

        # 処理完了後、元のテンプレートを復元
        print(f"\n{'='*60}")
        print("バッチ処理完了")
        print(f"{'='*60}")
        print(f"生成された動画: {len(generated_videos)}/{total}曲")
        print(f"{'='*60}\n")

        self._restore_original_template()
        print(f"✓ テンプレートを元に戻しました: {self.template_path}")

        return generated_videos


def main():
    """メイン実行"""
    import sys

    # コマンドライン引数がある場合はそれを使用
    if len(sys.argv) >= 2:
        csv_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else 'output_videos'
    else:
        # 対話式で入力を受け取る
        print("\n=== バッチ動画生成（CSVから - 動的背景選択） ===")
        print("\n利用可能なCSVファイル:")
        csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
        for i, f in enumerate(csv_files, 1):
            print(f"  {i}. {f}")

        csv_choice = input("\nCSVファイル名を入力 (デフォルト: ranking_all.csv): ").strip()
        csv_path = csv_choice if csv_choice else 'ranking_all.csv'

        output_dir = input("出力ディレクトリ (デフォルト: output_videos): ").strip() or 'output_videos'

    if not os.path.exists(csv_path):
        print(f"エラー: CSVファイルが見つかりません: {csv_path}")
        sys.exit(1)

    # オプション選択（対話式の場合のみ）
    if len(sys.argv) < 2:
        print("\n処理オプション:")
        id_match_only = input("曲IDにマッチする動画がある曲のみ処理しますか? (y/n, デフォルト: n): ").strip().lower() == 'y'
        include_artist = input("アーティスト名を含めますか? (y/n, デフォルト: y): ").strip().lower() != 'n'
    else:
        id_match_only = False
        include_artist = True

    # バッチ生成実行
    generator = DynamicBackgroundBatchGenerator()
    videos = generator.generate_from_csv_with_dynamic_bg(
        csv_path,
        output_dir,
        use_video_analysis=True,  # サムネイル分析を使用
        use_category=True,         # カテゴリーも考慮
        include_artist=include_artist,
        id_match_only=id_match_only
    )

    print(f"\n✅ 完了: {len(videos)}本の動画を生成しました")


if __name__ == '__main__':
    main()
