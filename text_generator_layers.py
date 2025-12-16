import json
from PIL import Image, ImageDraw, ImageFont
import os


class LayerBasedTextGenerator:
    """レイヤー対応テキスト画像生成"""

    def __init__(self, template_path='template.json'):
        """初期化"""
        with open(template_path, 'r', encoding='utf-8') as f:
            self.template = json.load(f)

        self.canvas_w = self.template['canvas']['w']
        self.canvas_h = self.template['canvas']['h']

        # 新形式: layers_ordered（順序を保持した配列）
        if 'layers_ordered' in self.template:
            self.layers_ordered = self.template['layers_ordered']
        # 旧形式: layers（タイプ別に分類）
        elif 'layers' in self.template:
            self.layers = self.template['layers']
            self.layers_ordered = None
        else:
            self.layers_ordered = None
            self.layers = {'background': [], 'video': [], 'images': []}

        self.text_areas = self.template.get('text_areas', {})
        self.fonts = self.template.get('fonts', {})

    def calculate_font_size(self, text, font_path, max_width, max_height, max_lines):
        """枠内に収まる最大フォントサイズを計算"""
        lines = self.split_text_to_lines(text, max_lines)

        min_size = 10
        max_size = 500
        best_size = min_size

        while min_size <= max_size:
            mid_size = (min_size + max_size) // 2

            try:
                if font_path and os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, mid_size)
                else:
                    font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()

            total_height = 0
            max_line_width = 0

            for line in lines:
                bbox = font.getbbox(line)
                line_width = bbox[2] - bbox[0]
                # getbbox()はベースラインからの相対座標を返すため、
                # 実際の描画高さはフォントサイズを基準にする
                line_height = mid_size
                max_line_width = max(max_line_width, line_width)
                total_height += line_height

            line_spacing = mid_size * 0.2
            total_height += line_spacing * (len(lines) - 1)

            if max_line_width <= max_width and total_height <= max_height:
                best_size = mid_size
                min_size = mid_size + 1
            else:
                max_size = mid_size - 1

        return best_size

    def split_text_to_lines(self, text, max_lines):
        """テキストを§§§の位置でのみ改行して分割

        例: "アーティスト名の§§§「曲名」§§§弾いてみた"
        -> ["アーティスト名の", "「曲名」", "弾いてみた"]

        §§§がない場合は1行で返す
        """
        if not text:
            return [""]

        # §§§が含まれている場合は§§§で分割
        if '§§§' in text:
            parts = text.split('§§§')
            # 空の要素を除去
            lines = [part for part in parts if part]
            return lines[:max_lines]
        else:
            # §§§がない場合は1行として返す
            return [text]

    def generate_composite_image(self, artist, song, output_path, include_artist=True):
        """全レイヤーを合成した最終画像を生成

        レイヤー順: template.jsonの layers_ordered 配列の順番通りに合成

        Args:
            artist: アーティスト名
            song: 曲名
            output_path: 出力パス
            include_artist: アーティスト名を含めるかどうか（デフォルト: True）
        """
        # ベース画像を作成
        composite = Image.new('RGBA', (self.canvas_w, self.canvas_h), (255, 255, 255, 255))

        # 新形式: layers_ordered を使用（順序を保持）
        if self.layers_ordered is not None:
            for layer in self.layers_ordered:
                if not layer.get('visible', True):
                    continue

                layer_type = layer.get('type')
                path = layer.get('path')
                x, y = layer.get('x', 0), layer.get('y', 0)
                w, h = layer.get('w', 100), layer.get('h', 100)

                if layer_type == 'background' and path and os.path.exists(path):
                    # 背景画像を合成（アスペクト比保持）
                    bg_img = Image.open(path).convert('RGBA')
                    original_w, original_h = bg_img.size
                    aspect_ratio = original_w / original_h

                    if w / h > aspect_ratio:
                        new_h = h
                        new_w = int(h * aspect_ratio)
                    else:
                        new_w = w
                        new_h = int(w / aspect_ratio)

                    bg_img = bg_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    paste_x = x + (w - new_w) // 2
                    paste_y = y + (h - new_h) // 2
                    composite.paste(bg_img, (paste_x, paste_y), bg_img)

                elif layer_type == 'video' and path:
                    # 動画レイヤーはスキップ（動画生成時に実際の動画を合成）
                    # プレビュー用に半透明の青色で表示する場合は以下をコメント解除
                    # video_overlay = Image.new('RGBA', (w, h), (100, 150, 255, 100))
                    # composite.paste(video_overlay, (x, y), video_overlay)
                    pass

                elif layer_type == 'image' and path and os.path.exists(path):
                    # PNG画像を合成（アスペクト比保持）
                    png_img = Image.open(path).convert('RGBA')
                    original_w, original_h = png_img.size
                    aspect_ratio = original_w / original_h

                    if w / h > aspect_ratio:
                        new_h = h
                        new_w = int(h * aspect_ratio)
                    else:
                        new_w = w
                        new_h = int(w / aspect_ratio)

                    png_img = png_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    paste_x = x + (w - new_w) // 2
                    paste_y = y + (h - new_h) // 2
                    composite.paste(png_img, (paste_x, paste_y), png_img)

        # 旧形式: background, video, images の順で合成（後方互換性）
        else:
            # 1. 背景レイヤーを合成
            for bg_layer in self.layers.get('background', []):
                if bg_layer.get('visible', True) and bg_layer.get('path'):
                    path = bg_layer['path']
                    if os.path.exists(path):
                        bg_img = Image.open(path).convert('RGBA')
                        x, y = bg_layer.get('x', 0), bg_layer.get('y', 0)
                        w, h = bg_layer.get('w', self.canvas_w), bg_layer.get('h', self.canvas_h)
                        bg_img = bg_img.resize((w, h), Image.Resampling.LANCZOS)
                        composite.paste(bg_img, (x, y), bg_img)

            # 2. 動画レイヤー（静止画として表示）
            for video_layer in self.layers.get('video', []):
                if video_layer.get('visible', True) and video_layer.get('path'):
                    # 動画の代わりに動画エリアを示す矩形を描画
                    x, y = video_layer.get('x', 0), video_layer.get('y', 0)
                    w, h = video_layer.get('w', 100), video_layer.get('h', 100)

                    # 動画エリアを半透明の青で表示
                    video_overlay = Image.new('RGBA', (w, h), (100, 150, 255, 100))
                    composite.paste(video_overlay, (x, y), video_overlay)

            # 3. PNGレイヤーを合成
            for img_layer in self.layers.get('images', []):
                if img_layer.get('visible', True) and img_layer.get('path'):
                    path = img_layer['path']
                    if os.path.exists(path):
                        png_img = Image.open(path).convert('RGBA')
                        x, y = img_layer.get('x', 0), img_layer.get('y', 0)
                        # テンプレートで指定されたサイズを使用
                        w = img_layer.get('w')
                        h = img_layer.get('h')
                        if w and h:
                            # テンプレートで指定されたサイズに直接リサイズ
                            png_img = png_img.resize((w, h), Image.Resampling.LANCZOS)
                            composite.paste(png_img, (x, y), png_img)

        # 4. テキストレイヤーを描画
        draw = ImageDraw.Draw(composite)

        # テキスト生成（§§§で改行位置を指定）
        if include_artist and artist:
            text = f"{artist}の§§§「{song}」§§§弾いてみた"
        else:
            text = f"「{song}」§§§弾いてみた"

        for area_name, area in self.text_areas.items():
            x, y, w, h = area['x'], area['y'], area['w'], area['h']
            max_lines = area.get('lines', 3)

            # フォントパスを決定（テンプレートに指定があればそれを優先）
            area_font = area.get('font')  # テキストエリアごとのフォント設定
            template_font = self.fonts.get('primary', self.fonts.get('secondary'))

            # デフォルトでRampartOne-Regular.ttfを使用
            fallback_fonts = [
                area_font,  # テキストエリア固有のフォント（最優先）
                'fonts/RampartOne-Regular.ttf',  # fontsディレクトリ（優先）
                'RampartOne-Regular.ttf',  # カレントディレクトリ（後方互換性）
                template_font,  # テンプレート全体のフォント設定
                '/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc',
                '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',
                '/System/Library/Fonts/Hiragino Sans GB.ttc',
                '/Library/Fonts/Arial Unicode.ttf'
            ]

            working_font_path = None
            for fp in fallback_fonts:
                if fp and os.path.exists(fp):
                    working_font_path = fp
                    break

            # 最適なフォントサイズを計算
            font_size = self.calculate_font_size(text, working_font_path, w, h, max_lines)

            # フォントを読み込み
            if working_font_path:
                try:
                    font = ImageFont.truetype(working_font_path, font_size)
                except Exception as e:
                    print(f"フォント読み込みエラー: {e}")
                    font = ImageFont.load_default()
            else:
                print("警告: 日本語フォントが見つかりません。デフォルトフォントを使用します。")
                font = ImageFont.load_default()

            # テキストを行に分割
            lines = self.split_text_to_lines(text, max_lines)

            # 行間スペース
            line_spacing = font_size * 0.2

            # まず全体の高さを計算して垂直中央を求める
            total_height = 0
            line_info = []
            for line in lines:
                bbox = font.getbbox(line)
                line_width = bbox[2] - bbox[0]
                # 実際の描画高さはフォントサイズを基準にする（はみ出し防止）
                line_height = font_size
                line_info.append((line, line_width, line_height))
                total_height += line_height

            # 行間を追加
            total_height += line_spacing * (len(lines) - 1)

            # 垂直中央揃えの開始位置を計算
            current_y = y + (h - total_height) // 2

            # 各行を描画
            for line, line_width, line_height in line_info:
                # 水平中央揃え
                text_x = x + (w - line_width) // 2

                # === 新規追加: 文字の内側に小さい文字パターンを描画 ===
                try:
                    import numpy as np
                    import random
                    # テキストマスクを取得
                    mask = font.getmask(line)
                    if mask.size[0] > 0 and mask.size[1] > 0:
                        # サイズを整数に変換
                        mask_w = int(mask.size[0])
                        mask_h = int(mask.size[1])

                        # マスクをnumpy配列経由でImage形式に変換
                        mask_array = np.array(mask).reshape(mask_h, mask_w)
                        mask_image = Image.fromarray(mask_array, mode='L')

                        # 小さい文字パターンを描画する画像を作成
                        pattern_img = Image.new('RGBA', (mask_w, mask_h), (255, 255, 255, 0))
                        pattern_draw = ImageDraw.Draw(pattern_img)

                        # 小さいフォントサイズ（メインテキストの1/8くらい）
                        small_font_size = max(8, font_size // 8)
                        try:
                            small_font = ImageFont.truetype(working_font_path, small_font_size)
                        except:
                            small_font = font

                        # ランダムに小さい文字を配置
                        # 文字の種類（曲名やアーティスト名の文字を使用）
                        chars = list(set(line))  # 重複を除いた文字リスト
                        if not chars:
                            chars = ['♪', '♫', '♬', '♭', '♯']  # デフォルト音楽記号

                        # グリッド状に配置
                        step_x = small_font_size
                        step_y = small_font_size
                        for py in range(0, mask_h, step_y):
                            for px in range(0, mask_w, step_x):
                                # ランダムに文字を選択
                                char = random.choice(chars)
                                # 透明度を調整（20-40%）
                                alpha = random.randint(50, 100)
                                # 白い小さい文字を描画
                                pattern_draw.text((px, py), char, font=small_font,
                                                fill=(255, 255, 255, alpha))

                        # パターン画像をそのまま使用（白背景なし）
                        # compositeにパターンを貼り付け
                        composite.paste(pattern_img, (int(text_x), int(current_y)), mask_image)
                except Exception as e:
                    print(f"警告: パターン背景の描画に失敗しました: {e}")
                # === 新規追加ここまで ===

                # 縁取り（黒）- ボールド強調版
                outline_width = max(4, font_size // 15)  # 元の2倍の太さ
                for dx in range(-outline_width, outline_width + 1):
                    for dy in range(-outline_width, outline_width + 1):
                        if dx != 0 or dy != 0:
                            draw.text((text_x + dx, current_y + dy), line,
                                    font=font, fill=(0, 0, 0, 255))

                # メインテキスト（白）
                draw.text((text_x, current_y), line, font=font, fill=(255, 255, 255, 255))
                current_y += line_height + line_spacing

        # 画像を保存
        composite.save(output_path, 'PNG')
        print(f"合成画像生成完了: {output_path}")
        return output_path

    def generate_all_text_images(self, artist, song, output_dir='output', include_artist=True):
        """各レイヤーを個別の画像として生成

        Args:
            artist: アーティスト名
            song: 曲名
            output_dir: 出力ディレクトリ
            include_artist: アーティスト名を含めるかどうか（デフォルト: True）

        Returns:
            dict: {
                'background': 背景画像のパス,
                'png_overlay': PNGオーバーレイのパス,
                'text': テキストオーバーレイのパス
            }
        """
        os.makedirs(output_dir, exist_ok=True)

        results = {}

        # 1. 背景画像を生成
        background_path = os.path.join(output_dir, "background.png")
        background = Image.new('RGBA', (self.canvas_w, self.canvas_h), (255, 255, 255, 0))

        if self.layers_ordered:
            for layer in self.layers_ordered:
                if not layer.get('visible', True):
                    continue

                if layer['type'] == 'background':
                    path = layer.get('path')
                    if path and os.path.exists(path):
                        x, y = layer.get('x', 0), layer.get('y', 0)
                        w, h = layer.get('w', self.canvas_w), layer.get('h', self.canvas_h)
                        bg_img = Image.open(path).convert('RGBA')

                        # アスペクト比を保持してリサイズ
                        original_w, original_h = bg_img.size
                        aspect_ratio = original_w / original_h

                        # テンプレートで指定された枠に収まるようにリサイズ
                        if w / h > aspect_ratio:
                            # 高さに合わせる
                            new_h = h
                            new_w = int(h * aspect_ratio)
                        else:
                            # 幅に合わせる
                            new_w = w
                            new_h = int(w / aspect_ratio)

                        bg_img = bg_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                        # 中央配置
                        paste_x = x + (w - new_w) // 2
                        paste_y = y + (h - new_h) // 2
                        background.paste(bg_img, (paste_x, paste_y), bg_img)
                    break  # 最初の背景レイヤーのみ使用

        background.save(background_path, 'PNG')
        results['background'] = background_path
        print(f"背景画像生成完了: {background_path}")

        # 2. PNGオーバーレイを生成
        png_overlay_path = os.path.join(output_dir, "png_overlay.png")
        png_overlay = Image.new('RGBA', (self.canvas_w, self.canvas_h), (255, 255, 255, 0))

        if self.layers_ordered:
            for layer in self.layers_ordered:
                if not layer.get('visible', True):
                    continue

                if layer['type'] == 'image':
                    path = layer.get('path')
                    if path and os.path.exists(path):
                        x, y = layer.get('x', 0), layer.get('y', 0)
                        w, h = layer.get('w', self.canvas_w), layer.get('h', self.canvas_h)
                        png_img = Image.open(path).convert('RGBA')

                        # アスペクト比を保持してリサイズ
                        original_w, original_h = png_img.size
                        aspect_ratio = original_w / original_h

                        # テンプレートで指定された枠に収まるようにリサイズ
                        if w / h > aspect_ratio:
                            # 高さに合わせる
                            new_h = h
                            new_w = int(h * aspect_ratio)
                        else:
                            # 幅に合わせる
                            new_w = w
                            new_h = int(w / aspect_ratio)

                        png_img = png_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                        # 中央配置
                        paste_x = x + (w - new_w) // 2
                        paste_y = y + (h - new_h) // 2
                        png_overlay.paste(png_img, (paste_x, paste_y), png_img)

        png_overlay.save(png_overlay_path, 'PNG')
        results['png_overlay'] = png_overlay_path
        print(f"PNGオーバーレイ生成完了: {png_overlay_path}")

        # 3. テキストオーバーレイを生成
        text_overlay_path = os.path.join(output_dir, "text_overlay.png")
        text_overlay = Image.new('RGBA', (self.canvas_w, self.canvas_h), (255, 255, 255, 0))
        draw = ImageDraw.Draw(text_overlay)

        # テキスト生成（§§§で改行位置を指定）
        if include_artist and artist:
            text = f"{artist}の§§§「{song}」§§§弾いてみた"
        else:
            text = f"「{song}」§§§弾いてみた"

        for area_name, area in self.text_areas.items():
            x, y, w, h = area['x'], area['y'], area['w'], area['h']
            max_lines = area.get('lines', 3)

            # フォントパスを決定（テンプレートに指定があればそれを優先）
            area_font = area.get('font')  # テキストエリアごとのフォント設定
            template_font = self.fonts.get('primary', self.fonts.get('secondary'))

            # デフォルトでRampartOne-Regular.ttfを使用
            fallback_fonts = [
                area_font,  # テキストエリア固有のフォント（最優先）
                'fonts/RampartOne-Regular.ttf',  # fontsディレクトリ（優先）
                'RampartOne-Regular.ttf',  # カレントディレクトリ（後方互換性）
                template_font,  # テンプレート全体のフォント設定
                '/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc',
                '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',
                '/System/Library/Fonts/Hiragino Sans GB.ttc',
                '/Library/Fonts/Arial Unicode.ttf'
            ]

            working_font_path = None
            for fp in fallback_fonts:
                if fp and os.path.exists(fp):
                    working_font_path = fp
                    break

            # 最適なフォントサイズを計算
            font_size = self.calculate_font_size(text, working_font_path, w, h, max_lines)

            # フォントを読み込み
            if working_font_path:
                try:
                    font = ImageFont.truetype(working_font_path, font_size)
                except Exception as e:
                    print(f"フォント読み込みエラー: {e}")
                    font = ImageFont.load_default()
            else:
                print("警告: 日本語フォントが見つかりません。デフォルトフォントを使用します。")
                font = ImageFont.load_default()

            # テキストを行に分割
            lines = self.split_text_to_lines(text, max_lines)

            # 行間スペース
            line_spacing = font_size * 0.2

            # まず全体の高さを計算して垂直中央を求める
            total_height = 0
            line_info = []
            for line in lines:
                bbox = font.getbbox(line)
                line_width = bbox[2] - bbox[0]
                # 実際の描画高さはフォントサイズを基準にする（はみ出し防止）
                line_height = font_size
                line_info.append((line, line_width, line_height))
                total_height += line_height

            # 行間を追加
            total_height += line_spacing * (len(lines) - 1)

            # 垂直中央揃えの開始位置を計算
            current_y = y + (h - total_height) // 2

            # 各行を描画
            for line, line_width, line_height in line_info:
                # 水平中央揃え
                text_x = x + (w - line_width) // 2

                # === 新規追加: 文字の内側に白背景を描画 ===
                try:
                    import numpy as np
                    # テキストマスクを取得
                    mask = font.getmask(line)
                    if mask.size[0] > 0 and mask.size[1] > 0:
                        # サイズを整数に変換
                        mask_w = int(mask.size[0])
                        mask_h = int(mask.size[1])

                        # マスクをnumpy配列経由でImage形式に変換
                        mask_array = np.array(mask).reshape(mask_h, mask_w)
                        mask_image = Image.fromarray(mask_array, mode='L')

                        # 白い塗りつぶし画像を作成
                        white_fill = Image.new('RGBA', (mask_w, mask_h), (255, 255, 255, 255))

                        # text_overlayに白背景を貼り付け
                        text_overlay.paste(white_fill, (int(text_x), int(current_y)), mask_image)
                except Exception as e:
                    print(f"警告: 白背景の描画に失敗しました: {e}")
                # === 新規追加ここまで ===

                # 縁取り（黒）- ボールド強調版
                outline_width = max(4, font_size // 15)  # 元の2倍の太さ
                for dx in range(-outline_width, outline_width + 1):
                    for dy in range(-outline_width, outline_width + 1):
                        if dx != 0 or dy != 0:
                            draw.text((text_x + dx, current_y + dy), line,
                                    font=font, fill=(0, 0, 0, 255))

                # メインテキスト（白）
                draw.text((text_x, current_y), line, font=font, fill=(255, 255, 255, 255))
                current_y += line_height + line_spacing

        text_overlay.save(text_overlay_path, 'PNG')
        results['text'] = text_overlay_path
        print(f"テキストオーバーレイ生成完了: {text_overlay_path}")

        return results


def main():
    """テスト用メイン関数"""
    import sys

    if len(sys.argv) < 3:
        print("使用方法: python text_generator_layers.py <artist> <song>")
        print("例: python text_generator_layers.py Ado うっせぇわ")
        sys.exit(1)

    artist = sys.argv[1]
    song = sys.argv[2]

    generator = LayerBasedTextGenerator('template.json')
    output_paths = generator.generate_all_text_images(artist, song)

    print("\n生成されたファイル:")
    for name, path in output_paths.items():
        print(f"  {name}: {path}")


if __name__ == '__main__':
    main()
