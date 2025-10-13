# game_logic/yaku_system.py
"""役判定システム - 手札役とボード役の管理"""

import pyxel


class HandYakuSystem:
    """手札から成立する役の管理"""
    
    def __init__(self):
        """手札役の定義を初期化"""
        self.yaku_definitions = [
            # 役の判定は上から順に行われるため、カード枚数が多く、条件が厳しいものを上に置く
            {
                "name": "GOKO", "points": 100, "num_cards": 5,
                "is_member": lambda c: c.kind == 'hikari',
                "validate": lambda cards: len({c.month for c in cards}) == 5,
                "effect": "instant_win"
            },
            {
                "name": "AMESHIKO", "points": 70, "num_cards": 4,
                "is_member": lambda c: c.kind == 'hikari',
                "validate": lambda cards: any(c.month == 11 for c in cards) and len({c.month for c in cards}) == 4
            },
            {
                "name": "SHIKO", "points": 80, "num_cards": 4,
                "is_member": lambda c: c.kind == 'hikari',
                "validate": lambda cards: not any(c.month == 11 for c in cards) and len({c.month for c in cards}) == 4
            },
            {
                "name": "SANKO", "points": 50, "num_cards": 3,
                "is_member": lambda c: c.kind == 'hikari' and c.month != 11,
                "validate": lambda cards: len({c.month for c in cards}) == 3
            },
            {
                "name": "INOSHIKACHO", "points": 50, "num_cards": 3,
                "is_member": lambda c: c.kind == 'tane',
                "validate": lambda cards: {c.month for c in cards} == {6, 7, 10},
                "effect": "steal"
            },
            {
                "name": "AKATAN", "points": 50, "num_cards": 3,
                "is_member": lambda c: c.ribbon_color == 'red' and c.kind == 'tan',
                "validate": lambda cards: len(cards) == 3
            },
            {
                "name": "AOTAN", "points": 50, "num_cards": 3,
                "is_member": lambda c: c.ribbon_color == 'blue' and c.kind == 'tan',
                "validate": lambda cards: len(cards) == 3
            },
            {
                "name": "HANAMI", "points": 50, "num_cards": 2,
                "is_member": lambda c: True,
                "validate": lambda cards: {c.month for c in cards} == {3, 9} and any(c.month == 3 and c.kind == 'hikari' for c in cards) and any(c.month == 9 and c.kind == 'tane' for c in cards)
            },
            {
                "name": "TSUKIMI", "points": 50, "num_cards": 2,
                "is_member": lambda c: True,
                "validate": lambda cards: {c.month for c in cards} == {8, 9} and any(c.month == 8 and c.kind == 'hikari' for c in cards) and any(c.month == 9 and c.kind == 'tane' for c in cards)
            },
        ]

    def find_formed_yaku(self, selected_cards):
        """
        選択されたカードから成立する役を見つける
        
        Args:
            selected_cards: 選択されたCardオブジェクトのリスト
            
        Returns:
            成立した役の辞書、または None
        """
        if not selected_cards:
            return None

        for yaku in self.yaku_definitions:
            if len(selected_cards) == yaku["num_cards"]:
                if all(yaku["is_member"](c) for c in selected_cards):
                    if yaku["validate"](selected_cards):
                        return yaku
        return None

    def get_yaku_definitions(self):
        """役定義のリストを取得"""
        return self.yaku_definitions


