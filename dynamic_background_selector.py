#!/usr/bin/env python3
"""
動的背景選択システム
曲のカテゴリーとYouTubeサムネイル色分析に基づいて
テンプレートJSONの背景を自動更新
"""

import json
import os
from thumbnail_color_analyzer import ThumbnailColorAnalyzer


class DynamicBackgroundSelector:
    """テンプレートの背景を動的に選択・更新"""

    def __init__(self, template_path='template.json'):
        self.template_path = template_path
        self.analyzer = ThumbnailColorAnalyzer()
        self.template = self._load_template()

    def _load_template(self):
        """テンプレートJSONを読み込み"""
        with open(self.template_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_template(self, output_path=None):
        """テンプレートJSONを保存

        Args:
            output_path: 保存先パス（Noneの場合は元のファイルを上書き）
        """
        if output_path is None:
            output_path = self.template_path

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.template, f, ensure_ascii=False, indent=2)

        print(f"✓ テンプレート保存: {output_path}")

    def update_background_by_video_id(self, video_id, output_path=None):
        """YouTubeビデオIDを使って背景を自動選択

        Args:
            video_id: YouTube動画ID
            output_path: 保存先パス（Noneの場合は元のファイルを上書き）

        Returns:
            更新されたテンプレート
        """
        # サムネイル分析で最適な背景色を取得
        background_path = self.analyzer.analyze_video_thumbnail(video_id)

        # テンプレートの背景レイヤーを更新
        self._update_background_layer(background_path)

        # 保存
        self._save_template(output_path)

        return self.template

    def update_background_by_tags(self, tags, output_path=None):
        """曲のタグ（カテゴリー）から背景を選択

        Args:
            tags: タグのリスト
            output_path: 保存先パス

        Returns:
            更新されたテンプレート
        """
        # カテゴリーから推奨色を取得
        color_name = self.analyzer.get_category_default_color(tags)

        background_path = os.path.join(
            self.analyzer.background_dir,
            f'{color_name}.png'
        )

        print(f"\nカテゴリーベース背景選択")
        print(f"  タグ: {tags}")
        print(f"  選択色: {color_name}")

        # テンプレートの背景レイヤーを更新
        self._update_background_layer(background_path)

        # 保存
        self._save_template(output_path)

        return self.template

    def update_background_by_hybrid(self, video_id, tags, output_path=None):
        """ハイブリッド方式: サムネイル分析 + カテゴリー考慮

        Args:
            video_id: YouTube動画ID
            tags: タグのリスト
            output_path: 保存先パス

        Returns:
            更新されたテンプレート
        """
        print(f"\nハイブリッド背景選択")
        print(f"  動画ID: {video_id}")
        print(f"  タグ: {tags}")

        # まずサムネイル分析
        background_path = self.analyzer.analyze_video_thumbnail(video_id)

        # カテゴリーからの推奨も取得
        category_color = self.analyzer.get_category_default_color(tags)
        print(f"  カテゴリー推奨色: {category_color}")

        # サムネイル分析を優先（より正確）
        # テンプレートの背景レイヤーを更新
        self._update_background_layer(background_path)

        # 保存
        self._save_template(output_path)

        return self.template

    def _update_background_layer(self, new_background_path):
        """テンプレート内の背景レイヤーのパスを更新

        Args:
            new_background_path: 新しい背景画像のパス
        """
        # layers_ordered形式（新形式）
        if 'layers_ordered' in self.template:
            for layer in self.template['layers_ordered']:
                if layer['type'] == 'background':
                    old_path = layer.get('path', '')
                    layer['path'] = new_background_path
                    print(f"  背景レイヤー更新: {os.path.basename(old_path)} → {os.path.basename(new_background_path)}")
                    break

        # layers形式（旧形式）
        elif 'layers' in self.template and 'background' in self.template['layers']:
            for layer in self.template['layers']['background']:
                old_path = layer.get('path', '')
                layer['path'] = new_background_path
                print(f"  背景レイヤー更新: {os.path.basename(old_path)} → {os.path.basename(new_background_path)}")
                break

    def create_template_for_song(self, song_data, taiko_data=None, output_path='template_generated.json'):
        """曲データから専用テンプレートを生成

        Args:
            song_data: 曲データ（video_id含む）
            taiko_data: TaikoGameデータ（tags含む）
            output_path: 保存先パス

        Returns:
            生成されたテンプレート
        """
        video_id = song_data.get('video_id', '')
        tags = []

        if taiko_data and 'tags' in taiko_data:
            tags_str = taiko_data.get('tags', '[]')
            try:
                tags = eval(tags_str) if tags_str else []
            except:
                tags = []

        print(f"\n{'='*60}")
        print(f"テンプレート生成: {song_data.get('song_name', 'Unknown')}")
        print(f"{'='*60}")

        if video_id and tags:
            # ハイブリッド方式
            self.update_background_by_hybrid(video_id, tags, output_path)
        elif video_id:
            # サムネイル分析のみ
            self.update_background_by_video_id(video_id, output_path)
        elif tags:
            # カテゴリーのみ
            self.update_background_by_tags(tags, output_path)
        else:
            print("⚠ video_idもtagsも見つかりません。デフォルト背景を使用")
            self._save_template(output_path)

        return self.template


def main():
    """テスト実行"""
    selector = DynamicBackgroundSelector()

    print("=" * 60)
    print("動的背景選択システム - テスト")
    print("=" * 60)

    # テストケース1: サムネイル分析
    print("\n【テスト1: サムネイル分析】")
    selector.update_background_by_video_id('dQw4w9WgXcQ', 'template_test1.json')

    # テストケース2: カテゴリーベース
    print("\n【テスト2: カテゴリーベース】")
    selector = DynamicBackgroundSelector()  # リロード
    selector.update_background_by_tags(['ボカロ', 'ポップス'], 'template_test2.json')

    # テストケース3: ハイブリッド
    print("\n【テスト3: ハイブリッド】")
    selector = DynamicBackgroundSelector()  # リロード
    selector.update_background_by_hybrid('9bZkp7q19f0', ['K-POP', 'ダンス'], 'template_test3.json')

    print("\n" + "=" * 60)
    print("✅ テスト完了")
    print("=" * 60)


if __name__ == '__main__':
    main()
