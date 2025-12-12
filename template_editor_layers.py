import sys
import json
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QPushButton, QLabel, QSpinBox,
                               QFileDialog, QListWidget, QMessageBox, QListWidgetItem,
                               QCheckBox, QComboBox)
from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QPainter, QPixmap, QPen, QColor, QFont, QBrush


class Layer:
    """レイヤークラス"""

    def __init__(self, layer_type, name, x=0, y=0, w=None, h=None, **kwargs):
        self.type = layer_type  # 'background', 'video', 'image', 'text'
        self.name = name
        self.rect = QRect(x, y, w or 100, h or 100)
        self.visible = True
        self.path = kwargs.get('path', '')
        self.lines = kwargs.get('lines', 1)

    def to_dict(self):
        """辞書形式に変換"""
        data = {
            'type': self.type,
            'name': self.name,
            'x': self.rect.x(),
            'y': self.rect.y(),
            'w': self.rect.width(),
            'h': self.rect.height(),
            'visible': self.visible
        }
        if self.path:
            data['path'] = self.path
        if self.type == 'text':
            data['lines'] = self.lines
        return data


class ResizableLayer(QWidget):
    """リサイズ・移動可能なレイヤー"""

    HANDLE_SIZE = 10

    def __init__(self, layer, parent=None):
        super().__init__(parent)
        self.layer = layer
        self.dragging = False
        self.resizing = False
        self.resize_corner = None
        self.drag_start = QPoint()
        self.setMouseTracking(True)

    def paint(self, painter, scale=1.0):
        """レイヤーを描画"""
        if not self.layer.visible:
            return

        rect = self.layer.rect

        # レイヤータイプに応じた色
        colors = {
            'background': QColor(100, 200, 100),
            'video': QColor(100, 150, 255),
            'image': QColor(255, 150, 100),
            'text': QColor(255, 100, 100)
        }
        color = colors.get(self.layer.type, QColor(200, 200, 200))

        # 実際の画像・動画がある場合はプレビュー表示
        import os
        if self.layer.path and os.path.exists(self.layer.path):
            if self.layer.type in ['background', 'image']:
                # 画像を読み込んでプレビュー
                pixmap = QPixmap(self.layer.path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        rect.width(), rect.height(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    # 中央配置
                    x = rect.x() + (rect.width() - scaled_pixmap.width()) // 2
                    y = rect.y() + (rect.height() - scaled_pixmap.height()) // 2

                    # PNG画像のアルファチャンネルを正しく扱うために合成モードを設定
                    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                    painter.drawPixmap(x, y, scaled_pixmap)

                    # 枠のみ描画
                    painter.setPen(QPen(color, 2))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawRect(rect)
                else:
                    # 画像読み込み失敗時は通常の色つき四角
                    self._draw_colored_rect(painter, rect, color)
            elif self.layer.type == 'video':
                # 動画は青い半透明矩形 + アイコン表示
                self._draw_colored_rect(painter, rect, color)
                painter.setPen(QPen(Qt.white, 2))
                font = QFont("Arial", 24, QFont.Bold)
                painter.setFont(font)
                painter.drawText(rect, Qt.AlignCenter, "▶")
        else:
            # パスがない場合は通常の色つき四角
            self._draw_colored_rect(painter, rect, color)

        # ラベルを描画
        painter.setPen(QPen(color.darker(150)))
        font = QFont("Arial", 12, QFont.Bold)
        painter.setFont(font)

        label_text = f"{self.layer.name}"
        if self.layer.type == 'text':
            label_text += f" (lines: {self.layer.lines})"

        painter.drawText(rect.x(), rect.y() - 5, label_text)

        # リサイズハンドルを描画
        handles = self.get_resize_handles()
        painter.setBrush(QBrush(color))
        for handle in handles:
            painter.drawRect(handle)

    def _draw_colored_rect(self, painter, rect, color):
        """色つき矩形を描画（ヘルパー関数）"""
        # 枠を描画
        painter.setPen(QPen(color, 2))
        painter.drawRect(rect)

        # 半透明の塗りつぶし
        color.setAlpha(50)
        painter.setBrush(QBrush(color))
        painter.drawRect(rect)

    def get_resize_handles(self):
        """リサイズハンドルの位置を取得"""
        r = self.layer.rect
        s = self.HANDLE_SIZE
        return [
            QRect(r.right() - s, r.bottom() - s, s, s),  # 右下
            QRect(r.left(), r.bottom() - s, s, s),       # 左下
            QRect(r.right() - s, r.top(), s, s),         # 右上
            QRect(r.left(), r.top(), s, s)               # 左上
        ]

    def get_resize_corner_at(self, pos):
        """指定位置のリサイズコーナーを取得"""
        handles = self.get_resize_handles()
        corners = ['br', 'bl', 'tr', 'tl']
        for i, handle in enumerate(handles):
            if handle.contains(pos):
                return corners[i]
        return None

    def contains_point(self, pos):
        """ポイントが枠内にあるか"""
        return self.layer.rect.contains(pos)


class LayerCanvas(QWidget):
    """レイヤー対応キャンバス"""

    def __init__(self, width=1080, height=1920, parent=None):
        super().__init__(parent)
        self.canvas_width = width
        self.canvas_height = height
        self.layers = []
        self.selected_layer = None
        self.scale = 1.0

        # キャンバスのアスペクト比に応じて最小サイズを設定
        if height > width:
            # 縦長の場合
            self.setMinimumSize(400, 700)
        else:
            # 横長の場合
            self.setMinimumSize(600, 400)
        self.setMouseTracking(True)

    def add_layer(self, layer):
        """レイヤーを追加"""
        resizable = ResizableLayer(layer)
        self.layers.append(resizable)
        self.update()
        return resizable

    def remove_layer(self, layer_widget):
        """レイヤーを削除"""
        if layer_widget in self.layers:
            self.layers.remove(layer_widget)
            self.update()

    def move_layer_up(self, layer_widget):
        """レイヤーをリスト上で上に移動（描画順を前に = 背面へ）"""
        if layer_widget in self.layers:
            idx = self.layers.index(layer_widget)
            if idx > 0:
                self.layers[idx], self.layers[idx - 1] = self.layers[idx - 1], self.layers[idx]
                self.update()

    def move_layer_down(self, layer_widget):
        """レイヤーをリスト上で下に移動（描画順を後ろに = 前面へ）"""
        if layer_widget in self.layers:
            idx = self.layers.index(layer_widget)
            if idx < len(self.layers) - 1:
                self.layers[idx], self.layers[idx + 1] = self.layers[idx + 1], self.layers[idx]
                self.update()

    def calculate_scale(self):
        """キャンバスのスケールを計算"""
        widget_ratio = self.width() / self.height()
        canvas_ratio = self.canvas_width / self.canvas_height

        if widget_ratio > canvas_ratio:
            return self.height() / self.canvas_height
        else:
            return self.width() / self.canvas_width

    def get_scaled_rect(self):
        """スケーリングされたキャンバスの矩形を取得"""
        scale = self.calculate_scale()
        scaled_w = int(self.canvas_width * scale)
        scaled_h = int(self.canvas_height * scale)
        offset_x = (self.width() - scaled_w) // 2
        offset_y = (self.height() - scaled_h) // 2
        return QRect(offset_x, offset_y, scaled_w, scaled_h)

    def widget_to_canvas_pos(self, widget_pos):
        """ウィジェット座標をキャンバス座標に変換"""
        scale = self.calculate_scale()
        canvas_rect = self.get_scaled_rect()
        x = int((widget_pos.x() - canvas_rect.x()) / scale)
        y = int((widget_pos.y() - canvas_rect.y()) / scale)
        return QPoint(x, y)

    def canvas_to_widget_rect(self, canvas_rect):
        """キャンバス座標をウィジェット座標に変換"""
        scale = self.calculate_scale()
        widget_canvas = self.get_scaled_rect()
        return QRect(
            int(canvas_rect.x() * scale + widget_canvas.x()),
            int(canvas_rect.y() * scale + widget_canvas.y()),
            int(canvas_rect.width() * scale),
            int(canvas_rect.height() * scale)
        )

    def paintEvent(self, event):
        """描画イベント"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 背景を描画
        painter.fillRect(self.rect(), QColor(40, 40, 40))

        # キャンバスを描画
        canvas_rect = self.get_scaled_rect()
        painter.fillRect(canvas_rect, QColor(255, 255, 255))

        # レイヤーを描画（下から順に）
        for layer_widget in self.layers:
            saved_rect = layer_widget.layer.rect
            layer_widget.layer.rect = self.canvas_to_widget_rect(saved_rect)
            layer_widget.paint(painter)
            layer_widget.layer.rect = saved_rect

    def mousePressEvent(self, event):
        """マウス押下イベント"""
        if event.button() == Qt.LeftButton:
            canvas_pos = self.widget_to_canvas_pos(event.pos())

            # レイヤーを上から順にチェック（描画順の逆）
            for layer_widget in reversed(self.layers):
                corner = layer_widget.get_resize_corner_at(canvas_pos)
                if corner:
                    self.selected_layer = layer_widget
                    layer_widget.resizing = True
                    layer_widget.resize_corner = corner
                    layer_widget.drag_start = canvas_pos
                    return

            for layer_widget in reversed(self.layers):
                if layer_widget.contains_point(canvas_pos):
                    self.selected_layer = layer_widget
                    layer_widget.dragging = True
                    layer_widget.drag_start = canvas_pos
                    break

    def mouseMoveEvent(self, event):
        """マウス移動イベント"""
        canvas_pos = self.widget_to_canvas_pos(event.pos())

        if self.selected_layer:
            if self.selected_layer.dragging:
                delta = canvas_pos - self.selected_layer.drag_start
                self.selected_layer.layer.rect.translate(delta)
                self.selected_layer.drag_start = canvas_pos
                self.update()

            elif self.selected_layer.resizing:
                corner = self.selected_layer.resize_corner
                rect = self.selected_layer.layer.rect

                if corner == 'br':
                    rect.setBottomRight(canvas_pos)
                elif corner == 'bl':
                    rect.setBottomLeft(canvas_pos)
                elif corner == 'tr':
                    rect.setTopRight(canvas_pos)
                elif corner == 'tl':
                    rect.setTopLeft(canvas_pos)

                if rect.width() < 50:
                    rect.setWidth(50)
                if rect.height() < 50:
                    rect.setHeight(50)

                self.update()

    def mouseReleaseEvent(self, event):
        """マウス解放イベント"""
        if self.selected_layer:
            self.selected_layer.dragging = False
            self.selected_layer.resizing = False
            self.selected_layer.resize_corner = None
            self.selected_layer = None

    def export_template(self):
        """テンプレートをJSONとしてエクスポート（レイヤー順序を保持）"""
        # レイヤー順序を保持した配列として保存
        layers_array = []
        text_areas = {}

        for layer_widget in self.layers:
            layer = layer_widget.layer
            layer_dict = layer.to_dict()

            if layer.type == 'text':
                # テキストエリアは別途保存（後方互換性のため）
                text_area_dict = {
                    'x': layer.rect.x(),
                    'y': layer.rect.y(),
                    'w': layer.rect.width(),
                    'h': layer.rect.height(),
                    'lines': layer.lines
                }
                # フォント情報があれば追加
                if hasattr(layer, 'font_path') and layer.font_path:
                    text_area_dict['font'] = layer.font_path
                text_areas[layer.name] = text_area_dict
            else:
                # background, video, image レイヤーは順序を保持した配列に追加
                layers_array.append(layer_dict)

        template = {
            'canvas': {
                'w': self.canvas_width,
                'h': self.canvas_height
            },
            'layers_ordered': layers_array,  # 新形式: 順序を保持した配列
            'text_areas': text_areas,  # テキストエリア（後方互換性）
            'fonts': {
                'primary': 'fonts/RampartOne-Regular.ttf',  # デフォルトフォント
                'secondary': '/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc'
            }
        }

        return template


class LayerEditorWindow(QMainWindow):
    """レイヤーエディタのメインウィンドウ"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("レイヤー対応テンプレートエディタ")
        # 縦長のキャンバス(1080x1920)に合わせてウィンドウサイズを調整
        self.setGeometry(100, 100, 1200, 1000)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        layout = QHBoxLayout(main_widget)

        # キャンバス（縦長なので幅を広めに）
        self.canvas = LayerCanvas(1080, 1920)
        layout.addWidget(self.canvas, stretch=2)

        # サイドパネル
        side_panel = self.create_side_panel()
        layout.addWidget(side_panel, stretch=1)

        # template.jsonが存在する場合は読み込む
        self.load_template_if_exists()

        # フォントリストを初期化
        self.initialize_font_list()

    def create_side_panel(self):
        """サイドパネルを作成"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # タイトル
        title = QLabel("レイヤー管理")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # キャンバスサイズ設定
        layout.addWidget(QLabel("\nキャンバスサイズ:"))
        size_layout = QHBoxLayout()

        layout.addWidget(QLabel("幅:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 4000)
        self.width_spin.setValue(self.canvas.canvas_width)
        self.width_spin.setSingleStep(10)
        self.width_spin.valueChanged.connect(self.on_canvas_size_changed)
        size_layout.addWidget(self.width_spin)

        layout.addWidget(QLabel("高さ:"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(100, 4000)
        self.height_spin.setValue(self.canvas.canvas_height)
        self.height_spin.setSingleStep(10)
        self.height_spin.valueChanged.connect(self.on_canvas_size_changed)
        size_layout.addWidget(self.height_spin)

        layout.addLayout(size_layout)

        # よく使うサイズのプリセット
        preset_layout = QHBoxLayout()
        preset_label = QLabel("プリセット:")
        preset_layout.addWidget(preset_label)

        portrait_btn = QPushButton("縦 1080×1920")
        portrait_btn.clicked.connect(lambda: self.set_canvas_size(1080, 1920))
        preset_layout.addWidget(portrait_btn)

        landscape_btn = QPushButton("横 1920×1080")
        landscape_btn.clicked.connect(lambda: self.set_canvas_size(1920, 1080))
        preset_layout.addWidget(landscape_btn)

        layout.addLayout(preset_layout)

        # レイヤーリスト
        layout.addWidget(QLabel("\nレイヤー一覧:"))
        self.layer_list = QListWidget()
        layout.addWidget(self.layer_list)

        # レイヤー追加ボタン
        add_bg_btn = QPushButton("+ 背景画像レイヤー")
        add_bg_btn.clicked.connect(lambda: self.add_layer('background'))
        layout.addWidget(add_bg_btn)

        add_video_btn = QPushButton("+ 動画レイヤー")
        add_video_btn.clicked.connect(lambda: self.add_layer('video'))
        layout.addWidget(add_video_btn)

        add_img_btn = QPushButton("+ PNGレイヤー")
        add_img_btn.clicked.connect(lambda: self.add_layer('image'))
        layout.addWidget(add_img_btn)

        add_text_btn = QPushButton("+ テキストレイヤー")
        add_text_btn.clicked.connect(lambda: self.add_layer('text'))
        layout.addWidget(add_text_btn)

        # レイヤー操作ボタン
        layout.addWidget(QLabel("\nレイヤー操作:"))

        btn_layout = QHBoxLayout()
        up_btn = QPushButton("↑ 上へ")
        up_btn.clicked.connect(self.move_layer_up)
        btn_layout.addWidget(up_btn)

        down_btn = QPushButton("↓ 下へ")
        down_btn.clicked.connect(self.move_layer_down)
        btn_layout.addWidget(down_btn)
        layout.addLayout(btn_layout)

        remove_btn = QPushButton("削除")
        remove_btn.setStyleSheet("background-color: #f44336; color: white;")
        remove_btn.clicked.connect(self.remove_layer)
        layout.addWidget(remove_btn)

        # 選択レイヤーの詳細設定
        layout.addWidget(QLabel("\n選択レイヤーの設定:"))

        # 位置設定
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("X:"))
        self.x_spin = QSpinBox()
        self.x_spin.setRange(-1000, 5000)
        self.x_spin.valueChanged.connect(self.on_layer_position_changed)
        pos_layout.addWidget(self.x_spin)

        pos_layout.addWidget(QLabel("Y:"))
        self.y_spin = QSpinBox()
        self.y_spin.setRange(-1000, 5000)
        self.y_spin.valueChanged.connect(self.on_layer_position_changed)
        pos_layout.addWidget(self.y_spin)
        layout.addLayout(pos_layout)

        # サイズ設定
        size_layout2 = QHBoxLayout()
        size_layout2.addWidget(QLabel("幅:"))
        self.layer_w_spin = QSpinBox()
        self.layer_w_spin.setRange(10, 5000)
        self.layer_w_spin.valueChanged.connect(self.on_layer_size_changed)
        size_layout2.addWidget(self.layer_w_spin)

        size_layout2.addWidget(QLabel("高さ:"))
        self.layer_h_spin = QSpinBox()
        self.layer_h_spin.setRange(10, 5000)
        self.layer_h_spin.valueChanged.connect(self.on_layer_size_changed)
        size_layout2.addWidget(self.layer_h_spin)
        layout.addLayout(size_layout2)

        # アスペクト比固定チェックボックス
        self.aspect_lock = QCheckBox("アスペクト比を固定")
        self.aspect_lock.setChecked(True)
        layout.addWidget(self.aspect_lock)

        # スケール設定
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("スケール:"))

        # QDoubleSpinBoxに変更して小数点対応
        from PySide6.QtWidgets import QDoubleSpinBox
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(1.0, 500.0)
        self.scale_spin.setValue(100.0)
        self.scale_spin.setDecimals(2)  # 小数点2桁
        self.scale_spin.setSingleStep(0.1)  # 0.1%刻み
        self.scale_spin.setSuffix("%")
        self.scale_spin.valueChanged.connect(self.on_layer_scale_changed)
        scale_layout.addWidget(self.scale_spin)
        layout.addLayout(scale_layout)

        # テキスト行数設定
        layout.addWidget(QLabel("\nテキスト行数:"))
        self.lines_spin = QSpinBox()
        self.lines_spin.setRange(1, 5)
        self.lines_spin.setValue(3)
        self.lines_spin.valueChanged.connect(self.on_lines_changed)
        layout.addWidget(self.lines_spin)

        # フォント選択設定
        layout.addWidget(QLabel("\nフォント:"))
        self.font_combo = QComboBox()
        self.font_combo.currentTextChanged.connect(self.on_font_changed)
        layout.addWidget(self.font_combo)

        # レイヤーリストの選択変更時にも更新
        self.layer_list.currentItemChanged.connect(self.on_layer_selected)

        # ファイル操作ボタン
        layout.addStretch()

        load_btn = QPushButton("template.json を読み込む")
        load_btn.setStyleSheet("font-size: 14px; padding: 8px; background-color: #2196F3; color: white;")
        load_btn.clicked.connect(self.load_template)
        layout.addWidget(load_btn)

        save_btn = QPushButton("template.json を保存")
        save_btn.setStyleSheet("font-size: 16px; padding: 10px; background-color: #4CAF50; color: white;")
        save_btn.clicked.connect(self.save_template)
        layout.addWidget(save_btn)

        # 説明
        info = QLabel("\n色の意味:\n"
                     "• 緑: 背景画像\n"
                     "• 青: 動画\n"
                     "• オレンジ: PNG\n"
                     "• 赤: テキスト")
        info.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(info)

        return panel

    def add_layer(self, layer_type):
        """レイヤーを追加"""
        # レイヤー名を生成
        count = sum(1 for lw in self.canvas.layers if lw.layer.type == layer_type)
        name = f"{layer_type}_{count + 1}"

        # パスを選択
        path = ''
        if layer_type in ['background', 'image']:
            path, _ = QFileDialog.getOpenFileName(
                self, f"{layer_type}を選択", "", "Images (*.png *.jpg *.jpeg)"
            )
            if not path:
                return
        elif layer_type == 'video':
            path, _ = QFileDialog.getOpenFileName(
                self, "動画を選択", "", "Videos (*.mp4 *.mov *.avi)"
            )
            if not path:
                return

        # デフォルト位置とサイズ
        defaults = {
            'background': (0, 0, 1080, 1920),
            'video': (100, 100, 880, 495),  # 16:9
            'image': (200, 600, 680, 680),
            'text': (120, 1200, 840, 400)
        }
        x, y, w, h = defaults[layer_type]

        # レイヤーを作成
        layer = Layer(layer_type, name, x, y, w, h, path=path, lines=3)
        layer_widget = self.canvas.add_layer(layer)

        # リストに追加
        item = QListWidgetItem(f"{name} ({layer_type})")
        item.setData(Qt.UserRole, layer_widget)
        self.layer_list.addItem(item)

        self.update_layer_list()

    def remove_layer(self):
        """選択されたレイヤーを削除"""
        current_item = self.layer_list.currentItem()
        if not current_item:
            return

        layer_widget = current_item.data(Qt.UserRole)
        self.canvas.remove_layer(layer_widget)
        self.layer_list.takeItem(self.layer_list.row(current_item))

    def move_layer_up(self):
        """レイヤーを上に移動"""
        current_item = self.layer_list.currentItem()
        if not current_item:
            return

        layer_widget = current_item.data(Qt.UserRole)
        self.canvas.move_layer_up(layer_widget)
        self.update_layer_list()

    def move_layer_down(self):
        """レイヤーを下に移動"""
        current_item = self.layer_list.currentItem()
        if not current_item:
            return

        layer_widget = current_item.data(Qt.UserRole)
        self.canvas.move_layer_down(layer_widget)
        self.update_layer_list()

    def update_layer_list(self, select_layer_widget=None):
        """レイヤーリストを更新（上から下へ = 下層から上層へ）"""
        # 現在選択されているレイヤーを記憶
        if select_layer_widget is None:
            current_item = self.layer_list.currentItem()
            if current_item:
                select_layer_widget = current_item.data(Qt.UserRole)

        self.layer_list.clear()
        for layer_widget in self.canvas.layers:
            layer = layer_widget.layer
            item = QListWidgetItem(f"{layer.name} ({layer.type})")
            item.setData(Qt.UserRole, layer_widget)
            self.layer_list.addItem(item)

            # 選択を復元
            if layer_widget == select_layer_widget:
                self.layer_list.setCurrentItem(item)

    def on_lines_changed(self, value):
        """テキスト行数が変更された時"""
        current_item = self.layer_list.currentItem()
        if not current_item:
            return

        layer_widget = current_item.data(Qt.UserRole)
        if layer_widget.layer.type == 'text':
            layer_widget.layer.lines = value
            self.canvas.update()

    def on_canvas_size_changed(self):
        """キャンバスサイズが変更された時"""
        new_width = self.width_spin.value()
        new_height = self.height_spin.value()
        self.canvas.canvas_width = new_width
        self.canvas.canvas_height = new_height
        self.canvas.update()

    def set_canvas_size(self, width, height):
        """キャンバスサイズを設定"""
        self.width_spin.setValue(width)
        self.height_spin.setValue(height)

    def on_layer_selected(self, current, previous):
        """レイヤーが選択された時"""
        if not current:
            # 選択なしの場合は無効化
            self.x_spin.setEnabled(False)
            self.y_spin.setEnabled(False)
            self.layer_w_spin.setEnabled(False)
            self.layer_h_spin.setEnabled(False)
            self.scale_spin.setEnabled(False)
            self.aspect_lock.setEnabled(False)
            self.lines_spin.setEnabled(False)
            self.font_combo.setEnabled(False)
            return

        layer_widget = current.data(Qt.UserRole)
        layer = layer_widget.layer

        # 値更新中のシグナル発火を防ぐ
        self.x_spin.blockSignals(True)
        self.y_spin.blockSignals(True)
        self.layer_w_spin.blockSignals(True)
        self.layer_h_spin.blockSignals(True)
        self.scale_spin.blockSignals(True)
        self.lines_spin.blockSignals(True)
        self.font_combo.blockSignals(True)

        # 現在の値を設定
        self.x_spin.setValue(layer.rect.x())
        self.y_spin.setValue(layer.rect.y())
        self.layer_w_spin.setValue(layer.rect.width())
        self.layer_h_spin.setValue(layer.rect.height())
        self.scale_spin.setValue(100.0)

        # レイヤーの元サイズを保存（スケール計算用）
        if not hasattr(layer, 'original_width'):
            layer.original_width = layer.rect.width()
            layer.original_height = layer.rect.height()

        # 有効化
        self.x_spin.setEnabled(True)
        self.y_spin.setEnabled(True)
        self.layer_w_spin.setEnabled(True)
        self.layer_h_spin.setEnabled(True)
        self.scale_spin.setEnabled(True)
        self.aspect_lock.setEnabled(True)

        # テキストレイヤーの場合のみ行数設定とフォント設定を有効化
        if layer.type == 'text':
            self.lines_spin.setValue(layer.lines)
            self.lines_spin.setEnabled(True)
            self.font_combo.setEnabled(True)

            # レイヤーに保存されているフォント情報を復元
            if hasattr(layer, 'font_path') and layer.font_path:
                # 保存されているフォントパスに対応するアイテムを選択
                for i in range(self.font_combo.count()):
                    if self.font_combo.itemData(i) == layer.font_path:
                        self.font_combo.setCurrentIndex(i)
                        break
            else:
                # デフォルトを選択
                self.font_combo.setCurrentIndex(0)
        else:
            self.lines_spin.setEnabled(False)
            self.font_combo.setEnabled(False)

        # シグナルを再有効化
        self.x_spin.blockSignals(False)
        self.y_spin.blockSignals(False)
        self.layer_w_spin.blockSignals(False)
        self.layer_h_spin.blockSignals(False)
        self.scale_spin.blockSignals(False)
        self.lines_spin.blockSignals(False)
        self.font_combo.blockSignals(False)

    def on_layer_position_changed(self):
        """レイヤーの位置が変更された時"""
        current_item = self.layer_list.currentItem()
        if not current_item:
            return

        layer_widget = current_item.data(Qt.UserRole)
        layer = layer_widget.layer

        new_x = self.x_spin.value()
        new_y = self.y_spin.value()

        layer.rect.moveTo(new_x, new_y)
        self.canvas.update()

    def on_layer_size_changed(self):
        """レイヤーのサイズが変更された時"""
        current_item = self.layer_list.currentItem()
        if not current_item:
            return

        layer_widget = current_item.data(Qt.UserRole)
        layer = layer_widget.layer

        # アスペクト比固定時の処理
        if self.aspect_lock.isChecked() and hasattr(layer, 'original_width'):
            sender = self.sender()
            if sender == self.layer_w_spin:
                # 幅を変更した場合、高さを比例させる
                new_w = self.layer_w_spin.value()
                aspect_ratio = layer.original_height / layer.original_width
                new_h = int(new_w * aspect_ratio)

                self.layer_h_spin.blockSignals(True)
                self.layer_h_spin.setValue(new_h)
                self.layer_h_spin.blockSignals(False)
            elif sender == self.layer_h_spin:
                # 高さを変更した場合、幅を比例させる
                new_h = self.layer_h_spin.value()
                aspect_ratio = layer.original_width / layer.original_height
                new_w = int(new_h * aspect_ratio)

                self.layer_w_spin.blockSignals(True)
                self.layer_w_spin.setValue(new_w)
                self.layer_w_spin.blockSignals(False)

        new_w = self.layer_w_spin.value()
        new_h = self.layer_h_spin.value()

        layer.rect.setWidth(new_w)
        layer.rect.setHeight(new_h)
        self.canvas.update()

    def on_layer_scale_changed(self):
        """レイヤーのスケールが変更された時"""
        current_item = self.layer_list.currentItem()
        if not current_item:
            return

        layer_widget = current_item.data(Qt.UserRole)
        layer = layer_widget.layer

        if not hasattr(layer, 'original_width'):
            layer.original_width = layer.rect.width()
            layer.original_height = layer.rect.height()

        # 小数点対応のスケール計算
        scale = self.scale_spin.value() / 100.0
        new_w = round(layer.original_width * scale)
        new_h = round(layer.original_height * scale)

        # SpinBoxの値を更新（シグナルをブロックして無限ループ防止）
        self.layer_w_spin.blockSignals(True)
        self.layer_h_spin.blockSignals(True)
        self.layer_w_spin.setValue(new_w)
        self.layer_h_spin.setValue(new_h)
        self.layer_w_spin.blockSignals(False)
        self.layer_h_spin.blockSignals(False)

        layer.rect.setWidth(new_w)
        layer.rect.setHeight(new_h)
        self.canvas.update()

    def load_template(self):
        """テンプレートを読み込む"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "テンプレートを開く", "", "JSON Files (*.json)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                template = json.load(f)

            # キャンバスをクリア
            self.canvas.layers.clear()
            self.layer_list.clear()

            # キャンバスサイズを設定
            if 'canvas' in template:
                self.width_spin.setValue(template['canvas']['w'])
                self.height_spin.setValue(template['canvas']['h'])

            # レイヤーを読み込む
            if 'layers' in template:
                layers_data = template['layers']

                # 背景レイヤー
                for bg in layers_data.get('background', []):
                    layer = Layer('background', bg['name'], bg['x'], bg['y'], bg['w'], bg['h'], path=bg.get('path', ''))
                    layer.visible = bg.get('visible', True)
                    self.canvas.add_layer(layer)

                # 動画レイヤー
                for vid in layers_data.get('video', []):
                    layer = Layer('video', vid['name'], vid['x'], vid['y'], vid['w'], vid['h'], path=vid.get('path', ''))
                    layer.visible = vid.get('visible', True)
                    self.canvas.add_layer(layer)

                # PNGレイヤー
                for img in layers_data.get('images', []):
                    layer = Layer('image', img['name'], img['x'], img['y'], img['w'], img['h'], path=img.get('path', ''))
                    layer.visible = img.get('visible', True)
                    self.canvas.add_layer(layer)

                # テキストレイヤー
                for name, area in layers_data.get('text_areas', {}).items():
                    layer = Layer('text', name, area['x'], area['y'], area['w'], area['h'], lines=area.get('lines', 3))
                    self.canvas.add_layer(layer)

            self.update_layer_list()
            QMessageBox.information(self, "読み込み完了", f"テンプレートを読み込みました:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"テンプレートの読み込みに失敗しました:\n{str(e)}")

    def load_template_if_exists(self):
        """起動時にtemplate.jsonが存在する場合は自動的に読み込む"""
        import os
        template_path = 'template.json'

        if os.path.exists(template_path):
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)

                # キャンバスサイズを設定
                canvas_size = template_data.get('canvas', {})
                if canvas_size:
                    self.canvas.canvas_width = canvas_size.get('w', 1080)
                    self.canvas.canvas_height = canvas_size.get('h', 1920)
                    self.width_spin.setValue(self.canvas.canvas_width)
                    self.height_spin.setValue(self.canvas.canvas_height)
                    self.canvas.update()

                # 新形式: layers_ordered
                if 'layers_ordered' in template_data:
                    for layer_data in template_data['layers_ordered']:
                        layer_type = layer_data.get('type')
                        name = layer_data.get('name', f'{layer_type}_layer')
                        x = layer_data.get('x', 0)
                        y = layer_data.get('y', 0)
                        w = layer_data.get('w', 100)
                        h = layer_data.get('h', 100)
                        visible = layer_data.get('visible', True)
                        path = layer_data.get('path', '')

                        layer = Layer(layer_type, name, x, y, w, h, path=path)
                        layer.visible = visible
                        self.canvas.add_layer(layer)

                # テキストエリアを追加
                for name, area in template_data.get('text_areas', {}).items():
                    layer = Layer('text', name, area['x'], area['y'], area['w'], area['h'], lines=area.get('lines', 3))
                    # フォント情報があれば復元
                    if 'font' in area:
                        layer.font_path = area['font']
                    self.canvas.add_layer(layer)

                self.update_layer_list()
                print(f"テンプレートを読み込みました: {template_path}")

            except Exception as e:
                print(f"テンプレートの読み込みに失敗しました: {e}")

    def initialize_font_list(self):
        """フォントリストを初期化"""
        import os
        import glob

        # フォントディレクトリからフォントファイルを検索
        font_dir = 'fonts'
        font_files = []

        if os.path.exists(font_dir):
            # .ttfと.otfファイルを検索
            ttf_files = glob.glob(os.path.join(font_dir, '*.ttf'))
            otf_files = glob.glob(os.path.join(font_dir, '*.otf'))
            font_files = ttf_files + otf_files

        # システムフォントも追加
        system_fonts = [
            '/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc',
            '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',
            '/System/Library/Fonts/Hiragino Sans GB.ttc',
            '/Library/Fonts/Arial Unicode.ttf'
        ]

        # フォント選択肢を作成
        self.available_fonts = {}

        # フォントディレクトリのフォント
        for font_path in font_files:
            font_name = os.path.basename(font_path)
            self.available_fonts[font_name] = font_path

        # システムフォント
        for font_path in system_fonts:
            if os.path.exists(font_path):
                font_name = os.path.basename(font_path)
                self.available_fonts[font_name] = font_path

        # コンボボックスに追加
        self.font_combo.clear()
        self.font_combo.addItem("デフォルト (RampartOne-Regular)", "")

        for font_name in sorted(self.available_fonts.keys()):
            self.font_combo.addItem(font_name, self.available_fonts[font_name])

    def on_font_changed(self, font_name):
        """フォントが変更されたときの処理"""
        current_item = self.layer_list.currentItem()
        if not current_item:
            return

        layer_widget = current_item.data(Qt.UserRole)
        layer = layer_widget.layer

        if layer.type != 'text':
            return

        # 選択されたフォントパスを取得
        font_path = self.font_combo.currentData()

        # レイヤーにフォント情報を保存
        layer.font_path = font_path if font_path else None

        print(f"フォント変更: {layer.name} -> {font_name if font_name != 'デフォルト (RampartOne-Regular)' else 'デフォルト'}")

    def save_template(self):
        """テンプレートを保存"""
        template = self.canvas.export_template()

        file_path, _ = QFileDialog.getSaveFileName(
            self, "テンプレートを保存", "template.json", "JSON Files (*.json)"
        )

        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(template, f, ensure_ascii=False, indent=2)

            QMessageBox.information(
                self, "保存完了", f"テンプレートを保存しました:\n{file_path}"
            )


def main():
    app = QApplication(sys.argv)
    window = LayerEditorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