class BoardYakuSystem:
    """ボード上で成立する役の管理"""
    
    def __init__(self):
        """ボード役のシステムを初期化"""
        pass

    def check_yaku(self, captured_cards, achieved_yaku):
        """
        獲得カードから成立する役をチェック
        
        Args:
            captured_cards: プレイヤーが獲得したカードのリスト
            achieved_yaku: 既に達成した役のリスト（小文字）
            
        Returns:
            (役が成立したか, 獲得点数, 成立した役名リスト, 特殊効果リスト, 役のカードリスト)
        """
        yaku_formed = False
        points = 0
        formed_yaku_names = []
        formed_yaku_effects = []
        newly_formed_cards = []

        # 猪鹿蝶
        if "inoshikacho" not in achieved_yaku:
            boar = next((c for c in captured_cards if c.month == 6 and c.kind == 'tane'), None)
            deer = next((c for c in captured_cards if c.month == 7 and c.kind == 'tane'), None)
            butterfly = next((c for c in captured_cards if c.month == 10 and c.kind == 'tane'), None)
            if boar and deer and butterfly:
                achieved_yaku.append("inoshikacho")
                points += 50
                formed_yaku_names.append("INOSHIKACHO")
                newly_formed_cards.extend([boar, deer, butterfly])
                yaku_formed = True

        # 赤短
        if "akatan" not in achieved_yaku:
            cards = [c for c in captured_cards if c.kind == 'tan' and c.ribbon_color == 'red']
            if len(cards) == 3:
                achieved_yaku.append("akatan")
                points += 50
                formed_yaku_names.append("AKATAN")
                newly_formed_cards.extend(cards)
                yaku_formed = True

        # 青短
        if "aotan" not in achieved_yaku:
            cards = [c for c in captured_cards if c.kind == 'tan' and c.ribbon_color == 'blue']
            if len(cards) == 3:
                achieved_yaku.append("aotan")
                points += 50
                formed_yaku_names.append("AOTAN")
                newly_formed_cards.extend(cards)
                yaku_formed = True

        # 花見
        if "hanami" not in achieved_yaku:
            card1 = next((c for c in captured_cards if c.month == 3 and c.kind == 'hikari'), None)
            card2 = next((c for c in captured_cards if c.month == 9 and c.kind == 'tane'), None)
            if card1 and card2:
                achieved_yaku.append("hanami")
                points += 50
                formed_yaku_names.append("HANAMI")
                newly_formed_cards.extend([card1, card2])
                yaku_formed = True

        # 月見
        if "tsukimi" not in achieved_yaku:
            card1 = next((c for c in captured_cards if c.month == 8 and c.kind == 'hikari'), None)
            card2 = next((c for c in captured_cards if c.month == 9 and c.kind == 'tane'), None)
            if card1 and card2:
                achieved_yaku.append("tsukimi")
                points += 50
                formed_yaku_names.append("TSUKIMI")
                newly_formed_cards.extend([card1, card2])
                yaku_formed = True

        # 光札の役（階層的）
        hikari_points, hikari_yaku_name, hikari_cards, hikari_effect = self._check_hikari_yaku(
            captured_cards, achieved_yaku
        )
        
        if hikari_points > 0:
            points += hikari_points
            formed_yaku_names.append(hikari_yaku_name)
            newly_formed_cards.extend(hikari_cards)
            yaku_formed = True
            if hikari_effect:
                formed_yaku_effects.append(hikari_effect)

        return yaku_formed, points, formed_yaku_names, formed_yaku_effects, newly_formed_cards

    def _check_hikari_yaku(self, captured_cards, achieved_yaku):
        """
        光札の役をチェック（五光、四光、雨四光、三光）
        
        Returns:
            (獲得点数, 役名, 役のカード, 特殊効果)
        """
        hikari_cards = [c for c in captured_cards if c.kind == 'hikari']
        hikari_count = len(hikari_cards)
        is_rainman_present = any(c.month == 11 for c in hikari_cards)
        
        potential_points = 0
        potential_yaku_name = ""
        potential_effect = None
        
        if hikari_count == 5:
            potential_points, potential_yaku_name = 100, "goko"
            potential_effect = "instant_win"
        elif hikari_count == 4 and not is_rainman_present:
            potential_points, potential_yaku_name = 80, "shiko"
        elif hikari_count == 4 and is_rainman_present:
            potential_points, potential_yaku_name = 70, "ameshiko"
        elif hikari_count == 3 and not is_rainman_present:
            potential_points, potential_yaku_name = 50, "sanko"

        # 既に獲得している点数を計算
        awarded_points = 0
        if "sanko" in achieved_yaku: awarded_points = 50
        if "ameshiko" in achieved_yaku: awarded_points = 70
        if "shiko" in achieved_yaku: awarded_points = 80
        if "goko" in achieved_yaku: awarded_points = 100

        if potential_points > awarded_points:
            # 新しい役を達成した場合
            actual_points = potential_points - awarded_points
            
            if potential_yaku_name not in achieved_yaku:
                achieved_yaku.append(potential_yaku_name)
            
            # 下位の光役が残っていれば削除
            if potential_yaku_name in ["shiko", "ameshiko", "goko"] and "sanko" in achieved_yaku:
                achieved_yaku.remove("sanko")
            if potential_yaku_name == "goko" and "shiko" in achieved_yaku:
                achieved_yaku.remove("shiko")
            if potential_yaku_name == "goko" and "ameshiko" in achieved_yaku:
                achieved_yaku.remove("ameshiko")
            
            # 役に含まれるカードを取得（三光の場合は雨を除く）
            yaku_hikari_cards = [c for c in hikari_cards 
                                if not (potential_yaku_name == "sanko" and c.month == 11)]
            
            return actual_points, potential_yaku_name.upper(), yaku_hikari_cards, potential_effect

        return 0, "", [], None