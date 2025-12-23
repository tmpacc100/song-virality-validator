#!/usr/bin/env python3
"""
QRect.translate() の挙動をテスト
"""
from PySide6.QtCore import QRect, QPoint

def test_translate():
    """translate()がin-placeで動作することを確認"""

    # 元のRect
    rect = QRect(100, 200, 300, 400)
    print(f"元のRect: x={rect.x()}, y={rect.y()}, w={rect.width()}, h={rect.height()}")

    # translate()を実行
    delta = QPoint(10, 20)
    rect.translate(delta)

    print(f"translate後: x={rect.x()}, y={rect.y()}, w={rect.width()}, h={rect.height()}")

    # 期待値: (110, 220, 300, 400)
    expected_x = 110
    expected_y = 220

    if rect.x() == expected_x and rect.y() == expected_y:
        print("\n✓ translate()はin-placeで動作します（問題なし）")
    else:
        print(f"\n✗ translate()が期待通りに動作していません")
        print(f"   期待値: ({expected_x}, {expected_y})")
        print(f"   実際の値: ({rect.x()}, {rect.y()})")

    # translated()との違いをテスト
    rect2 = QRect(100, 200, 300, 400)
    rect2_new = rect2.translated(delta)

    print(f"\n元のrect2: x={rect2.x()}, y={rect2.y()}")
    print(f"translated()の戻り値: x={rect2_new.x()}, y={rect2_new.y()}")

    if rect2.x() == 100 and rect2_new.x() == 110:
        print("✓ translated()は新しいRectを返します（元のRectは変更されない）")

if __name__ == '__main__':
    test_translate()
