"""
RLスケジューリング最適化モジュール
Reinforcement Learningを使用して投稿スケジュールを最適化
"""

import numpy as np
import datetime
from typing import Dict, List, Tuple, Any
import pandas as pd

try:
    import torch
    import torch.nn as nn
    from torch.distributions import Normal
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("警告: PyTorchが利用できません。pip install torch>=2.0.0 を実行してください。")


class ActorCriticNetwork(nn.Module):
    """Actor-Criticネットワーク（PPO用）"""

    def __init__(self, state_dim: int, action_dim: int):
        """初期化

        Args:
            state_dim: 状態空間の次元数
            action_dim: 行動空間の次元数
        """
        super().__init__()

        # 共有層
        self.shared = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU()
        )

        # Actor（方策）
        self.actor_mean = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim)
        )
        # 対数標準偏差（学習可能なパラメータ）
        self.actor_logstd = nn.Parameter(torch.zeros(action_dim))

        # Critic（価値関数）
        self.critic = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )

    def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """フォワードパス

        Args:
            state: 状態テンソル

        Returns:
            (行動平均, 行動標準偏差, 状態価値)
        """
        shared = self.shared(state)

        action_mean = self.actor_mean(shared)
        action_std = torch.exp(self.actor_logstd)
        value = self.critic(shared)

        return action_mean, action_std, value

    def get_action(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """行動をサンプリング

        Args:
            state: 状態テンソル

        Returns:
            (行動, ログ確率, 状態価値)
        """
        action_mean, action_std, value = self(state)

        # 正規分布から行動をサンプリング
        dist = Normal(action_mean, action_std)
        action = dist.sample()
        log_prob = dist.log_prob(action).sum(dim=-1)

        return action, log_prob, value


class PPOAgent:
    """PPOエージェント"""

    def __init__(self, state_dim: int, action_dim: int,
                 lr: float = 3e-4, gamma: float = 0.99,
                 epsilon_clip: float = 0.2, K_epochs: int = 4):
        """初期化

        Args:
            state_dim: 状態空間の次元数
            action_dim: 行動空間の次元数
            lr: 学習率
            gamma: 割引率
            epsilon_clip: PPOクリッピング閾値
            K_epochs: 更新エポック数
        """
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorchがインストールされていません")

        self.gamma = gamma
        self.epsilon_clip = epsilon_clip
        self.K_epochs = K_epochs

        self.policy = ActorCriticNetwork(state_dim, action_dim)
        self.optimizer = torch.optim.Adam(self.policy.parameters(), lr=lr)

        self.old_policy = ActorCriticNetwork(state_dim, action_dim)
        self.old_policy.load_state_dict(self.policy.state_dict())

    def select_action(self, state: np.ndarray) -> Tuple[np.ndarray, float, float]:
        """行動を選択

        Args:
            state: 状態配列

        Returns:
            (行動, ログ確率, 状態価値)
        """
        state_tensor = torch.FloatTensor(state).unsqueeze(0)

        with torch.no_grad():
            action, log_prob, value = self.old_policy.get_action(state_tensor)

        return action.numpy()[0], log_prob.item(), value.item()

    def update(self, memory: List[Tuple]) -> Dict[str, float]:
        """ポリシーを更新

        Args:
            memory: (state, action, log_prob, reward, value) のリスト

        Returns:
            損失の辞書
        """
        # データを抽出
        states = torch.FloatTensor([m[0] for m in memory])
        actions = torch.FloatTensor([m[1] for m in memory])
        old_log_probs = torch.FloatTensor([m[2] for m in memory])
        rewards = torch.FloatTensor([m[3] for m in memory])
        old_values = torch.FloatTensor([m[4] for m in memory])

        # 割引報酬を計算
        returns = []
        discounted_reward = 0
        for reward in reversed(rewards):
            discounted_reward = reward + self.gamma * discounted_reward
            returns.insert(0, discounted_reward)
        returns = torch.FloatTensor(returns)

        # 正規化
        returns = (returns - returns.mean()) / (returns.std() + 1e-7)

        # K エポック更新
        total_policy_loss = 0
        total_value_loss = 0

        for _ in range(self.K_epochs):
            # 現在のポリシーで評価
            action_means, action_stds, values = self.policy(states)

            # ログ確率を計算
            dist = Normal(action_means, action_stds)
            log_probs = dist.log_prob(actions).sum(dim=-1)

            # Ratio
            ratios = torch.exp(log_probs - old_log_probs.detach())

            # Advantage
            advantages = returns - old_values.detach()

            # PPO損失
            surr1 = ratios * advantages
            surr2 = torch.clamp(ratios, 1 - self.epsilon_clip, 1 + self.epsilon_clip) * advantages
            policy_loss = -torch.min(surr1, surr2).mean()

            # 価値関数損失
            value_loss = nn.MSELoss()(values.squeeze(), returns)

            # 合計損失
            loss = policy_loss + 0.5 * value_loss

            # 最適化
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

            total_policy_loss += policy_loss.item()
            total_value_loss += value_loss.item()

        # 古いポリシーを更新
        self.old_policy.load_state_dict(self.policy.state_dict())

        return {
            'policy_loss': total_policy_loss / self.K_epochs,
            'value_loss': total_value_loss / self.K_epochs
        }


class SchedulingEnvironment:
    """投稿スケジューリング環境"""

    def __init__(self, songs_data: List[Dict[str, Any]],
                 view_predictor: Any = None):
        """初期化

        Args:
            songs_data: 曲データのリスト
            view_predictor: 視聴数予測モデル
        """
        self.songs_data = songs_data
        self.view_predictor = view_predictor

        self.current_song_idx = 0
        self.schedule = []  # (song, posting_datetime) のリスト

    def reset(self) -> np.ndarray:
        """環境をリセット

        Returns:
            初期状態
        """
        self.current_song_idx = 0
        self.schedule = []
        return self._get_state()

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict]:
        """1ステップ実行

        Args:
            action: [date_offset(0-90), hour(0-23)]の配列

        Returns:
            (次の状態, 報酬, 終了フラグ, 情報辞書)
        """
        if self.current_song_idx >= len(self.songs_data):
            return self._get_state(), 0, True, {}

        song = self.songs_data[self.current_song_idx]

        # 行動を解釈
        date_offset = int(np.clip(action[0], 0, 90))
        hour = int(np.clip(action[1], 0, 23))

        # release_date制約を処理
        release_date_str = song.get('release_date', '')
        posting_datetime = self._calculate_posting_datetime(
            release_date_str, date_offset, hour
        )

        # 報酬を計算
        reward = self._calculate_reward(song, posting_datetime)

        # スケジュールに追加
        self.schedule.append((song, posting_datetime))
        self.current_song_idx += 1

        # 次の状態
        next_state = self._get_state()
        done = (self.current_song_idx >= len(self.songs_data))

        return next_state, reward, done, {'posting_datetime': posting_datetime}

    def _calculate_posting_datetime(self, release_date_str: str,
                                    date_offset: int, hour: int) -> datetime.datetime:
        """投稿日時を計算

        Args:
            release_date_str: リリース日（YYYY/MM/DD形式）
            date_offset: 日付オフセット
            hour: 時刻

        Returns:
            投稿日時
        """
        today = datetime.datetime.now()

        if release_date_str:
            try:
                release_date = datetime.datetime.strptime(release_date_str, '%Y/%m/%d')

                if release_date.date() >= today.date():
                    # 未来のrelease_date: 日付固定、時間のみ最適化
                    posting_datetime = release_date.replace(hour=hour, minute=0, second=0)
                else:
                    # 過去のrelease_date: 完全に自由
                    posting_datetime = today + datetime.timedelta(days=date_offset)
                    posting_datetime = posting_datetime.replace(hour=hour, minute=0, second=0)
            except:
                # パースエラー: デフォルト
                posting_datetime = today + datetime.timedelta(days=date_offset)
                posting_datetime = posting_datetime.replace(hour=hour, minute=0, second=0)
        else:
            # release_dateなし: 完全に自由
            posting_datetime = today + datetime.timedelta(days=date_offset)
            posting_datetime = posting_datetime.replace(hour=hour, minute=0, second=0)

        return posting_datetime

    def _calculate_reward(self, song: Dict[str, Any],
                         posting_datetime: datetime.datetime) -> float:
        """報酬を計算

        Args:
            song: 曲データ
            posting_datetime: 投稿予定日時

        Returns:
            報酬値
        """
        # 1. 予測視聴数（メイン報酬）
        if self.view_predictor:
            # 実際の予測を使用（未実装の場合はダミー）
            predicted_views = song.get('view_count', 0) * 0.8  # プレースホルダー
        else:
            predicted_views = song.get('view_count', 0) * 0.8

        view_reward = predicted_views / 100000  # スケーリング

        # 2. 投稿間隔ペナルティ
        interval_penalty = self._interval_penalty(posting_datetime)

        # 3. 視聴者疲労ペナルティ（週あたり投稿数）
        fatigue_penalty = self._fatigue_penalty(posting_datetime)

        # 4. 制約違反ペナルティ
        constraint_penalty = self._constraint_violation(song, posting_datetime)

        # 総報酬
        reward = view_reward - 0.2 * interval_penalty - 0.1 * fatigue_penalty - 10.0 * constraint_penalty

        return reward

    def _interval_penalty(self, posting_datetime: datetime.datetime) -> float:
        """投稿間隔ペナルティを計算"""
        if not self.schedule:
            return 0

        # 最後の投稿との間隔
        last_datetime = self.schedule[-1][1]
        hours_diff = abs((posting_datetime - last_datetime).total_seconds() / 3600)

        # 48時間以内はペナルティ
        if hours_diff < 48:
            return (48 - hours_diff) / 48
        return 0

    def _fatigue_penalty(self, posting_datetime: datetime.datetime) -> float:
        """視聴者疲労ペナルティを計算（週あたり3本以上でペナルティ）"""
        # 同じ週の投稿数をカウント
        week_start = posting_datetime - datetime.timedelta(days=posting_datetime.weekday())
        week_end = week_start + datetime.timedelta(days=7)

        week_count = sum(1 for _, dt in self.schedule
                        if week_start <= dt < week_end)

        # 週3本を超えるとペナルティ
        if week_count >= 3:
            return (week_count - 2) / 3
        return 0

    def _constraint_violation(self, song: Dict[str, Any],
                             posting_datetime: datetime.datetime) -> float:
        """制約違反を検出"""
        release_date_str = song.get('release_date', '')

        if not release_date_str:
            return 0

        try:
            release_date = datetime.datetime.strptime(release_date_str, '%Y/%m/%d')
            today = datetime.datetime.now()

            # release_dateが未来の場合、その日に投稿する必要がある
            if release_date.date() >= today.date():
                if posting_datetime.date() != release_date.date():
                    return 1.0  # 重大な違反
        except:
            pass

        return 0

    def _get_state(self) -> np.ndarray:
        """現在の状態を取得

        Returns:
            状態ベクトル
        """
        # 簡易実装: 現在の曲インデックスとスケジュール情報
        state = np.zeros(10)  # プレースホルダー

        if self.current_song_idx < len(self.songs_data):
            song = self.songs_data[self.current_song_idx]
            state[0] = self.current_song_idx / len(self.songs_data)
            state[1] = song.get('view_count', 0) / 1e7
            state[2] = len(self.schedule) / len(self.songs_data)

        return state


