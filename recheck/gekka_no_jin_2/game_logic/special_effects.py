# game_logic/special_effects.py
"""特殊効果システム - カウンターと陣の管理"""

import pyxel


class CounterSystem:
    """カウンター効果の管理"""
    
    def __init__(self):
        """カウンターシステムを初期化"""
        self.counter_turns = [0, 0]  # 各プレイヤーのカウンター残りターン数
        self.counter_cost = 15  # カウンター発動のゲージコスト
        self.counter_duration = 5  # カウンター持続ターン数

    def activate_counter(self, player_id):
        """
        カウンターを発動
        
        Args:
            player_id: プレイヤーID (0 or 1)
            
        Returns:
            カウンター発動のコスト（ゲージから引く値）
        """
        self.counter_turns[player_id] = self.counter_duration
        return -self.counter_cost

    def is_counter_active(self, player_id):
        """
        カウンターが有効かチェック
        
        Args:
            player_id: プレイヤーID
            
        Returns:
            カウンターが有効かどうか
        """
        return self.counter_turns[player_id] > 0

    def consume_counter(self, player_id):
        """
        カウンターを消費（成功時に呼ぶ）
        
        Args:
            player_id: プレイヤーID
        """
        self.counter_turns[player_id] = 0

    def update_counter_turns(self, player_id):
        """
        カウンターターンを減らす（ターン開始時に呼ぶ）
        
        Args:
            player_id: プレイヤーID
        """
        if self.counter_turns[player_id] > 0:
            self.counter_turns[player_id] -= 1

    def reset(self):
        """カウンター状態をリセット"""
        self.counter_turns = [0, 0]

    def get_counter_turns(self, player_id):
        """
        残りカウンターターン数を取得
        
        Args:
            player_id: プレイヤーID
            
        Returns:
            残りターン数
        """
        return self.counter_turns[player_id]


class JinSystem:
    """陣効果の管理"""
    
    def __init__(self, strongest_card_kind_by_month):
        """
        陣システムを初期化
        
        Args:
            strongest_card_kind_by_month: 各月の最強カードのkind辞書
        """
        self.jin_effect_active = [False, False]  # 各プレイヤーの陣発動状態
        self.strongest_card_kind_by_month = strongest_card_kind_by_month
        self.jin_bonus_multiplier = 2  # 陣発動時の点数倍率

    def check_jin_activation(self, card, current_round, player_id):
        """
        陣が発動するかチェック
        
        Args:
            card: 配置するカード
            current_round: 現在のラウンド
            player_id: プレイヤーID
            
        Returns:
            陣が発動するかどうか
        """
        is_strongest_card = card.kind == self.strongest_card_kind_by_month.get(card.month)
        return (not self.jin_effect_active[player_id] and 
                card.month == current_round and 
                is_strongest_card)

    def activate_jin(self, player_id):
        """
        陣を発動
        
        Args:
            player_id: プレイヤーID
        """
        self.jin_effect_active[player_id] = True
        pyxel.play(1, 14, loop=True)  # 陣発動のBGM

    def deactivate_jin(self, player_id):
        """
        陣を解除
        
        Args:
            player_id: プレイヤーID
            
        Returns:
            他にも陣が発動中のプレイヤーがいるか
        """
        self.jin_effect_active[player_id] = False
        
        # 他に陣発動中のプレイヤーがいなければBGMを停止
        if not any(self.jin_effect_active):
            pyxel.stop(1)
            return False
        return True

    def check_jin_deactivation(self, card, current_round):
        """
        陣が解除されるかチェック
        
        Args:
            card: 破壊/上書きされるカード
            current_round: 現在のラウンド
            
        Returns:
            陣が解除されるかどうか
        """
        is_strongest_for_month = card.kind == self.strongest_card_kind_by_month.get(card.month)
        return card.month == current_round and is_strongest_for_month

    def is_jin_active(self, player_id):
        """
        陣が有効かチェック
        
        Args:
            player_id: プレイヤーID
            
        Returns:
            陣が有効かどうか
        """
        return self.jin_effect_active[player_id]

    def apply_jin_bonus(self, points, player_id):
        """
        陣のボーナスを適用
        
        Args:
            points: 元の点数
            player_id: プレイヤーID
            
        Returns:
            ボーナス適用後の点数
        """
        if self.jin_effect_active[player_id]:
            return points * self.jin_bonus_multiplier
        return points

    def reset(self):
        """陣状態をリセット"""
        self.jin_effect_active = [False, False]
        pyxel.stop(1)

    def is_jin_card(self, card, current_round, player_id):
        """
        カードが陣カードかチェック（描画用）
        
        Args:
            card: チェックするカード
            current_round: 現在のラウンド
            player_id: カードの所有者
            
        Returns:
            陣カードかどうか
        """
        is_strongest_for_month = card.kind == self.strongest_card_kind_by_month.get(card.month)
        return (self.jin_effect_active[player_id] and 
                card.month == current_round and 
                is_strongest_for_month)