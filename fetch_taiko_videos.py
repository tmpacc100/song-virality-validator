#!/usr/bin/env python3
"""
TaikoGameサーバーの未投稿曲データからYouTube APIで動画情報を取得
"""
import csv
import json
import os
import datetime
from src.api.youtube import YouTubeClient

def fetch_taiko_videos(csv_path='filtered data/taiko_server_未投稿_filtered.csv'):
    """TaikoGame CSVからYouTube動画情報を取得"""

    if not os.path.exists(csv_path):
        print(f"エラー: ファイルが見つかりません: {csv_path}")
        return

    # YouTube APIクライアントを初期化
    try:
        youtube_client = YouTubeClient()
        print(f"✓ YouTube API初期化成功 ({len(youtube_client.api_keys)}個のAPIキー)")
    except Exception as e:
        print(f"✗ YouTube API初期化失敗: {e}")
        return

    # CSVを読み込む
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"\n{len(rows)}曲の情報を取得します")
    print("="*60)

    # 結果を保存するリスト
    results = []
    success_count = 0
    fail_count = 0

    for i, row in enumerate(rows, 1):
        song_id = row.get('id', '').strip()
        song_name = row.get('song_name', '').strip()
        artist_name = row.get('artist_name', '').strip()

        if not song_name:
            print(f"[{i}/{len(rows)}] スキップ: 曲名なし")
            continue

        # 検索クエリを構築
        if artist_name:
            query = f"{artist_name} {song_name}"
            print(f"\n[{i}/{len(rows)}] {artist_name} - {song_name}")
        else:
            query = song_name
            print(f"\n[{i}/{len(rows)}] {song_name}")

        try:
            # 動画を検索
            video = youtube_client.search_video(query, max_results=1)

            if video:
                video_id = video['id']['videoId']
                video_title = video['snippet']['title']
                print(f"  ✓ 動画発見: {video_title}")
                print(f"    Video ID: {video_id}")

                # 詳細情報を取得
                details = youtube_client.get_video_details(video_id)

                if details:
                    stats = details.get('statistics', {})
                    snippet = details.get('snippet', {})

                    view_count = int(stats.get('viewCount', 0))
                    like_count = int(stats.get('likeCount', 0))
                    comment_count = int(stats.get('commentCount', 0))
                    published_at = snippet.get('publishedAt', '')

                    print(f"    再生数: {view_count:,}")
                    print(f"    高評価: {like_count:,}")
                    print(f"    コメント: {comment_count:,}")

                    # 結果を保存
                    result = {
                        'id': song_id,
                        'song_name': song_name,
                        'artist_name': artist_name,
                        'video_id': video_id,
                        'video_title': video_title,
                        'view_count': view_count,
                        'like_count': like_count,
                        'comment_count': comment_count,
                        'published_at': published_at,
                        'release_date': row.get('release_date', ''),
                        'tags': row.get('tags', ''),
                        'difficulty': row.get('difficulty', ''),
                        'release_status': row.get('release_status', ''),
                    }

                    # 支持率を計算
                    if view_count > 0:
                        support_rate = (like_count / view_count) * 100
                        result['support_rate'] = round(support_rate, 2)
                    else:
                        result['support_rate'] = 0

                    # エンゲージメント率を計算
                    if view_count > 0:
                        engagement_rate = ((like_count + comment_count) / view_count) * 100
                        result['engagement_rate'] = round(engagement_rate, 2)
                    else:
                        result['engagement_rate'] = 0

                    results.append(result)
                    success_count += 1
                else:
                    print(f"  ✗ 詳細情報取得失敗")
                    fail_count += 1
            else:
                print(f"  ✗ 動画が見つかりません")
                fail_count += 1

        except Exception as e:
            print(f"  ✗ エラー: {e}")
            fail_count += 1

        # 進捗表示
        if i % 10 == 0:
            print(f"\n進捗: {i}/{len(rows)} ({success_count}成功, {fail_count}失敗)")
            print(f"APIリクエスト数: {youtube_client.request_count}")

    # 結果を保存
    print("\n" + "="*60)
    print(f"処理完了: {success_count}成功, {fail_count}失敗")
    print(f"総APIリクエスト数: {youtube_client.request_count}")

    if results:
        # JSONで保存
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path = f'taiko_youtube_data_{timestamp}.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n✓ JSON保存: {json_path}")

        # CSVで保存
        csv_path_out = f'taiko_youtube_data_{timestamp}.csv'
        fieldnames = [
            'id', 'song_name', 'artist_name', 'video_id', 'video_title',
            'view_count', 'like_count', 'comment_count', 'support_rate', 'engagement_rate',
            'published_at', 'release_date', 'tags', 'difficulty', 'release_status'
        ]
        with open(csv_path_out, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        print(f"✓ CSV保存: {csv_path_out}")

        # 統計情報を表示
        print("\n統計情報:")
        avg_views = sum(r['view_count'] for r in results) / len(results)
        avg_likes = sum(r['like_count'] for r in results) / len(results)
        avg_support = sum(r['support_rate'] for r in results) / len(results)
        print(f"  平均再生数: {avg_views:,.0f}")
        print(f"  平均高評価: {avg_likes:,.0f}")
        print(f"  平均支持率: {avg_support:.2f}%")

        # トップ10を表示
        print("\n再生数トップ10:")
        sorted_results = sorted(results, key=lambda x: x['view_count'], reverse=True)
        for i, r in enumerate(sorted_results[:10], 1):
            print(f"  {i}. {r['artist_name']} - {r['song_name']}")
            print(f"     再生数: {r['view_count']:,} | 高評価: {r['like_count']:,}")

def main():
    """メイン関数"""
    print("="*60)
    print("TaikoGame未投稿曲 YouTube情報取得ツール")
    print("="*60)

    csv_path = 'filtered data/taiko_server_未投稿_filtered.csv'

    if not os.path.exists(csv_path):
        print(f"\nエラー: ファイルが見つかりません: {csv_path}")
        return

    # 確認
    print(f"\n対象ファイル: {csv_path}")
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        row_count = sum(1 for _ in reader)
    print(f"曲数: {row_count}")

    confirm = input("\n処理を開始しますか? (y/n): ").strip().lower()
    if confirm != 'y':
        print("キャンセルしました")
        return

    fetch_taiko_videos(csv_path)

if __name__ == '__main__':
    main()