def optimize_schedule(songs_data: List[Dict[str, Any]],
                     view_predictor: Any = None,
                     num_episodes: int = 500) -> List[Tuple[Dict, datetime.datetime, float, float]]:
    """スケジュールを最適化

    Args:
        songs_data: 曲データのリスト
        view_predictor: 視聴数予測モデル
        num_episodes: エピソード数

    Returns:
        (song, posting_datetime, predicted_views, confidence) のリスト
    """
    if not TORCH_AVAILABLE:
        print("警告: PyTorchが利用できません。ルールベーススケジューリングにフォールバック")
        return _fallback_schedule(songs_data)

    print("\nRLスケジューリング最適化を開始...")

    env = SchedulingEnvironment(songs_data, view_predictor)
    agent = PPOAgent(state_dim=10, action_dim=2)

    best_schedule = []
    best_reward = float('-inf')

    for episode in range(num_episodes):
        state = env.reset()
        memory = []
        episode_reward = 0

        while True:
            action, log_prob, value = agent.select_action(state)
            next_state, reward, done, info = env.step(action)

            memory.append((state, action, log_prob, reward, value))
            episode_reward += reward

            state = next_state

            if done:
                break

        # ポリシー更新
        agent.update(memory)

        # ベストスケジュールを保存
        if episode_reward > best_reward:
            best_reward = episode_reward
            best_schedule = env.schedule.copy()

        if (episode + 1) % 50 == 0:
            print(f"Episode {episode + 1}/{num_episodes}: Reward = {episode_reward:.2f}, Best = {best_reward:.2f}")

    # 結果を整形
    optimized_schedule = []
    for song, posting_datetime in best_schedule:
        optimized_schedule.append((
            song,
            posting_datetime,
            song.get('view_count', 0) * 0.8,  # 予測視聴数（プレースホルダー）
            0.75  # 信頼度（プレースホルダー）
        ))

    print(f"\n最適化完了: {len(optimized_schedule)}曲")
    return optimized_schedule


