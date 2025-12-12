import csv
import os
from moviepy import VideoFileClip, TextClip, CompositeVideoClip
from multiprocessing import Pool, cpu_count

# 設定
csv_file = "/Users/shii/Desktop/song virality validator/ranking_all.csv"
base_mp4 = "/Users/shii/Desktop/song virality validator/擬似UNITY動画ファイル/new base.mp4"
output_dir = "./output"

os.makedirs(output_dir, exist_ok=True)

def process_song(args):
    """各曲の動画を生成する処理"""
    song_name, base_mp4_path, output_dir = args

    try:
        # ベース動画読み込み（各プロセスで個別に読み込む）
        base_video = VideoFileClip(base_mp4_path)

        # テキストの作成（中央表示）
        txt_clip = (
            TextClip(
                text=song_name,
                font_size=90,           # 文字サイズ
                color='white',        # 文字色
                stroke_color='black', # 縁取り
                stroke_width=3,
                font="/Library/Fonts/Arial Unicode.ttf",  # 日本語対応フォント
                method='caption',     # テキストレンダリング方法を指定
                size=(base_video.w - 200, None)  # 幅を動画より小さく（余白を大きく）
            )
            .with_duration(base_video.duration)
            .with_position(("center", base_video.h // 2 - 100))  # 中央より上に配置
        )

        # 合成
        final = CompositeVideoClip([base_video, txt_clip])

        # 出力ファイル名
        dst = os.path.join(output_dir, f"{song_name}.mp4")

        # 書き出し
        final.write_videofile(dst, codec="libx264", audio_codec="aac", threads=2)

        # リソース解放
        base_video.close()
        txt_clip.close()
        final.close()

        print(f"✓ 作成完了：{dst}")
        return True
    except Exception as e:
        print(f"✗ エラー ({song_name}): {e}")
        return False

if __name__ == "__main__":
    # CSVから曲名を読み込み
    songs = []
    with open(csv_file, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)  # ヘッダー行

        for row in reader:
            song_name = row[1].strip()  # 2列目が曲名
            if song_name:
                songs.append((song_name, base_mp4, output_dir))

    print(f"処理対象: {len(songs)}曲")
    print(f"使用コア数: {cpu_count()}コア")

    # マルチプロセスで並列処理
    with Pool(processes=cpu_count()) as pool:
        results = pool.map(process_song, songs)

    success_count = sum(results)
    print(f"\n完了: {success_count}/{len(songs)}曲")
