"""
ML視聴数予測モジュール
Deep Learningを使用してYouTube動画の視聴数を予測
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any
import datetime
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor
import joblib

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("警告: TensorFlowが利用できません。scikit-learnのGradientBoostingRegressorを使用します。")


class ViewCountPredictor:
    """視聴数予測モデル"""

    def __init__(self, input_dim: int = 40):
        """初期化

        Args:
            input_dim: 入力特徴量の次元数
        """
        self.input_dim = input_dim
        self.model = None
        self.scaler = StandardScaler()
        self.history = None

    def build_model(self) -> keras.Model:
        """ニューラルネットワークモデルを構築

        Returns:
            Kerasモデル
        """
        if not TF_AVAILABLE:
            raise ImportError("TensorFlowがインストールされていません")

        # 入力層
        inputs = layers.Input(shape=(self.input_dim,), name='features')

        # 第1層: Dense + Dropout + BatchNorm
        x = layers.Dense(128, activation='relu',
                        kernel_regularizer=keras.regularizers.l2(0.01))(inputs)
        x = layers.Dropout(0.3)(x)
        x = layers.BatchNormalization()(x)

        # 第2層: Dense + Dropout + BatchNorm
        x = layers.Dense(64, activation='relu',
                        kernel_regularizer=keras.regularizers.l2(0.01))(x)
        x = layers.Dropout(0.2)(x)
        x = layers.BatchNormalization()(x)

        # 第3層: Dense
        x = layers.Dense(32, activation='relu')(x)

        # 出力層1: 視聴数予測（対数スケール）
        view_output = layers.Dense(1, activation='linear', name='views')(x)

        # 信頼度スコア用の分岐
        confidence_branch = layers.Dense(16, activation='relu')(x)
        confidence_output = layers.Dense(1, activation='sigmoid', name='confidence')(confidence_branch)

        # モデル構築
        model = keras.Model(inputs=inputs, outputs=[view_output, confidence_output])

        # コンパイル
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss={
                'views': 'mean_squared_logarithmic_error',  # MSLEでスケール不変
                'confidence': 'binary_crossentropy'
            },
            loss_weights={'views': 1.0, 'confidence': 0.1},
            metrics={
                'views': ['mae', 'mse'],
                'confidence': 'accuracy'
            }
        )

        return model

    def _train_sklearn(self, X: pd.DataFrame, y: np.ndarray,
                      use_augmentation: bool = True,
                      verbose: int = 1) -> Dict[str, Any]:
        """scikit-learnを使用してモデルを訓練

        Args:
            X: 特徴量DataFrame
            y: ターゲット配列（視聴数）
            use_augmentation: データ拡張を使用するか
            verbose: 詳細度

        Returns:
            訓練履歴
        """
        if verbose:
            print("\n⚠ TensorFlowが利用できないため、GradientBoostingRegressorを使用します")

        # 特徴量を正規化
        X_scaled = self.scaler.fit_transform(X.values)

        # データ拡張
        if use_augmentation and len(X_scaled) < 1000:
            if verbose:
                print(f"データ拡張を実行: {len(X_scaled)}サンプル → ", end='')
            X_scaled, y = self.augment_data(X_scaled, y, augmentation_factor=5)
            if verbose:
                print(f"{len(X_scaled)}サンプル")

        # 対数変換（視聴数）
        y_log = np.log1p(y)

        # 信頼度ラベル（高視聴数 = 高信頼）
        y_confidence = (y > np.median(y)).astype(float)

        # 2つの出力を結合
        y_combined = np.column_stack([y_log, y_confidence])

        # GradientBoostingRegressorモデルを構築
        self.model = MultiOutputRegressor(
            GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42,
                verbose=verbose
            )
        )

        # 訓練
        if verbose:
            print(f"\n訓練開始: {len(X_scaled)}サンプル")

        self.model.fit(X_scaled, y_combined)

        # 簡単な評価
        train_pred = self.model.predict(X_scaled)
        train_mae = np.mean(np.abs(np.expm1(train_pred[:, 0]) - y))

        if verbose:
            print(f"\n訓練完了:")
            print(f"  Training MAE: {train_mae:,.0f}")

        self.history = {'train_mae': train_mae}
        return self.history

    def augment_data(self, X: np.ndarray, y: np.ndarray,
                    augmentation_factor: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """データ拡張を実行

        Args:
            X: 特徴量配列
            y: ターゲット配列
            augmentation_factor: 拡張倍率

        Returns:
            (拡張された特徴量, 拡張されたターゲット)
        """
        augmented_X = [X]
        augmented_y = [y]

        for _ in range(augmentation_factor - 1):
            # 時間ジッタリング（±3時間）
            X_aug = X.copy()
            # hourカラムにノイズを追加（存在する場合）
            if X.shape[1] > 0:
                hour_noise = np.random.uniform(-3, 3, X.shape[0])
                # 最初のカラムをhourと仮定
                X_aug[:, 0] = np.clip(X_aug[:, 0] + hour_noise, 0, 23)

            # 視聴数に±5%のノイズを追加
            y_aug = y * np.random.uniform(0.95, 1.05, len(y))

            augmented_X.append(X_aug)
            augmented_y.append(y_aug)

        return np.vstack(augmented_X), np.concatenate(augmented_y)

    def train(self, X: pd.DataFrame, y: np.ndarray,
             validation_split: float = 0.2,
             epochs: int = 100,
             batch_size: int = 32,
             use_augmentation: bool = True,
             verbose: int = 1) -> Dict[str, Any]:
        """モデルを訓練

        Args:
            X: 特徴量DataFrame
            y: ターゲット配列（視聴数）
            validation_split: 検証データの割合
            epochs: エポック数
            batch_size: バッチサイズ
            use_augmentation: データ拡張を使用するか
            verbose: 詳細度

        Returns:
            訓練履歴
        """
        # TensorFlowがない場合はscikit-learnを使用
        if not TF_AVAILABLE:
            return self._train_sklearn(X, y, use_augmentation, verbose)

        # 特徴量を正規化
        X_scaled = self.scaler.fit_transform(X.values)

        # データ拡張
        if use_augmentation and len(X_scaled) < 1000:
            print(f"データ拡張を実行: {len(X_scaled)}サンプル → ", end='')
            X_scaled, y = self.augment_data(X_scaled, y, augmentation_factor=5)
            print(f"{len(X_scaled)}サンプル")

        # 対数変換（視聴数）
        y_log = np.log1p(y)

        # 信頼度ラベル（高視聴数 = 高信頼）
        y_confidence = (y > np.median(y)).astype(float)

        # モデル構築
        self.input_dim = X_scaled.shape[1]
        self.model = self.build_model()

        if verbose:
            print("\nモデルアーキテクチャ:")
            self.model.summary()

        # Early Stopping
        early_stopping = keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=20,
            restore_best_weights=True,
            verbose=verbose
        )

        # ReduceLROnPlateau
        reduce_lr = keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=10,
            min_lr=1e-6,
            verbose=verbose
        )

        # 訓練
        print(f"\n訓練開始: {len(X_scaled)}サンプル")
        history = self.model.fit(
            X_scaled,
            {'views': y_log, 'confidence': y_confidence},
            validation_split=validation_split,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[early_stopping, reduce_lr],
            verbose=verbose
        )

        self.history = history.history

        # 評価メトリクスを表示
        if verbose:
            final_loss = history.history['val_loss'][-1]
            final_views_mae = history.history['val_views_mae'][-1]
            print(f"\n訓練完了:")
            print(f"  Validation Loss: {final_loss:.4f}")
            print(f"  Validation MAE: {final_views_mae:.4f}")

        return self.history

    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """視聴数を予測

        Args:
            X: 特徴量DataFrame

        Returns:
            (予測視聴数, 信頼度スコア)
        """
        if self.model is None:
            raise ValueError("モデルが訓練されていません。先にtrain()を実行してください。")

        # 正規化
        X_scaled = self.scaler.transform(X.values)

        # TensorFlowモデルかscikit-learnモデルかで分岐
        if TF_AVAILABLE and hasattr(self.model, 'predict') and callable(getattr(self.model, 'predict')):
            try:
                # TensorFlowモデル
                pred_log, pred_confidence = self.model.predict(X_scaled, verbose=0)
                pred_views = np.expm1(pred_log.flatten())
                pred_confidence = pred_confidence.flatten()
            except:
                # sklearn MultiOutputRegressor
                predictions = self.model.predict(X_scaled)
                pred_views = np.expm1(predictions[:, 0])
                pred_confidence = predictions[:, 1]
        else:
            # sklearn MultiOutputRegressor
            predictions = self.model.predict(X_scaled)
            pred_views = np.expm1(predictions[:, 0])
            pred_confidence = predictions[:, 1]

        return pred_views, pred_confidence

    def save(self, model_path: str = 'models/view_predictor.pkl',
            scaler_path: str = 'models/view_scaler.pkl'):
        """モデルを保存

        Args:
            model_path: モデルの保存先
            scaler_path: スケーラーの保存先
        """
        import os
        os.makedirs('models', exist_ok=True)

        if self.model:
            # TensorFlowモデルかscikit-learnモデルかで分岐
            if TF_AVAILABLE and hasattr(self.model, 'save'):
                try:
                    self.model.save(model_path.replace('.pkl', '.h5'))
                    print(f"モデルを保存: {model_path.replace('.pkl', '.h5')}")
                except:
                    joblib.dump(self.model, model_path)
                    print(f"モデルを保存: {model_path}")
            else:
                joblib.dump(self.model, model_path)
                print(f"モデルを保存: {model_path}")

        joblib.dump(self.scaler, scaler_path)
        print(f"スケーラーを保存: {scaler_path}")

    def load(self, model_path: str = 'models/view_predictor.pkl',
            scaler_path: str = 'models/view_scaler.pkl'):
        """モデルを読み込み

        Args:
            model_path: モデルのパス
            scaler_path: スケーラーのパス
        """
        import os

        # .h5ファイルが存在する場合はTensorFlowモデルとして読み込み
        h5_path = model_path.replace('.pkl', '.h5')
        if TF_AVAILABLE and os.path.exists(h5_path):
            self.model = keras.models.load_model(h5_path)
            print(f"モデルを読み込み: {h5_path}")
        elif os.path.exists(model_path):
            self.model = joblib.load(model_path)
            print(f"モデルを読み込み: {model_path}")
        else:
            raise FileNotFoundError(f"モデルファイルが見つかりません: {model_path}")

        self.scaler = joblib.load(scaler_path)
        print(f"スケーラーを読み込み: {scaler_path}")


def train_view_predictor(X: pd.DataFrame, y: np.ndarray,
                        epochs: int = 100,
                        validation_split: float = 0.2) -> ViewCountPredictor:
    """View Predictorを訓練（便利関数）

    Args:
        X: 特徴量DataFrame
        y: ターゲット配列
        epochs: エポック数
        validation_split: 検証データの割合

    Returns:
        訓練済みViewCountPredictor
    """
    predictor = ViewCountPredictor(input_dim=X.shape[1])

    predictor.train(
        X, y,
        epochs=epochs,
        validation_split=validation_split,
        use_augmentation=True,
        verbose=1
    )

    return predictor


def cross_validate(X: pd.DataFrame, y: np.ndarray,
                  n_splits: int = 5) -> List[float]:
    """時系列クロスバリデーション

    Args:
        X: 特徴量DataFrame
        y: ターゲット配列
        n_splits: 分割数

    Returns:
        各分割のMAEスコアリスト
    """

    tscv = TimeSeriesSplit(n_splits=n_splits)
    scores = []

    print(f"\n時系列クロスバリデーション ({n_splits} splits):")

    for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
        print(f"\nFold {fold}/{n_splits}")

        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        predictor = ViewCountPredictor(input_dim=X.shape[1])
        predictor.train(X_train, y_train, validation_split=0, epochs=50, verbose=0)

        pred_views, _ = predictor.predict(X_val)
        mae = np.mean(np.abs(pred_views - y_val))
        scores.append(mae)

        print(f"  MAE: {mae:,.0f}")

    print(f"\n平均MAE: {np.mean(scores):,.0f} ± {np.std(scores):,.0f}")
    return scores


def main():
    """テスト用メイン関数"""
    from feature_engineering import FeatureEngineer
    import json

    print("="*60)
    print("ML視聴数予測 - テスト")
    print("="*60)

    # サンプルデータ生成
    np.random.seed(42)
    n_samples = 100

    # ダミー特徴量
    X = pd.DataFrame({
        'hour': np.random.randint(0, 24, n_samples),
        'is_weekend': np.random.randint(0, 2, n_samples),
        'is_evening': np.random.randint(0, 2, n_samples),
        'has_vocaloid_tag': np.random.randint(0, 2, n_samples),
        'log_view_count': np.random.normal(10, 2, n_samples),
        'engagement_rate': np.random.uniform(0, 0.05, n_samples),
    })

    # ダミーターゲット（視聴数）
    y = np.exp(X['log_view_count'] + np.random.normal(0, 0.5, n_samples)) * 10000

    print(f"\nサンプルデータ: {len(X)}件")
    print(f"特徴量数: {X.shape[1]}")
    print(f"視聴数範囲: {y.min():,.0f} - {y.max():,.0f}")

    # モデル訓練
    print("\n" + "-"*60)
    print("モデル訓練")
    print("-"*60)

    predictor = train_view_predictor(X, y, epochs=50, validation_split=0.2)

    # 予測
    print("\n" + "-"*60)
    print("予測テスト")
    print("-"*60)

    X_test = X.head(5)
    y_test = y[:5]

    pred_views, pred_confidence = predictor.predict(X_test)

    print("\n予測結果:")
    for i in range(len(X_test)):
        print(f"  実際: {y_test[i]:>10,.0f} | 予測: {pred_views[i]:>10,.0f} | 信頼度: {pred_confidence[i]:.2f}")

    # モデル保存
    print("\n" + "-"*60)
    print("モデル保存")
    print("-"*60)
    predictor.save()

    print("\n✅ テスト完了")


if __name__ == '__main__':
    main()
