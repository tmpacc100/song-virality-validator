import json
import subprocess
import os


class VideoCompositor:
    """FFmpegを使用して動画を合成"""

    def __init__(self, template_path='template.json'):
        """初期化"""
        with open(template_path, 'r', encoding='utf-8') as f:
            self.template = json.load(f)

        # 新形式: layers_ordered（順序を保持した配列）
        if 'layers_ordered' in self.template:
            self.layers_ordered = self.template['layers_ordered']
            # videoレイヤーを抽出
            self.video_layers = [layer for layer in self.layers_ordered if layer['type'] == 'video']
        # 旧形式: layers（タイプ別に分類）
        elif 'layers' in self.template:
            self.layers_ordered = None
            self.text_areas = self.template['layers'].get('text_areas', {})
            self.video_layers = self.template['layers'].get('video', [])
        else:
            self.layers_ordered = None
            self.text_areas = self.template.get('text_areas', {})
            self.video_layers = []

        # FFmpegのパスを初期化
        self.ffmpeg_path = 'ffmpeg'

    def check_ffmpeg(self):
        """FFmpegがインストールされているかチェック"""
        # 複数のパスを試す
        ffmpeg_paths = ['ffmpeg', '/opt/homebrew/bin/ffmpeg', '/usr/local/bin/ffmpeg']
        for ffmpeg_path in ffmpeg_paths:
            try:
                result = subprocess.run([ffmpeg_path, '-version'],
                                      capture_output=True,
                                      text=True)
                if result.returncode == 0:
                    self.ffmpeg_path = ffmpeg_path
                    return True
            except FileNotFoundError:
                continue
        return False

    def compose_video(self, base_video, background_image_path, png_overlay_path,
                     text_overlay_path, output_path,
                     use_gpu=True, codec='h264_videotoolbox'):
        """レイヤー順序に従って動画を合成

        Args:
            base_video: ベース動画のパス（動画レイヤーと音声に使用）
            background_image_path: 背景画像のパス
            png_overlay_path: PNGオーバーレイのパス
            text_overlay_path: テキストオーバーレイのパス
            output_path: 出力動画のパス
            use_gpu: GPUエンコードを使用するか
            codec: 使用するコーデック (h264_videotoolbox, h264, など)
        """
        if not self.check_ffmpeg():
            raise RuntimeError("FFmpegがインストールされていません")

        # FFmpegコマンドを構築
        cmd = [self.ffmpeg_path, '-y']  # -y: 上書き確認なし

        # レイヤー順序: 背景 → 動画 → PNG → テキスト
        # 入力ファイルを順番に追加
        cmd.extend(['-loop', '1', '-i', background_image_path])  # [0] 背景画像
        cmd.extend(['-i', base_video])  # [1] 動画
        cmd.extend(['-loop', '1', '-i', png_overlay_path])  # [2] PNGオーバーレイ
        cmd.extend(['-loop', '1', '-i', text_overlay_path])  # [3] テキストオーバーレイ

        # 動画の長さに合わせる
        cmd.extend(['-shortest'])

        # レイヤー情報を取得
        video_layer = None
        png_layer = None

        if self.layers_ordered:
            for layer in self.layers_ordered:
                if layer['type'] == 'video' and layer.get('visible', True):
                    video_layer = layer
                elif layer['type'] == 'image' and layer.get('visible', True):
                    png_layer = layer

        # デフォルト値
        if video_layer:
            vx, vy = video_layer.get('x', 0), video_layer.get('y', 0)
            vw, vh = video_layer.get('w', 720), video_layer.get('h', 1257)
        else:
            vx, vy, vw, vh = 0, 0, 720, 1257

        if png_layer:
            px, py = png_layer.get('x', 0), png_layer.get('y', 0)
            pw, ph = png_layer.get('w', 1080), png_layer.get('h', 1920)
        else:
            px, py, pw, ph = 0, 0, 1080, 1920

        # filter_complexで全レイヤーを合成
        # 注意: 背景・PNG・テキストはtext_generator_layers.pyで
        # 既にキャンバスサイズ（1080x1920等）で生成済み
        # したがってリサイズ不要、overlay=0:0で配置
        # 動画のみテンプレートの座標とサイズに従ってリサイズ・配置
        filter_complex = (
            f'[1:v]scale={vw}:{vh}[video];'  # 動画のみリサイズ
            f'[0:v][video]overlay={vx}:{vy}[bg_video];'  # 背景+動画
            f'[bg_video][2:v]overlay=0:0[bg_video_png];'  # +PNG（リサイズなし、0:0配置）
            f'[bg_video_png][3:v]overlay=0:0[out]'  # +テキスト（リサイズなし、0:0配置）
        )

        cmd.extend(['-filter_complex', filter_complex])
        cmd.extend(['-map', '[out]'])  # 合成された映像
        cmd.extend(['-map', '1:a'])  # ベース動画の音声

        # エンコード設定
        if use_gpu:
            cmd.extend(['-c:v', codec])
            cmd.extend(['-b:v', '8M'])  # ビットレート
        else:
            cmd.extend(['-c:v', 'libx264'])
            cmd.extend(['-preset', 'fast'])
            cmd.extend(['-crf', '23'])

        # オーディオをコピー
        cmd.extend(['-c:a', 'copy'])

        # ピクセルフォーマット
        cmd.extend(['-pix_fmt', 'yuv420p'])

        # 出力ファイル
        cmd.append(output_path)

        print(f"動画合成中: {output_path}")
        print(f"コマンド: {' '.join(cmd)}")

        # FFmpegを実行
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"エラー: {result.stderr}")
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")

        print(f"合成完了: {output_path}")
        return output_path



def main():
    """テスト用メイン関数"""
    import sys

    if len(sys.argv) < 3:
        print("使用方法: python video_compositor.py <base_video> <output_video>")
        print("例: python video_compositor.py input.mp4 output.mp4")
        print("\n各レイヤー画像は output/ ディレクトリから読み込まれます:")
        print("  - background.png (背景)")
        print("  - png_overlay.png (PNGオーバーレイ)")
        print("  - text_overlay.png (テキスト)")
        sys.exit(1)

    base_video = sys.argv[1]
    output_video = sys.argv[2]

    # レイヤー画像のパス
    background = 'output/background.png'
    png_overlay = 'output/png_overlay.png'
    text_overlay = 'output/text_overlay.png'

    # 存在チェック
    for path in [background, png_overlay, text_overlay]:
        if not os.path.exists(path):
            print(f"エラー: 画像が見つかりません: {path}")
            sys.exit(1)

    compositor = VideoCompositor('template.json')

    # GPU利用可能かチェック
    try:
        result = compositor.compose_video(
            base_video=base_video,
            background_image_path=background,
            png_overlay_path=png_overlay,
            text_overlay_path=text_overlay,
            output_path=output_video,
            use_gpu=True,
            codec='h264_videotoolbox'
        )
        print(f"\n完了: {result}")
    except Exception as e:
        print(f"GPU合成失敗、CPU合成を試行: {e}")
        try:
            result = compositor.compose_video(
                base_video=base_video,
                background_image_path=background,
                png_overlay_path=png_overlay,
                text_overlay_path=text_overlay,
                output_path=output_video,
                use_gpu=False
            )
            print(f"\n完了: {result}")
        except Exception as e2:
            print(f"合成失敗: {e2}")
            sys.exit(1)


if __name__ == '__main__':
    main()
