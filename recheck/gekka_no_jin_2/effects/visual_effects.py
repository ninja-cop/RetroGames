# effects/visual_effects.py
"""ビジュアルエフェクト関連の機能"""

import pyxel


# ホワイトアウト演出用のカラーパレット遷移パス
FADE_PATHS = {
    0:  [5, 6, 7, 7, 7],    # Black -> Dark Gray -> Light Gray -> White
    1:  [12, 13, 6, 7, 7],  # Dark Blue -> Blue -> Lavender -> Light Gray -> White
    2:  [13, 14, 15, 7, 7], # Dark Purple -> Lavender -> Pink -> Light Peach -> White
    3:  [11, 6, 7, 7, 7],   # Dark Green -> Green -> Light Gray -> White
    4:  [15, 6, 7, 7, 7],   # Brown -> Light Peach -> Light Gray -> White
    5:  [6, 7, 7, 7, 7],    # Dark Gray -> Light Gray -> White
    6:  [7, 7, 7, 7, 7],    # Light Gray -> White
    7:  [7, 7, 7, 7, 7],    # White -> White
    8:  [14, 15, 7, 7, 7],  # Red -> Pink -> Light Peach -> White
    9:  [10, 15, 7, 7, 7],  # Orange -> Yellow -> Light Peach -> White
    10: [15, 7, 7, 7, 7],   # Yellow -> Light Peach -> White
    11: [6, 7, 7, 7, 7],    # Green -> Light Gray -> White
    12: [6, 7, 7, 7, 7],    # Blue -> Light Gray -> White
    13: [6, 7, 7, 7, 7],    # Lavender -> Light Gray -> White
    14: [15, 7, 7, 7, 7],   # Pink -> Light Peach -> White
    15: [7, 7, 7, 7, 7],    # Light Peach -> White
}


class VisualEffects:
    """ビジュアルエフェクトのユーティリティクラス"""
    
    @staticmethod
    def apply_white_out_palette(timer: int, max_timer: int):
        """
        画面全体を徐々に白くするためのパレット操作
        
        Args:
            timer: 残りタイマー値（減少していく）
            max_timer: 最大タイマー値
        """
        if timer <= 0:
            return

        # progress goes from 0.0 to 1.0
        progress = 1.0 - (timer / float(max_timer))
        eased_progress = progress * progress  # イージング

        # Determine the stage of the fade (0 to 5)
        fade_stage = int(eased_progress * 5)

        for original_color in range(16):
            if original_color == 7:  # 白色はスキップ
                continue

            path = FADE_PATHS[original_color]
            stage_index = min(fade_stage, len(path) - 1)
            new_color = path[stage_index]
            
            if original_color != new_color:
                pyxel.pal(original_color, new_color)

    @staticmethod
    def flash_white(duration: int, current_frame: int) -> bool:
        """
        ホワイトフラッシュ効果（敗北演出用）
        
        Args:
            duration: フラッシュの持続フレーム数
            current_frame: 現在のフレームカウンタ
            
        Returns:
            現在のフレームで白く塗るべきかどうか
        """
        if duration <= 0:
            return False
        
        # 3フレームごとに白く塗る/元に戻すを繰り返す
        return (current_frame // 3) % 2 == 0

    @staticmethod
    def flash_rectangle(x: int, y: int, w: int, h: int, 
                       color: int, frame_count: int, interval: int = 6):
        """
        点滅する矩形を描画（役カード表示用）
        
        Args:
            x, y: 矩形の位置
            w, h: 矩形のサイズ
            color: 矩形の色
            frame_count: 現在のフレームカウント
            interval: 点滅間隔（フレーム数）
        """
        if (frame_count // interval) % 2 == 0:
            # 2重の枠線で太く見せる
            pyxel.rectb(x - 1, y - 1, w + 2, h + 2, color)
            pyxel.rectb(x - 2, y - 2, w + 4, h + 4, color)

    @staticmethod
    def flash_border(x: int, y: int, w: int, h: int, 
                    color: int, frame_count: int, interval: int = 15):
        """
        点滅する枠線を描画（陣カード表示用）
        
        Args:
            x, y: 枠の位置
            w, h: 枠のサイズ
            color: 枠の色
            frame_count: 現在のフレームカウント
            interval: 点滅間隔（フレーム数）
        """
        if (frame_count // interval) % 2 == 0:
            pyxel.rectb(x - 2, y - 2, w + 4, h + 4, color)

    @staticmethod
    def get_flashing_color(frame_count: int, colors: list = None) -> int:
        """
        点滅する色を取得
        
        Args:
            frame_count: 現在のフレームカウント
            colors: 使用する色のリスト（デフォルト: [8, 10, 12]）
            
        Returns:
            現在のフレームで使用すべき色
        """
        if colors is None:
            colors = [8, 10, 12]
        
        color_index = (frame_count // 3) % len(colors)
        return colors[color_index]