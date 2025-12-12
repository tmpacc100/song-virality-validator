import csv
import os
import json
from multiprocessing import Pool, cpu_count
from text_generator_layers import LayerBasedTextGenerator
from video_compositor import VideoCompositor


def _parallel_worker(args):
    """マルチプロセス用のワーカー関数（トップレベル関数として定義）"""
    idx, artist, song, total, template_path, base_video, output_dir, row = args
    try:
        print(f"\n[{idx + 1}/{total}] {artist} - {song}")
        generator = LayerBasedBatchVideoGenerator(template_path, base_video)
        return generator.generate_single_video(artist, song, output_dir, row=row)
    except Exception as e:
        print(f"エラー: {artist} - {song}: {e}")
        import traceback
        traceback.print_exc()
        return None


class LayerBasedBatchVideoGenerator:
    """レイヤー対応CSVバッチ動画生成"""

    def __init__(self, template_path='template.json', base_video='base.mp4'):
        """初期化

        Args:
            template_path: レイヤー対応テンプレートJSONのパス
            base_video: ベース動画のパス（音声用）
        """
        self.template_path = template_path
        self.base_video = base_video
        self.text_generator = LayerBasedTextGenerator(template_path)
        self.video_compositor = VideoCompositor(template_path)

    def generate_single_video(self, artist, song, output_dir='output', video_name=None, base_video_override=None, include_artist=True, row=None):
        """1つの動画を生成

        Args:
            artist: アーティスト名
            song: 曲名
            output_dir: 出力ディレクトリ
            video_name: 出力動画名（指定しない場合は自動生成）
            base_video_override: 使用する動画ファイルのパス（指定しない場合は自動検索）
            include_artist: アーティスト名を含めるかどうか（デフォルト: True）
            row: CSVの行データ（曲IDを含む辞書、オプション）

        Returns:
            生成された動画のパス
        """
        os.makedirs(output_dir, exist_ok=True)

        # === 新規追加: 各曲ごとにテンプレートを再読み込み ===
        # バッチ処理中にtemplate.jsonを変更した場合、次の曲から変更が適用される
        self.text_generator = LayerBasedTextGenerator(self.template_path)
        self.video_compositor = VideoCompositor(self.template_path)
        # === 新規追加ここまで ===

        # 合成画像を生成
        print(f"\n{'='*60}")
        print(f"処理中: {artist} - {song}")
        print('='*60)

        temp_dir = os.path.join(output_dir, 'temp', f"{artist}_{song}")
        os.makedirs(temp_dir, exist_ok=True)

        # 各レイヤーを個別の画像として生成
        layer_images = self.text_generator.generate_all_text_images(
            artist, song, temp_dir, include_artist=include_artist
        )

        background_path = layer_images['background']
        png_overlay_path = layer_images['png_overlay']
        text_overlay_path = layer_images['text']

        # 使用する動画ファイルを決定
        if base_video_override:
            # 明示的に指定された場合
            actual_base_video = base_video_override
            print(f"指定された動画を使用: {actual_base_video}")
        else:
            # outputディレクトリから動画を検索
            video_source_dir = 'output'
            actual_base_video = None

            # 優先順位1: 曲ID（rowに'id'がある場合）
            song_id = row.get('id', '').strip() if row else None
            print(f"[デバッグ] row={row is not None}, song_id='{song_id}'")  # デバッグ
            if song_id:
                # 小文字と大文字両方の拡張子をチェック
                for ext in ['.mp4', '.MP4']:
                    song_id_video_path = os.path.join(video_source_dir, f"{song_id}{ext}")
                    print(f"[デバッグ] 検索中: {song_id_video_path}, 存在={os.path.exists(song_id_video_path)}")  # デバッグ
                    if os.path.exists(song_id_video_path):
                        actual_base_video = song_id_video_path
                        print(f"✓ 曲ID {song_id} に対応する動画を発見: {actual_base_video}")
                        break

            # 優先順位2: 曲名（IDで見つからなかった場合）
            if not actual_base_video:
                # 小文字と大文字両方の拡張子をチェック
                for ext in ['.mp4', '.MP4']:
                    song_video_path = os.path.join(video_source_dir, f"{song}{ext}")
                    if os.path.exists(song_video_path):
                        actual_base_video = song_video_path
                        print(f"曲名に対応する動画を発見: {actual_base_video}")
                        break

            # 優先順位3: デフォルト動画
            if not actual_base_video:
                actual_base_video = self.base_video
                if song_id:
                    print(f"ID {song_id} / 曲名「{song}」に対応する動画が見つかりません。デフォルト動画を使用: {actual_base_video}")
                else:
                    print(f"曲名「{song}」に対応する動画が見つかりません。デフォルト動画を使用: {actual_base_video}")

        # 動画名を決定
        if video_name is None:
            # 曲IDがある場合は末尾に追加
            song_id = row.get('id', '').strip() if row else None
            if song_id:
                video_name = f"{artist}_{song}_{song_id}.mp4"
            else:
                video_name = f"{artist}_{song}.mp4"

        output_video = os.path.join(output_dir, video_name)

        # 動画を合成（レイヤー順序: 背景 → 動画 → PNG → テキスト）
        try:
            self.video_compositor.compose_video(
                base_video=actual_base_video,
                background_image_path=background_path,
                png_overlay_path=png_overlay_path,
                text_overlay_path=text_overlay_path,
                output_path=output_video,
                use_gpu=True,
                codec='h264_videotoolbox'
            )
        except Exception as e:
            print(f"GPU合成失敗、CPU合成を試行: {e}")
            self.video_compositor.compose_video(
                base_video=actual_base_video,
                background_image_path=background_path,
                png_overlay_path=png_overlay_path,
                text_overlay_path=text_overlay_path,
                output_path=output_video,
                use_gpu=False
            )

        print(f"✓ 完成: {output_video}")
        return output_video

    def process_from_csv(self, csv_path, output_dir='output', use_multiprocessing=False, id_match_only=False):
        """CSVファイルから複数の動画を生成

        Args:
            csv_path: CSVファイルのパス
            output_dir: 出力ディレクトリ
            use_multiprocessing: マルチプロセス処理を使用するか
            id_match_only: Trueの場合、曲IDにマッチする動画がある曲のみ処理

        Returns:
            生成された動画のパスのリスト
        """
        # CSVを読み込む
        songs = []
        skipped_count = 0
        video_source_dir = 'output'

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # パターン1: アーティスト名, 曲名（新形式のランキングCSV）
                artist = row.get('アーティスト名') or row.get('artist_name') or row.get('artist')
                song = row.get('曲名') or row.get('music_name') or row.get('song')

                # パターン2: 曲名のみ（旧形式のCSV）
                if not song:
                    song_name = row.get('song_name')
                    if song_name:
                        artist = ""
                        song = song_name

                if song:  # songがあれば追加（artistは空でもOK）
                    # 曲IDマッチのみモードの場合、IDをチェック
                    if id_match_only:
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
                                songs.append((artist or "", song, row))
                            else:
                                skipped_count += 1
                        else:
                            # IDがない場合はスキップ
                            skipped_count += 1
                    else:
                        # 通常モード：全て追加
                        songs.append((artist or "", song, row))

        if id_match_only and skipped_count > 0:
            print(f"\n曲IDマッチなしでスキップ: {skipped_count}曲")

        print(f"\n{len(songs)}曲の動画を生成します")

        if not songs:
            print("エラー: CSVに有効なデータがありません")
            return []

        # 生成開始
        if use_multiprocessing:
            return self._process_parallel(songs, output_dir)
        else:
            return self._process_sequential(songs, output_dir)

    def _process_sequential(self, songs, output_dir):
        """逐次処理で動画を生成"""
        results = []
        for i, (artist, song, row) in enumerate(songs, 1):
            print(f"\n[{i}/{len(songs)}]")
            try:
                video_path = self.generate_single_video(artist, song, output_dir, row=row)
                results.append(video_path)
            except Exception as e:
                print(f"エラー: {artist} - {song}: {e}")
                import traceback
                traceback.print_exc()
                results.append(None)
        return results

    def _process_parallel(self, songs, output_dir):
        """並列処理で動画を生成"""
        print(f"マルチプロセス処理 (CPU: {cpu_count()}コア)")

        # トップレベルのワーカー関数に渡す引数を準備
        args = [
            (i, artist, song, len(songs), self.template_path, self.base_video, output_dir, row)
            for i, (artist, song, row) in enumerate(songs)
        ]

        with Pool(processes=min(cpu_count(), len(songs))) as pool:
            results = pool.map(_parallel_worker, args)

        return results


