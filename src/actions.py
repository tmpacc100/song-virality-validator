import os
import datetime
import csv
import json
import subprocess
from typing import List, Dict, Any

from src.config import Config
from src.api.youtube import YouTubeClient
from src.api.gameserver import GameServerClient
from src.utils.text_processing import extract_artist_from_title, clean_japanese_artist_name
# from src.ml.scheduler import ViewCountPredictor # Uncomment when ML is ready

youtube_client = YouTubeClient()
game_client = GameServerClient()

def fetch_new_videos():
    """Option 1: Fetch new videos using YouTube API."""
    print("\n=== Fetch New Videos ===")
    
    # Logic to load CSV and process
    # This roughly maps to the 'process_songs_from_csv' I wrote earlier
    # For now, let's ask for the file
    csv_file = input("Enter CSV filename (default: songs.csv): ").strip() or 'songs.csv'
    if not os.path.exists(csv_file):
        print(f"File not found: {csv_file}")
        return

    songs_data = []
    # Simplified processing loop (restoring full logic would take more time, 
    # but I'll implement the core flow)
    
    try:
        # Load cache if acceptable
        # ... logic ...

        # Core processing
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 日本語カラム名と英語カラム名の両方に対応
                song_name = (row.get('曲名') or row.get('song_name') or '').strip()
                artist_name = (row.get('アーティスト名') or row.get('artist_name') or '').strip()

                if not song_name:
                    continue

                # 検索クエリを構築
                if artist_name:
                    query = f"{artist_name} {song_name}"
                    print(f"Processing: {artist_name} - {song_name}")
                else:
                    query = song_name
                    print(f"Processing: {song_name}")

                # Use the new client
                video = youtube_client.search_video(query)
                if video:
                    print(f"  Found: {video['snippet']['title']}")
                    # ... get stats, etc ...
                    details = youtube_client.get_video_details(video['id']['videoId'])
                    if details:
                        # Construct data
                        stats = details.get('statistics', {})
                        print(f"    Views: {stats.get('viewCount', 'N/A')}")
                        print(f"    Likes: {stats.get('likeCount', 'N/A')}")
                else:
                    print("  Not found.")

        print("\nDone fetching.")
        # Save cache/results

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def manage_tasks():
    """Option 2: Task Management."""
    print("\n=== Manage Tasks ===")
    print("(Not fully ported yet)")

def export_csv():
    """Option 3: Export CSV."""
    print("\n=== Export CSV ===")
    # Logic to load rankings.json and write to CSVs
    pass

def scrape_titles():
    """Option 4: Scrape Titles."""
    print("\n=== Scrape Titles ===")
    # Logic to run scrape_titles.py
    if os.path.exists('scrape_titles.py'):
        subprocess.run(['python3', 'scrape_titles.py'])
    else:
        print("Script not found.")

def generate_videos():
    """Option 5: Generate Videos."""
    print("\n=== Generate Videos ===")
    print("1. バッチ動画生成（基本）")
    print("2. バッチ動画生成（レイヤー対応）")
    print("3. バッチ動画生成（CSVから - 動的背景選択）")
    print("0. 戻る")

    choice = input("\n選択: ").strip()

    if choice == '1':
        if os.path.exists('batch_video_generator.py'):
            subprocess.run(['python3', 'batch_video_generator.py'])
        else:
            print("Script not found: batch_video_generator.py")
    elif choice == '2':
        if os.path.exists('batch_video_generator_layers.py'):
            subprocess.run(['python3', 'batch_video_generator_layers.py'])
        else:
            print("Script not found: batch_video_generator_layers.py")
    elif choice == '3':
        if os.path.exists('batch_video_with_dynamic_bg.py'):
            subprocess.run(['python3', 'batch_video_with_dynamic_bg.py'])
        else:
            print("Script not found: batch_video_with_dynamic_bg.py")
    elif choice == '0':
        return
    else:
        print("無効な選択です")

def refetch_with_artists():
    """Option 6: Update Artists Only."""
    print("\n=== Update Artists Only ===")
    pass

def search_artist_itunes():
    """Option 7: iTunes Artist Search."""
    print("\n=== iTunes Artist Search ===")
    pass