def _fallback_schedule(songs_data: List[Dict[str, Any]]) -> List[Tuple[Dict, datetime.datetime, float, float]]:
    """ルールベーススケジューリング（フォールバック）"""
    print("ルールベーススケジューリングを使用")

    schedule = []
    today = datetime.datetime.now()
    current_date = today

    for song in sorted(songs_data, key=lambda x: x.get('view_count', 0), reverse=True):
        release_date_str = song.get('release_date', '')

        if release_date_str:
            try:
                release_date = datetime.datetime.strptime(release_date_str, '%Y/%m/%d')
                if release_date.date() >= today.date():
                    posting_datetime = release_date.replace(hour=18, minute=0, second=0)
                else:
                    posting_datetime = current_date.replace(hour=18, minute=0, second=0)
                    current_date += datetime.timedelta(days=2)
            except:
                posting_datetime = current_date.replace(hour=18, minute=0, second=0)
                current_date += datetime.timedelta(days=2)
        else:
            posting_datetime = current_date.replace(hour=18, minute=0, second=0)
            current_date += datetime.timedelta(days=2)

        schedule.append((song, posting_datetime, song.get('view_count', 0) * 0.8, 0.75))

    return schedule


def main():
    """テスト用メイン関数"""
    print("="*60)
    print("RLスケジューリング最適化 - テスト")
    print("="*60)

    # サンプルデータ
    sample_songs = [
        {'song_name': 'マシュマロ', 'artist_name': 'DECO*27', 'release_date': '2025/11/22', 'view_count': 15000000},
        {'song_name': 'WATCH ME!', 'artist_name': 'YOASOBI', 'release_date': '2025/09/09', 'view_count': 25000000},
        {'song_name': 'らしさ', 'artist_name': 'Official髭男dism', 'release_date': '2025/10/14', 'view_count': 12000000},
    ]

    # 最適化実行
    schedule = optimize_schedule(sample_songs, num_episodes=100)

    print("\n最適化されたスケジュール:")
    for song, dt, pred_views, conf in schedule:
        print(f"  {dt.strftime('%Y/%m/%d %H:%M')} - {song['song_name']} (予測: {pred_views:,.0f} views, 信頼度: {conf:.2f})")


if __name__ == '__main__':
    main()