def main():
    """メイン関数"""
    import sys

    print("=" * 60)
    print("レイヤー対応バッチ動画生成ツール")
    print("=" * 60)

    if len(sys.argv) < 2:
        print("\n使用方法:")
        print("  python batch_video_generator_layers.py <csv_file> [base_video]")
        print("\n例:")
        print("  python batch_video_generator_layers.py songs.csv")
        print("  python batch_video_generator_layers.py ranking_overall.csv base.mp4")
        print("\nCSV形式:")
        print("  artist_name,music_name")
        print("  Ado,うっせぇわ")
        print("  King Gnu,白日")
        sys.exit(1)

    csv_path = sys.argv[1]
    base_video = sys.argv[2] if len(sys.argv) > 2 else 'base.mp4'

    # ファイルチェック
    if not os.path.exists(csv_path):
        print(f"エラー: CSVファイルが見つかりません: {csv_path}")
        sys.exit(1)

    if not os.path.exists(base_video):
        print(f"エラー: ベース動画が見つかりません: {base_video}")
        sys.exit(1)

    if not os.path.exists('template.json'):
        print("エラー: template.json が見つかりません")
        print("先に template_editor_layers.py を実行してテンプレートを作成してください")
        sys.exit(1)

    # バッチ生成
    generator = LayerBasedBatchVideoGenerator('template.json', base_video)

    # オプション選択
    print("\n処理オプション:")
    id_match_only = input("曲IDにマッチする動画がある曲のみ処理しますか? (y/n, デフォルト: n): ").strip().lower() == 'y'
    use_mp = input("マルチプロセス処理を使用しますか? (y/n, デフォルト: n): ").strip().lower() == 'y'

    results = generator.process_from_csv(
        csv_path,
        output_dir='output_videos',
        use_multiprocessing=use_mp,
        id_match_only=id_match_only
    )

    # 結果表示
    print("\n" + "=" * 60)
    print("処理完了")
    print("=" * 60)

    success_count = sum(1 for r in results if r is not None)
    print(f"成功: {success_count}/{len(results)}")

    if success_count > 0:
        print("\n生成された動画:")
        for result in results:
            if result:
                print(f"  ✓ {result}")


if __name__ == '__main__':
    main()
