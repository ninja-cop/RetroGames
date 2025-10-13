# models/card.py
"""花札カードのデータクラス"""

import pyxel
from config.constants import SMALL_CARD_WIDTH, SMALL_CARD_HEIGHT, LARGE_CARD_WIDTH, LARGE_CARD_HEIGHT


class Card:
    """花札一枚のデータ。大小の座標情報を持つ"""
    
    def __init__(self, month, kind, s_u, s_v, l_u, l_v, l_img, ribbon_color='none'):
        """
        カードを初期化する
        
        Args:
            month: 月 (1-12)
            kind: カードの種類 ('kasu', 'tan', 'tane', 'hikari')
            s_u, s_v: 小さいカードの画像座標
            l_u, l_v: 大きいカードの画像座標
            l_img: 大きいカードの画像番号
            ribbon_color: 短冊の色 ('red', 'blue', 'none')
        """
        self.month = month
        self.kind = kind
        
        # 小さいカードの描画情報
        self.s_u, self.s_v = s_u, s_v
        
        # 大きいカードの描画情報
        self.l_u, self.l_v, self.l_img = l_u, l_v, l_img
        
        # 短冊の色情報
        self.ribbon_color = ribbon_color
        
        # カードの階級と点数を計算
        self.rank = self._get_rank(kind)
        self.points = self._get_points(kind)

    def _get_rank(self, kind):
        """カードの階級を取得する（上書き判定で使用）"""
        rank_map = {
            'kasu': 0,
            'tan': 1,
            'tane': 2,
            'hikari': 3
        }
        return rank_map.get(kind, -1)

    def _get_points(self, kind):
        """カードの基本点数を取得する"""
        points_map = {
            'hikari': 20,
            'tane': 10,
            'tan': 5,
            'kasu': 1
        }
        return points_map.get(kind, 0)

    def draw_small(self, x, y):
        """小さいサイズでカードを描画する（手札用）"""
        pyxel.blt(x, y, 0, self.s_u, self.s_v, SMALL_CARD_WIDTH, SMALL_CARD_HEIGHT, 14)

    def draw_large(self, x, y):
        """大きいサイズでカードを描画する（ボード用）"""
        pyxel.blt(x, y, self.l_img, self.l_u, self.l_v, LARGE_CARD_WIDTH, LARGE_CARD_HEIGHT, 14)

    @staticmethod
    def draw_back(x, y):
        """カード裏面を単色で描画する"""
        pyxel.rect(x, y, SMALL_CARD_WIDTH, SMALL_CARD_HEIGHT, 4)
        pyxel.rectb(x, y, SMALL_CARD_WIDTH, SMALL_CARD_HEIGHT, 0)

    def __repr__(self):
        """デバッグ用の文字列表現"""
        return f"Card({self.month}月, {self.kind}, {self.points}pt)"