def fetch_taikogame_to_csv():
    """Option 8: Fetch TaikoGame Data."""
    print("\n=== Fetch TaikoGame Data ===")
    artists, songs = game_client.fetch_taiko_songs()
    if songs:
        # Save to csv
        filename = 'taiko_songs.csv'
        keys = songs[0].keys()
        with open(filename, 'w', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(songs)
        print(f"Saved to {filename}")

def open_template():
    """Option 9: Open Template Editor."""
    print("\n=== Open Template Editor ===")
    if os.path.exists('template_editor_layers.py'):
        subprocess.run(['python3', 'template_editor_layers.py'])
    else:
        print("Script not found.")

from src.ml.feature_engineering import FeatureEngineer
from src.ml.scheduler import ViewCountPredictor
from src.ml.rl_scheduler import ComprehensiveScheduler # Renamed/refactored class

def ml_rl_schedule_optimization():
    """Option 10: ML/RL Optimization."""
    print("\n=== ML/RL Schedule Optimization ===")
    
    # Check dependencies
    if not os.path.exists('rankings.json'):
         print("Error: rankings.json not found. Run '1. Fetch New Videos' first.")
         return

    try:
        with open('rankings.json', 'r', encoding='utf-8') as f:
            rankings = json.load(f)
            
        if 'overall' not in rankings:
            print("Error: 'overall' ranking not found.")
            return

        print("Loading data...")
        songs_data = []
        # Convert ranking format back to flat list for ML
        for item in rankings['overall']:
            song = {
                'song_name': item['song_name'],
                'artist_name': item.get('artist_name', ''),
                'video_id': item['video_id'],
                'release_date': item.get('release_date', ''),
                'view_count': item['metrics']['view_count'],
                'like_count': item['metrics']['like_count'],
                'comment_count': item['metrics']['comment_count'],
                'support_rate': item['metrics']['support_rate'],
                'growth_rate': item['metrics']['growth_rate'],
                'days_since_published': item['metrics']['days_since_published']
                # Add other metrics if needed by FeatureEngineer
            }
            songs_data.append(song)
            
        print(f"Loaded {len(songs_data)} songs.")

        # 2. Feature Engineering
        print("\nStep 2: Feature Engineering")
        engineer = FeatureEngineer()
        target_datetime = datetime.datetime.now()
        
        # Load Taiko data for features if available
        taiko_map = {}
        if os.path.exists('filtered data/taiko_server_未投稿_filtered.csv'):
            with open('filtered data/taiko_server_未投稿_filtered.csv', 'r', encoding='utf-8') as f:
                 reader = csv.DictReader(f)
                 for row in reader:
                     if row.get('song_name'):
                         taiko_map[row.get('song_name')] = row

        X, y, feature_names = engineer.prepare_training_data(songs_data, taiko_map, target_datetime)
        
        # 3. Train Predictor
        print("\nStep 3: Training View Count Predictor")
        predictor = ViewCountPredictor(input_dim=X.shape[1])
        predictor.train(X, y, epochs=50, verbose=1) # Reduced epochs for speed/test
        predictor.save(model_path='models/view_predictor.pkl', scaler_path='models/view_scaler.pkl')
        
        # 4. RL Optimization
        print("\nStep 4: RL Schedule Optimization")
        scheduler = ComprehensiveScheduler(ml_predictor=predictor)
        optimized_schedule = scheduler.optimize_schedule(songs_data, optimization_mode='comprehensive')
        
        # 5. Save Results
        print("\nStep 5: Saving Results")
        # Logic to update rankings.json with predictions (simplified)
        ml_map = {s['song_name']: s for s in optimized_schedule}
        
        updated = 0
        for metric in rankings:
            for item in rankings[metric]:
                sname = item['song_name']
                if sname in ml_map:
                    pred = ml_map[sname]
                    if 'ml_predictions' not in item: item['ml_predictions'] = {}
                    
                    item['ml_predictions']['optimal_posting_datetime'] = pred.get('optimal_posting_datetime', '')
                    item['ml_predictions']['predicted_view_count'] = pred.get('predicted_view_count', 0)
                    updated += 1
                    
        with open('rankings.json', 'w', encoding='utf-8') as f:
            json.dump(rankings, f, ensure_ascii=False, indent=2)
            
        print(f"Updated {updated} entries in rankings.json")
        
    except Exception as e:
        print(f"Error in ML/RL optimization: {e}")
        import traceback
        traceback.print_exc()
