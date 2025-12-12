import json
import csv

def json_to_csv(json_file='rankings.json', output_prefix='ranking'):
    """JSONファイルからCSVファイルを生成"""

    # JSONファイルを読み込む
    with open(json_file, 'r', encoding='utf-8') as f:
        rankings = json.load(f)

    metric_names = {
        'popularity': '人気度ランキング',
        'support_rate': '支持率ランキング',
        'engagement': 'エンゲージメントランキング',
        'growth_rate': '急上昇度ランキング',
        'overall': '総合ランキング'
    }

    # 各ランキングごとにCSVを作成
    for metric_key, metric_name in metric_names.items():
        if metric_key not in rankings:
            continue

        csv_filename = f"{output_prefix}_{metric_key}.csv"

        with open(csv_filename, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)

            # ヘッダー行
            writer.writerow([
                '順位',
                'アーティスト名',
                '曲名',
                '動画タイトル',
                'Video ID',
                '再生数',
                '高評価数',
                '支持率(%)',
                'コメント数',
                '急上昇度(views/day)',
                '公開日数'
            ])

            # データ行
            for item in rankings[metric_key]:
                writer.writerow([
                    item['rank'],
                    item.get('artist_name', ''),
                    item['song_name'],
                    item.get('video_title', ''),
                    item['video_id'],
                    item['metrics']['view_count'],
                    item['metrics']['like_count'],
                    item['metrics']['support_rate'],
                    item['metrics']['comment_count'],
                    item['metrics']['growth_rate'],
                    item['metrics']['days_since_published']
                ])

        print(f"作成完了: {csv_filename} ({len(rankings[metric_key])}曲)")

    # 全ランキングを1つのCSVにまとめる
    create_combined_csv(rankings, f"{output_prefix}_all.csv")


def create_combined_csv(rankings, output_file):
    """全てのランキング情報を1つのCSVにまとめる"""

    # 全ての曲を収集（重複を削除）
    all_songs = {}

    for metric_key in ['popularity', 'support_rate', 'engagement', 'growth_rate', 'overall']:
        if metric_key not in rankings:
            continue

        for item in rankings[metric_key]:
            song_name = item['song_name']
            if song_name not in all_songs:
                all_songs[song_name] = {
                    'artist_name': item.get('artist_name', ''),
                    'video_title': item.get('video_title', ''),
                    'video_id': item['video_id'],
                    'metrics': item['metrics'],
                    'ranks': {}
                }
            all_songs[song_name]['ranks'][metric_key] = item['rank']

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)

        # ヘッダー行
        writer.writerow([
            'アーティスト名',
            '曲名',
            '動画タイトル',
            'Video ID',
            '再生数',
            '高評価数',
            '支持率(%)',
            'コメント数',
            '急上昇度(views/day)',
            '公開日数',
            '人気度順位',
            '支持率順位',
            'エンゲージメント順位',
            '急上昇度順位',
            '総合順位'
        ])

        # 総合順位でソート
        sorted_songs = sorted(
            all_songs.items(),
            key=lambda x: x[1]['ranks'].get('overall', 999)
        )

        # データ行
        for song_name, data in sorted_songs:
            writer.writerow([
                data.get('artist_name', ''),
                song_name,
                data.get('video_title', ''),
                data['video_id'],
                data['metrics']['view_count'],
                data['metrics']['like_count'],
                data['metrics']['support_rate'],
                data['metrics']['comment_count'],
                data['metrics']['growth_rate'],
                data['metrics']['days_since_published'],
                data['ranks'].get('popularity', '-'),
                data['ranks'].get('support_rate', '-'),
                data['ranks'].get('engagement', '-'),
                data['ranks'].get('growth_rate', '-'),
                data['ranks'].get('overall', '-')
            ])

    print(f"作成完了: {output_file} (全{len(all_songs)}曲)")


if __name__ == '__main__':
    print("JSONからCSVへの変換を開始します...")
    print("="*60)
    json_to_csv()
    print("="*60)
    print("変換が完了しました！")
