from src.actions import (
    fetch_new_videos,
    manage_tasks,
    export_csv,
    scrape_titles,
    generate_videos,
    refetch_with_artists,
    search_artist_itunes,
    fetch_taikogame_to_csv,
    open_template,
    ml_rl_schedule_optimization
)

def main():
    """メインメニュー"""
    while True:
        print("\n" + "="*60)
        print("YouTube曲バイラリティ分析ツール (Refactored)")
        print("="*60)
        print("1. 新動画fetch（YouTube API）")
        print("2. タスク管理")
        print("3. CSV出力")
        print("4. タイトルスクレイピング（API不要）")
        print("5. 動画生成")
        print("6. アーティスト名のみ更新（API不要）")
        print("7. iTunes APIで全曲アーティスト更新")
        print("8. TaikoGameデータ取得・CSV保存")
        print("9. テンプレート編集")
        print("10. 🤖 ML/RLスケジュール最適化")
        print("0. 終了")

        choice = input("\n選択: ").strip()

        if choice == '1':
            fetch_new_videos()
        elif choice == '2':
            manage_tasks()
        elif choice == '3':
            export_csv()
        elif choice == '4':
            scrape_titles()
        elif choice == '5':
            generate_videos()
        elif choice == '6':
            refetch_with_artists()
        elif choice == '7':
            search_artist_itunes()
        elif choice == '8':
            fetch_taikogame_to_csv()
        elif choice == '9':
            open_template()
        elif choice == '10':
            ml_rl_schedule_optimization()
        elif choice == '0':
            print("\n終了します")
            break
        else:
            print("\n無効な選択です。0-10 のいずれかを入力してください。")

if __name__ == '__main__':
    main()
