import json
from PIL import Image, ImageDraw, ImageFont
import os


class TextImageGenerator:
    """テキスト画像を自動生成"""

    def __init__(self, template_path='template.json'):
        """初期化"""
        with open(template_path, 'r', encoding='utf-8') as f:
            self.template = json.load(f)

        self.canvas_w = self.template['canvas']['w']
        self.canvas_h = self.template['canvas']['h']
        self.text_areas = self.template['text_areas']
        self.fonts = self.template['fonts']

    def calculate_font_size(self, text, font_path, max_width, max_height, max_lines):
        """枠内に収まる最大フォントサイズを計算"""
        # 改行で分割
        lines = self.split_text_to_lines(text, max_lines)

        # 二分探索でフォントサイズを見つける
        min_size = 10
        max_size = 500
        best_size = min_size

        while min_size <= max_size:
            mid_size = (min_size + max_size) // 2

            try:
                font = ImageFont.truetype(font_path, mid_size)
            except:
                # フォントが見つからない場合はデフォルトを使用
                font = ImageFont.load_default()

            # テキストの全体サイズを計算
            total_height = 0
            max_line_width = 0

            for line in lines:
                bbox = font.getbbox(line)
                line_width = bbox[2] - bbox[0]
                line_height = bbox[3] - bbox[1]

                max_line_width = max(max_line_width, line_width)
                total_height += line_height

            # 行間を追加
            line_spacing = mid_size * 0.2
            total_height += line_spacing * (len(lines) - 1)

            # 収まるかチェック
            if max_line_width <= max_width and total_height <= max_height:
                best_size = mid_size
                min_size = mid_size + 1
            else:
                max_size = mid_size - 1

        return best_size

    def split_text_to_lines(self, text, max_lines):
        """テキストを指定行数に分割"""
        words = list(text)  # 日本語対応のため文字単位
        if len(words) == 0:
            return [""]

        # 均等に分割
        chars_per_line = len(words) // max_lines + (1 if len(words) % max_lines else 0)

        lines = []
        for i in range(0, len(words), chars_per_line):
            lines.append(''.join(words[i:i + chars_per_line]))

        return lines[:max_lines]

    def generate_text_image(self, text, area_name, output_path, font_path=None, include_background=True):
        """テキスト画像を生成"""
        if area_name not in self.text_areas:
            raise ValueError(f"Unknown text area: {area_name}")

        area = self.text_areas[area_name]
        x, y, w, h = area['x'], area['y'], area['w'], area['h']
        max_lines = area['lines']

        # フォントパスを決定
        if font_path is None:
            font_path = self.fonts.get('primary', self.fonts.get('secondary'))

        # フォントファイルの存在チェック
        if font_path and not os.path.exists(font_path):
            print(f"警告: フォント {font_path} が見つかりません。デフォルトフォントを使用します。")
            font_path = None

        # 最適なフォントサイズを計算
        font_size = self.calculate_font_size(text, font_path, w, h, max_lines)

        # 背景画像を読み込む
        if include_background and 'images' in self.template and len(self.template['images']) > 0:
            bg_path = self.template['images'][0].get('path')
            if bg_path and os.path.exists(bg_path):
                img = Image.open(bg_path).convert('RGBA')
                # サイズをキャンバスに合わせる
                img = img.resize((self.canvas_w, self.canvas_h), Image.Resampling.LANCZOS)
            else:
                print(f"警告: 背景画像 {bg_path} が見つかりません。白背景を使用します。")
                img = Image.new('RGBA', (self.canvas_w, self.canvas_h), (255, 255, 255, 255))
        else:
            # 背景なしの場合は白背景
            img = Image.new('RGBA', (self.canvas_w, self.canvas_h), (255, 255, 255, 255))

        draw = ImageDraw.Draw(img)

        # フォントを読み込み
        if font_path and os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, font_size)
            except:
                font = ImageFont.load_default()
        else:
            font = ImageFont.load_default()

        # テキストを行に分割
        lines = self.split_text_to_lines(text, max_lines)

        # 各行を描画
        line_spacing = font_size * 0.2
        current_y = y

        for line in lines:
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]
            line_height = bbox[3] - bbox[1]

            # 中央揃え
            text_x = x + (w - line_width) // 2

            # テキストを描画（白色、縁取り付き）
            # 縁取り（黒）
            outline_width = max(2, font_size // 30)
            for dx in range(-outline_width, outline_width + 1):
                for dy in range(-outline_width, outline_width + 1):
                    if dx != 0 or dy != 0:
                        draw.text((text_x + dx, current_y + dy), line, font=font, fill=(0, 0, 0, 255))

            # メインテキスト（白）
            draw.text((text_x, current_y), line, font=font, fill=(255, 255, 255, 255))

            current_y += line_height + line_spacing

        # 画像を保存
        img.save(output_path, 'PNG')
        print(f"生成完了: {output_path}")

    def generate_all_text_images(self, artist, song, output_dir='output'):
        """全てのテキスト画像を生成"""
        os.makedirs(output_dir, exist_ok=True)

        # テキストは1種類のみ: アーティスト名の「曲名」弾いてみた
        text = f"{artist}の「{song}」弾いてみた"

        # text_areasの最初のエリアを使用（通常は'artist'だが、名前は問わない）
        area_names = list(self.text_areas.keys())
        if not area_names:
            raise ValueError("テンプレートにtext_areasが定義されていません")

        # 最初のテキストエリアのみ使用
        area_name = area_names[0]
        output_path = os.path.join(output_dir, "text.png")

        self.generate_text_image(text, area_name, output_path)

        return {'text': output_path}


def main():
    """テスト用メイン関数"""
    import sys

    if len(sys.argv) < 3:
        print("使用方法: python text_generator.py <artist> <song>")
        print("例: python text_generator.py Ado うっせぇわ")
        sys.exit(1)

    artist = sys.argv[1]
    song = sys.argv[2]

    generator = TextImageGenerator('template.json')
    output_paths = generator.generate_all_text_images(artist, song)

    print("\n生成されたファイル:")
    for name, path in output_paths.items():
        print(f"  {name}: {path}")


if __name__ == '__main__':
    main()
