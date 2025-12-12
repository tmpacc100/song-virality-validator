import csv
import os
import json
from multiprocessing import Pool, cpu_count
from text_generator import TextImageGenerator
from video_compositor import VideoCompositor


class BatchVideoGenerator:
    """CSVから複数の動画をバッチ生成"""

    def __init__(self, template_path='template.json', base_video='base.mp4'):
        """初期化

        Args:
            template_path: テンプレートJSONのパス
            base_video: ベース動画のパス
        """
        self.template_path = template_path
        self.base_video = base_video
        self.text_generator = TextImageGenerator(template_path)
        self.video_compositor = VideoCompositor(template_path)

    def generate_single_video(self, artist, song, output_dir='output', video_name=None):
        """1つの動画を生成

        Args:
            artist: アーティスト名
            song: 曲名
            output_dir: 出力ディレクトリ
            video_name: 出力動画名（指定しない場合は自動生成）

        Returns:
            生成された動画のパス
        """
        os.makedirs(output_dir, exist_ok=True)

        # テキスト画像を生成
        print(f"\n{'='*60}")
        print(f"処理中: {artist} - {song}")
        print('='*60)

        temp_dir = os.path.join(output_dir, 'temp', f"{artist}_{song}")
        os.makedirs(temp_dir, exist_ok=True)

        text_images = self.text_generator.generate_all_text_images(
            artist, song, temp_dir
        )

        # テキスト画像のパスを取得
        text_image_path = text_images['text']

        # 動画名を決定
        if video_name is None:
            video_name = f"{artist}_{song}.mp4"

        output_video = os.path.join(output_dir, video_name)

        # 動画を合成
        try:
            self.video_compositor.compose_video(
                self.base_video,
                text_image_path,
                output_video,
                use_gpu=True,
                codec='h264_videotoolbox'
            )
        except Exception as e:
            print(f"GPU合成失敗、CPU合成を試行: {e}")
            self.video_compositor.compose_simple(
                self.base_video,
                text_image_path,
                output_video
            )

        print(f"✓ 完成: {output_video}")
        return output_video

    def process_from_csv(self, csv_path, output_dir='output', use_multiprocessing=False):
        """CSVファイルから複数の動画を生成

        Args:
            csv_path: CSVファイルのパス
            output_dir: 出力ディレクトリ
            use_multiprocessing: マルチプロセス処理を使用するか

        Returns:
            生成された動画のパスのリスト
        """
        # CSVを読み込む
        songs = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                artist = row.get('artist_name') or row.get('artist')
                song = row.get('music_name') or row.get('song')
                if artist and song:
                    songs.append((artist, song))

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
        for i, (artist, song) in enumerate(songs, 1):
            print(f"\n[{i}/{len(songs)}]")
            try:
                video_path = self.generate_single_video(artist, song, output_dir)
                results.append(video_path)
            except Exception as e:
                print(f"エラー: {artist} - {song}: {e}")
                results.append(None)
        return results

    def _process_parallel(self, songs, output_dir):
        """並列処理で動画を生成"""
        print(f"マルチプロセス処理 (CPU: {cpu_count()}コア)")

        # ワーカー関数
        def worker(args):
            idx, artist, song = args
            try:
                print(f"\n[{idx + 1}/{len(songs)}] {artist} - {song}")
                generator = BatchVideoGenerator(self.template_path, self.base_video)
                return generator.generate_single_video(artist, song, output_dir)
            except Exception as e:
                print(f"エラー: {artist} - {song}: {e}")
                return None

        # 並列処理
        args = [(i, artist, song) for i, (artist, song) in enumerate(songs)]
        with Pool(processes=min(cpu_count(), len(songs))) as pool:
            results = pool.map(worker, args)

        return results


def main():
    """メイン関数"""
    import sys

    print("=" * 60)
    print("バッチ動画生成ツール")
    print("=" * 60)

    # 引数チェック
    if len(sys.argv) < 2:
        print("\n使用方法:")
        print("  python batch_video_generator.py <csv_file> [base_video]")
        print("\n例:")
        print("  python batch_video_generator.py songs.csv")
        print("  python batch_video_generator.py songs.csv base.mp4")
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
        print("先に template_editor.py を実行してテンプレートを作成してください")
        sys.exit(1)

    # バッチ生成
    generator = BatchVideoGenerator('template.json', base_video)

    # マルチプロセス使用の確認
    use_mp = input("\nマルチプロセス処理を使用しますか? (y/n): ").strip().lower() == 'y'

    results = generator.process_from_csv(
        csv_path,
        output_dir='output_videos',
        use_multiprocessing=use_mp
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
