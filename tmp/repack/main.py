import pyxel
import json
import random
import collections
import os
import sys


# Helper to locate resources when bundled by PyInstaller
def resource_path(relative_path: str) -> str:
    """Return absolute path to resource, works for dev and for PyInstaller bundling.

    Usage:
        pyxel.load(resource_path('my_resource.pyxres'))
        with open(resource_path('card_definitions.json')) as f: ...
    """
    base_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    return os.path.join(base_path, relative_path)

# 分離したモジュールをインポート
from models.card import Card
from config.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, SMALL_CARD_WIDTH, SMALL_CARD_HEIGHT,
    LARGE_CARD_WIDTH, LARGE_CARD_HEIGHT, get_board_positions,
    PLAYER_COLORS, PASS_BUTTON_WIDTH, PASS_BUTTON_HEIGHT, 
    PASS_BUTTON_MARGIN_X, ATTACK_BUTTON_WIDTH, ATTACK_BUTTON_HEIGHT,
    ATTACK_BUTTON_MARGIN_X, YAKU_BUTTON_WIDTH, YAKU_BUTTON_HEIGHT,
    YAKU_BUTTON_MARGIN_X, COUNTER_BUTTON_WIDTH, COUNTER_BUTTON_HEIGHT,
    COUNTER_BUTTON_MARGIN_X, MAX_ROUNDS, STAGE_NAMES
)
from effects import ParticleSystem, VisualEffects

# ボード位置を定数として取得
BOARD_POSITIONS = get_board_positions()


class App:
    def __init__(self):
        pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="Gekka no Jin", fps=30)
        pyxel.mouse(False)
        pyxel.load(resource_path("my_resource.pyxres"))
        self.MAX_ROUNDS = MAX_ROUNDS
        self.STAGE_NAMES = STAGE_NAMES
        
        # パーティクルシステムを初期化
        self.particle_system = ParticleSystem()
        
        # 手札から成立させられる役の定義
        self.hand_yaku_definitions = [
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
        
        self.game_state = "title_screen"
        self.yaku_message_timer = 0
        self.yaku_message_cards = []
        self.yaku_formed_by_player = None
        self.cpu_turn_delay_timer = 0
        self.formed_hand_yaku = None
        self.title_bgm_playing = False
        self.pre_ending_timer = 0
        self.defeat_flash_timer = 0
        self.round_for_display = 1
        self.tan_change_used = [False, False]
        self.counter_turns = [0, 0]
        self.counter_card_display_active = False
        self.eleven_month_kasu_card = Card(month=11, kind='kasu', s_u=60, s_v=160, l_u=96, l_v=106, l_img=2, ribbon_color="none")

        # 各月の最強カードのkindを前もって計算しておく
        with open(resource_path("card_definitions.json"), "r") as f:
            card_defs_data = json.load(f)["cards"]
        
        rank_map = {'kasu': 0, 'tan': 1, 'tane': 2, 'hikari': 3}
        self.strongest_card_kind_by_month = {}
        for month in range(1, 13):
            cards_in_month = [c for c in card_defs_data if c['month'] == month]
            if not cards_in_month:
                continue
            strongest_card = max(cards_in_month, key=lambda c: rank_map.get(c['kind'], -1))
            self.strongest_card_kind_by_month[month] = strongest_card['kind']

        # 各月の最強カードのオブジェクトを保持
        self.strongest_card_objects = {}
        for month, kind in self.strongest_card_kind_by_month.items():
            card_data = next((c for c in card_defs_data if c['month'] == month and c['kind'] == kind), None)
            if card_data:
                self.strongest_card_objects[month] = Card(
                    month=card_data["month"],
                    kind=card_data["kind"],
                    s_u=card_data["s_u"],
                    s_v=card_data["s_v"],
                    l_u=card_data["l_u"],
                    l_v=card_data["l_v"],
                    l_img=card_data["l_img"],
                    ribbon_color=card_data["ribbon_color"]
                )
        
        # Ensure update/draw exist and are callables; add safe fallbacks if missing
        if not callable(getattr(self, 'update', None)):
            def _update_fallback():
                # minimal no-op update
                if pyxel.btnp(pyxel.KEY_Q):
                    pyxel.quit()
            self.update = _update_fallback

        if not callable(getattr(self, 'draw', None)):
            def _draw_fallback():
                # minimal fallback draw to avoid AttributeError
                try:
                    pyxel.cls(0)
                    pyxel.text(10, 10, 'Starting...', 7)
                except Exception:
                    pass
            self.draw = _draw_fallback

        try:
            pyxel.run(self.update, self.draw)
        except Exception:
            # Print traceback to console for debugging, then exit gracefully
            import traceback, sys
            traceback.print_exc()
            print('Pyxel run failed — see traceback above')
            sys.exit(1)

    def new_game(self):
        """ゲーム全体を最初から始めるときに呼ばれる"""
        self.gauge_value = 0
        self.achieved_yaku = [[], []]
        self.current_round = 1
        self.player_total_scores = [0, 0]
        self.round_wins = [0, 0]
        self.setup_round()

    def setup_round(self):
        """各ラウンドの開始時に呼ばれる"""
        pyxel.stop(1)
        self.achieved_yaku = [[], []]
        self.round_for_display = self.current_round
        self.round_start_gauge = 0
        self.gauge_value = 0
        self.kasu_attack_used = [False, False]
        self.tan_change_used = [False, False]
        self.counter_turns = [0, 0]
        self.jin_effect_active = [False, False]
        self.deck = self._create_deck()
        random.shuffle(self.deck)
        self.draw_pile = collections.deque(self.deck)
        self.player_hands = [[], []]
        self.captured_cards = [[], []]
        for _ in range(6):
            self.player_hands[0].append(self.draw_pile.popleft())
            self.player_hands[1].append(self.draw_pile.popleft())
        self.board = [None] * 12
        self.current_player = random.randint(0, 1)
        self.game_state = "start_screen"
        pyxel.play(0, 9)
        self.start_timer = 2 * 30
        self.turn_state = "action"
        self.selected_card_indices = []
        self.formed_hand_yaku = None
        self.message = f"Player {self.current_player + 1}'s Turn"
        self.message_color = PLAYER_COLORS[self.current_player]
        self.message_flash_timer = 0
        self.consecutive_forced_passes = 0
        self.winner = None
        self.particle_system.clear()  # パーティクルシステムをクリア
        self.yaku_message = ""
        self.yaku_message_timer = 0
        self.yaku_message_cards = []
        self.yaku_formed_by_player = None
        self.cpu_turn_delay_timer = 0

    def _create_deck(self):
        with open("card_definitions.json", "r") as f:
            data = json.load(f)
        
        card_defs = []
        for card_data in data["cards"]:
            card_defs.append(Card(
                month=card_data["month"],
                kind=card_data["kind"],
                s_u=card_data["s_u"],
                s_v=card_data["s_v"],
                l_u=card_data["l_u"],
                l_v=card_data["l_v"],
                l_img=card_data["l_img"],
                ribbon_color=card_data["ribbon_color"]
            ))
        return card_defs

    def update(self):
        if self.yaku_message_timer > 0:
            self.yaku_message_timer -= 1
            if self.yaku_message_timer == 0:
                self.counter_card_display_active = False

        if self.defeat_flash_timer > 0:
            self.defeat_flash_timer -= 1

        # パーティクルシステムの更新
        self.particle_system.update_all()

        if pyxel.btnp(pyxel.KEY_Q): pyxel.quit()

        if self.game_state == "title_screen":
            if not self.title_bgm_playing:
                pyxel.play(3, 13, loop=False)
                self.title_bgm_playing = True
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_RETURN):
                pyxel.stop(3)
                self.title_bgm_playing = False
                self.new_game()
            return

        if self.game_state == "match_over" and (pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)):
            self.game_state = "game_over_screen"
        elif self.game_state == "game_over_screen" and (pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)):
            pyxel.stop()
            self.title_bgm_playing = False
            self.game_state = "title_screen"
        elif self.game_state == "round_over" and (pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)):
            self.setup_round()
        
        elif self.game_state == "pre_ending":
            self.pre_ending_timer -= 1
            
            # パーティクルの動きをスロー化
            self.particle_system.slow_down(0.95)

            if self.pre_ending_timer <= 0:
                self.end_match()
            return
        
        if self.game_state == "start_screen":
            self.start_timer -= 1
            if self.start_timer <= 0:
                self.game_state = "play"
            return

        if self.game_state != "play": return

        if self.turn_state == "draw":
            previous_player = 1 - self.current_player
            if self.counter_turns[previous_player] > 0:
                self.counter_turns[previous_player] -= 1

            if self.draw_pile:
                self.player_hands[self.current_player].append(self.draw_pile.popleft())
                if self.message_flash_timer <= 0:
                    self.message = f"Player {self.current_player + 1} drew a card."
                    self.message_color = PLAYER_COLORS[self.current_player]
                    self.message_flash_timer = 0
            else:
                if self.message_flash_timer <= 0:
                    self.message = "Draw pile is empty."
                    self.message_color = 7
                    self.message_flash_timer = 0
            self.turn_state = "action"
            return

        if self.current_player == 0:
            if self.turn_state == "action":
                if not self._has_valid_moves(self.current_player):
                    self.pass_turn()
                else:
                    self.consecutive_forced_passes = 0
                    self.handle_mouse_input()
            elif self.turn_state in ["destroy_target_selection", "yaku_destroy_target_selection"]:
                self.handle_mouse_input()
        else:
            if self.cpu_turn_delay_timer > 0:
                self.cpu_turn_delay_timer -= 1
                return

            if self.turn_state == "action":
                if not self._has_valid_moves(self.current_player):
                    self.pass_turn()
                else:
                    self.consecutive_forced_passes = 0
                    self.handle_cpu_turn()

    def handle_mouse_input(self):
        hand = self.player_hands[self.current_player]
        hand_width = len(hand) * SMALL_CARD_WIDTH + (len(hand) - 1) * 4
        start_x = (SCREEN_WIDTH - hand_width) / 2

        if self.turn_state == "destroy_target_selection":
            for i, pos in enumerate(BOARD_POSITIONS):
                if self.board[i] is not None:
                    if self.is_mouse_over(pos[0], pos[1], LARGE_CARD_WIDTH, LARGE_CARD_HEIGHT):
                        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                            self.destroy_card_on_board(i)
                            return
            return

        if self.turn_state == "yaku_destroy_target_selection":
            for i, pos in enumerate(BOARD_POSITIONS):
                item = self.board[i]
                if item is not None and item[0] != self.current_player:
                    if self.is_mouse_over(pos[0], pos[1], LARGE_CARD_WIDTH, LARGE_CARD_HEIGHT):
                        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                            self.steal_card_on_board(i)
                            return
            return

        # 手札のクリック処理
        for i, card in enumerate(hand):
            x = start_x + i * (SMALL_CARD_WIDTH + 4)
            y = SCREEN_HEIGHT - SMALL_CARD_HEIGHT - 20
            if i in self.selected_card_indices: y -= 5
            if self.is_mouse_over(x, y, SMALL_CARD_WIDTH, SMALL_CARD_HEIGHT):
                if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                    if i in self.selected_card_indices:
                        self.selected_card_indices.remove(i)
                    else:
                        if len(self.selected_card_indices) < 5:
                            self.selected_card_indices.append(i)
                    
                    self.formed_hand_yaku = self._find_formed_hand_yaku()
                    return

        # ボードエリアのクリック処理
        if len(self.selected_card_indices) == 1:
            selected_card_index = self.selected_card_indices[0]
            selected_card = hand[selected_card_index]
            
            for i, pos in enumerate(BOARD_POSITIONS):
                if self.is_mouse_over(pos[0], pos[1], LARGE_CARD_WIDTH, LARGE_CARD_HEIGHT):
                    if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                        if selected_card.month == (i + 1):
                            board_item = self.board[i]
                            can_place = False
                            if board_item is None:
                                can_place = True
                            else:
                                board_card_rank = board_item[1].rank
                                if selected_card.rank >= board_card_rank:
                                    can_place = True
                                else:
                                    self.message = "Cannot place: Rank too low!"
                                    self.message_color = 7
                            if can_place:
                                self.place_card(i)
                        else:
                            self.message = "Month does not match!"
                            self.message_color = 7
                        return

        # ボタンのクリック処理
        if self.current_player == 0:
            pass_button_x = SCREEN_WIDTH - PASS_BUTTON_WIDTH - 5
            pass_button_y = SCREEN_HEIGHT - PASS_BUTTON_HEIGHT - 5
            next_button_x = pass_button_x

            # PASSボタン
            if self.is_mouse_over(pass_button_x, pass_button_y, PASS_BUTTON_WIDTH, PASS_BUTTON_HEIGHT):
                if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                    self.pass_turn()
                    return
            
            # ATTACKボタン
            selected_kasu_count = sum(1 for idx in self.selected_card_indices if self.player_hands[0][idx].kind == 'kasu')
            kasu_attack_possible = len(self.selected_card_indices) == 5 and selected_kasu_count == 5 and not self.kasu_attack_used[self.current_player]
            
            if kasu_attack_possible:
                attack_button_x = next_button_x - ATTACK_BUTTON_WIDTH - ATTACK_BUTTON_MARGIN_X
                if self.is_mouse_over(attack_button_x, pass_button_y, ATTACK_BUTTON_WIDTH, ATTACK_BUTTON_HEIGHT):
                    if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                        self.kasu_attack_used[self.current_player] = True
                        self.turn_state = "destroy_target_selection"
                        self.message = "Select a card to destroy!"
                        self.message_color = 7
                        self.player_hands[self.current_player] = [card for idx, card in enumerate(hand) if idx not in self.selected_card_indices]
                        self.selected_card_indices.clear()
                        self.formed_hand_yaku = None
                        return
                next_button_x = attack_button_x

            # YAKUボタン
            if self.formed_hand_yaku:
                yaku_button_x = next_button_x - YAKU_BUTTON_WIDTH - YAKU_BUTTON_MARGIN_X
                if self.is_mouse_over(yaku_button_x, pass_button_y, YAKU_BUTTON_WIDTH, YAKU_BUTTON_HEIGHT):
                    if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                        self.activate_hand_yaku(self.formed_hand_yaku)
                        return
                next_button_x = yaku_button_x

            # COUNTERボタン
            is_counter_card_selected = False
            if len(self.selected_card_indices) == 1:
                selected_card = hand[self.selected_card_indices[0]]
                if selected_card.month == 11 and selected_card.kind == 'kasu':
                    is_counter_card_selected = True

            if is_counter_card_selected:
                counter_button_x = next_button_x - COUNTER_BUTTON_WIDTH - COUNTER_BUTTON_MARGIN_X
                if self.is_mouse_over(counter_button_x, pass_button_y, COUNTER_BUTTON_WIDTH, COUNTER_BUTTON_HEIGHT):
                    if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                        self.counter_turns[self.current_player] = 5
                        self.update_gauge(-15)
                        
                        used_card_index = self.selected_card_indices[0]
                        used_card = hand.pop(used_card_index)
                        self.selected_card_indices.clear()

                        self.yaku_message = "COUNTER ACTIVATED!"
                        self.yaku_message_timer = 90
                        self.yaku_message_cards = [used_card]
                        self.yaku_formed_by_player = self.current_player
                        
                        pyxel.play(2, 18)
                        
                        self.current_player = 1 - self.current_player
                        if self.current_player == 1:
                            self.cpu_turn_delay_timer = 30
                        self.turn_state = "draw"
                        self.message = f"Player {self.current_player + 1}'s Turn."
                        return

    def handle_cpu_turn(self):
        cpu_hand = self.player_hands[self.current_player]

        # カス札アタックを評価
        kasu_cards_in_hand_indices = [i for i, card in enumerate(cpu_hand) if card.kind == 'kasu']
        if not self.kasu_attack_used[self.current_player] and len(kasu_cards_in_hand_indices) >= 5 and any(item is not None for item in self.board):
            best_target_index = -1
            max_value = -999
            for board_idx, item in enumerate(self.board):
                if item is not None:
                    owner, card_on_board = item
                    value = 0
                    if owner == 0:
                        value += card_on_board.points * 2
                        if card_on_board.kind == 'hikari': value += 10
                    else:
                        value -= card_on_board.points * 2
                    if value > max_value:
                        max_value = value
                        best_target_index = board_idx
            
            if best_target_index != -1 and max_value > 5:
                self.kasu_attack_used[self.current_player] = True
                self.selected_card_indices = kasu_cards_in_hand_indices[:5]
                for idx in sorted(self.selected_card_indices, reverse=True):
                    cpu_hand.pop(idx)
                self.destroy_card_on_board(best_target_index)
                self.selected_card_indices.clear()
                return

        # 通常のカードプレイを評価
        possible_moves = []

        for card_index, card in enumerate(cpu_hand):
            for board_pos_index in range(len(BOARD_POSITIONS)):
                if card.month == (board_pos_index + 1):
                    board_item = self.board[board_pos_index]
                    can_place = False
                    score = 0
                    
                    if board_item is None:
                        can_place = True
                        score = card.points
                    else:
                        owner, board_card = board_item
                        if card.rank >= board_card.rank:
                            can_place = True
                            score = card.points - board_card.points
                            if owner == 0:
                                score += 5
                    
                    if can_place:
                        possible_moves.append((score, card_index, board_pos_index))

        if possible_moves:
            possible_moves.sort(key=lambda x: x[0], reverse=True)
            top_moves = possible_moves[:3]
            selected_move = random.choice(top_moves)
            
            _, card_idx, board_idx = selected_move
            self.selected_card_indices = [card_idx]
            self.place_card(board_idx)
            return

        self.pass_turn()

    def _find_formed_hand_yaku(self):
        if not self.selected_card_indices:
            return None
        
        hand = self.player_hands[self.current_player]
        selected_cards = [hand[i] for i in self.selected_card_indices]

        for yaku in self.hand_yaku_definitions:
            if len(selected_cards) == yaku["num_cards"]:
                if all(yaku["is_member"](c) for c in selected_cards):
                    if yaku["validate"](selected_cards):
                        return yaku
        return None

    def activate_hand_yaku(self, yaku):
        self.yaku_message = yaku["name"]
        self.yaku_message_timer = 90
        if self.current_player == 0:
            pyxel.play(2, 17)
        else:
            pyxel.play(2, 0)

        hand = self.player_hands[self.current_player]
        used_cards = [hand[i] for i in self.selected_card_indices]
        self.yaku_message_cards = used_cards
        self.yaku_formed_by_player = self.current_player

        self.achieved_yaku[self.current_player].append(yaku["name"].lower())
        self.captured_cards[self.current_player].extend(used_cards)
        self.player_hands[self.current_player] = [card for idx, card in enumerate(hand) if idx not in self.selected_card_indices]
        
        self.selected_card_indices.clear()
        self.formed_hand_yaku = None

        if yaku.get("effect") == "instant_win":
            if self.current_player == 0:
                self.gauge_value = 100
            else:
                self.gauge_value = -100
            self.end_round()
            return

        points = yaku["points"]
        is_countered = False
        counter_player = 1 - self.current_player
        if self.counter_turns[counter_player] > 0:
            self.message = "COUNTER SUCCESS!"
            self.message_color = PLAYER_COLORS[counter_player]
            self.message_flash_timer = 90
            pyxel.play(2, 17)
            self.counter_card_display_active = True

            points *= -1
            self.counter_turns[counter_player] = 0
            is_countered = True
        
        self.update_gauge(points)
        if self.game_state == "match_over" or self.game_state == "round_over": return

        if is_countered:
            self.current_player = 1 - self.current_player
            if self.current_player == 1:
                self.cpu_turn_delay_timer = 30
            self.turn_state = "draw"
            return

        if yaku.get("effect") == "steal":
            self.turn_state = "yaku_destroy_target_selection"
            self.message = f"{yaku['name']}! Steal a card!"
            self.message_color = PLAYER_COLORS[self.current_player]
            self.message_flash_timer = 99999
        else:
            if self.draw_pile:
                self.player_hands[self.current_player].append(self.draw_pile.popleft())
            self.turn_state = "action"
            self.message = f"YAKU! {yaku['name']}! Your turn continues."
            self.message_color = PLAYER_COLORS[self.current_player]
            self.message_flash_timer = 99999

    def steal_card_on_board(self, board_index):
        if self.board[board_index] is None: return
        owner_id, card_to_steal = self.board[board_index]

        is_strongest_for_month = card_to_steal.kind == self.strongest_card_kind_by_month.get(card_to_steal.month)
        if self.jin_effect_active[owner_id] and card_to_steal.month == self.current_round and is_strongest_for_month:
            self.jin_effect_active[owner_id] = False
            if not any(self.jin_effect_active):
                pyxel.stop(1)

        pyxel.play(3, 3)

        try:
            self.captured_cards[owner_id].remove(card_to_steal)
        except ValueError:
            pass

        self.captured_cards[self.current_player].append(card_to_steal)
        self.board[board_index] = None
        
        self.current_player = 1 - self.current_player
        if self.current_player == 1:
            self.cpu_turn_delay_timer = 30
        self.turn_state = "draw"
        self.message = f"Player {self.current_player + 1}'s Turn."
        self.message_color = PLAYER_COLORS[self.current_player]
        self.message_flash_timer = 0

    def is_mouse_over(self, x, y, w, h):
        return x <= pyxel.mouse_x < x + w and y <= pyxel.mouse_y < y + h

    def pass_turn(self):
        self.consecutive_forced_passes += 1
        
        if self.consecutive_forced_passes >= 2:
            self.end_game_stalemate()
            return

        self.current_player = 1 - self.current_player
        if self.current_player == 1:
            self.cpu_turn_delay_timer = 30
        self.turn_state = "draw"
        self.message = f"Player {self.current_player + 1}'s Turn. Passed."
        self.message_color = PLAYER_COLORS[self.current_player]
        self.message_flash_timer = 0

    def end_game_stalemate(self):
        if self.gauge_value > 0:
            self.winner = 0
        elif self.gauge_value < 0:
            self.winner = 1
        else:
            player1_captured_count = sum(1 for item in self.board if item and item[0] == 0)
            player2_captured_count = sum(1 for item in self.board if item and item[0] == 1)

            if player1_captured_count > player2_captured_count:
                self.winner = 0
                self.gauge_value = 10
            elif player2_captured_count > player1_captured_count:
                self.winner = 1
                self.gauge_value = -10
            else:
                self.winner = -1
                self.gauge_value = 0

        if self.winner != -1:
            self.message = f"Stalemate win: P{self.winner + 1}! (Click or R)"
            self.message_color = PLAYER_COLORS[self.winner]
        else:
            self.message = "Stalemate Draw! (Click or R to restart)"
            self.message_color = 7
        
        self.end_round()

    def _has_valid_moves(self, player_id):
        hand = self.player_hands[player_id]

        for card in hand:
            for board_pos_index in range(len(BOARD_POSITIONS)):
                if card.month == (board_pos_index + 1):
                    board_item = self.board[board_pos_index]
                    if board_item is None:
                        return True
                    else:
                        board_card_rank = board_item[1].rank
                        if card.rank >= board_card_rank:
                            return True
        
        if not self.kasu_attack_used[player_id]:
            kasu_cards_in_hand_indices = [i for i, c in enumerate(hand) if c.kind == 'kasu']
            if len(kasu_cards_in_hand_indices) >= 5 and any(item is not None for item in self.board):
                best_target_value = -999
                for board_idx, item in enumerate(self.board):
                    if item is not None:
                        owner, card_on_board = item
                        value = 0
                        if owner == 1 - player_id: value += card_on_board.points
                        else: value -= card_on_board.points
                        if card_on_board.kind == 'hikari':
                            if owner == 1 - player_id: value += 5
                            else: value -= 5
                        if value > best_target_value: best_target_value = value
                if best_target_value > 0:
                    return True

        return False

    def destroy_card_on_board(self, board_index):
        if self.board[board_index] is None: return
        owner_id, card_to_destroy = self.board[board_index]

        is_strongest_for_month = card_to_destroy.kind == self.strongest_card_kind_by_month.get(card_to_destroy.month)
        if self.jin_effect_active[owner_id] and card_to_destroy.month == self.current_round and is_strongest_for_month:
            self.jin_effect_active[owner_id] = False
            if not any(self.jin_effect_active):
                pyxel.stop(1)

        pos = BOARD_POSITIONS[board_index]
        center_x = pos[0] + LARGE_CARD_WIDTH / 2
        center_y = pos[1] + LARGE_CARD_HEIGHT / 2
        
        # パーティクルシステムを使用して爆発エフェクトを追加
        self.particle_system.add_explosion(center_x, center_y, 40)

        pyxel.play(3, 4)

        try:
            self.captured_cards[owner_id].remove(card_to_destroy)
            points = card_to_destroy.points * 2
            self.update_gauge(points)
            if self.game_state == "gameover": return

        except ValueError:
            pass

        self.board[board_index] = None
        self.message = f"Card at position {board_index + 1} destroyed!"
        self.message_color = PLAYER_COLORS[self.current_player]
        self.message_flash_timer = 0

        self.current_player = 1 - self.current_player
        if self.current_player == 1:
            self.cpu_turn_delay_timer = 30
        self.turn_state = "draw"
        self.message = f"Player {self.current_player + 1}'s Turn. Card destroyed."
        self.message_color = PLAYER_COLORS[self.current_player]
        self.message_flash_timer = 0

    def place_card(self, area_index):
        hand = self.player_hands[self.current_player]
        used_card_index = self.selected_card_indices[0]
        used_card = hand.pop(used_card_index)

        is_strongest_card = used_card.kind == self.strongest_card_kind_by_month.get(used_card.month)
        is_jin_activation = not self.jin_effect_active[self.current_player] and used_card.month == self.current_round and is_strongest_card

        if is_jin_activation:
            pyxel.play(2, 15)
        else:
            pyxel.play(3, 5)

        points = used_card.points
        if self.jin_effect_active[self.current_player]:
            points *= 2
        
        if self.board[area_index] is not None:
            owner_id, overwritten_card = self.board[area_index]
            points -= overwritten_card.points

            is_strongest_for_month = overwritten_card.kind == self.strongest_card_kind_by_month.get(overwritten_card.month)
            if self.jin_effect_active[owner_id] and overwritten_card.month == self.current_round and is_strongest_for_month:
                self.jin_effect_active[owner_id] = False
                if not any(self.jin_effect_active):
                    pyxel.stop(1)

            try:
                self.captured_cards[owner_id].remove(overwritten_card)
            except ValueError:
                pass

        self.board[area_index] = (self.current_player, used_card)
        self.captured_cards[self.current_player].append(used_card)
        self.selected_card_indices.clear()
        self.formed_hand_yaku = None

        if is_jin_activation:
            self.jin_effect_active[self.current_player] = True
            self.message = f"JIN! Player {self.current_player + 1} activated the formation!"
            self.message_color = PLAYER_COLORS[self.current_player]
            self.message_flash_timer = 90
            pyxel.play(1, 14, loop=True)

        yaku_formed, yaku_points, formed_yaku_names, formed_yaku_effects = self.check_yaku()
        points += yaku_points

        counter_player = 1 - self.current_player
        if self.counter_turns[counter_player] > 0 and yaku_points > 0:
            self.message = "COUNTER SUCCESS!"
            self.message_color = PLAYER_COLORS[counter_player]
            self.message_flash_timer = 90
            pyxel.play(2, 17)
            self.counter_card_display_active = True

            points *= -1
            self.counter_turns[counter_player] = 0

            self.update_gauge(points)
            if self.game_state == "round_over" or self.game_state == "match_over": return
            if self.check_win_condition(): return

            self.current_player = 1 - self.current_player
            if self.current_player == 1:
                self.cpu_turn_delay_timer = 30
            self.turn_state = "draw"
            return

        if "instant_win" in formed_yaku_effects:
            if self.current_player == 0:
                self.gauge_value = 100
            else:
                self.gauge_value = -100
            self.end_round()
            return

        self.update_gauge(points)
        if self.game_state == "round_over" or self.game_state == "match_over": return

        if self.check_win_condition(): return

        if yaku_formed:
            yaku_names_str = " & ".join(formed_yaku_names)
            self.message = f"YAKU! {yaku_names_str} (+{points} pts)"
            self.message_color = PLAYER_COLORS[self.current_player]
            self.message_flash_timer = 99999
            return

        self.current_player = 1 - self.current_player
        if self.current_player == 1:
            self.cpu_turn_delay_timer = 30
        self.turn_state = "draw"
        if self.message_flash_timer <= 0:
            self.message = f"Player {self.current_player + 1}'s Turn. Draw a card."
            self.message_color = PLAYER_COLORS[self.current_player]
            self.message_flash_timer = 0

    def check_win_condition(self):
        if all(item is not None for item in self.board):
            self.end_round()
            return True
        return False

    def end_round(self):
        pyxel.stop(1)
        self.round_for_display = self.current_round
        round_score = self.gauge_value
        if round_score > 0:
            self.player_total_scores[0] += round_score
            self.round_wins[0] += 1
        elif round_score < 0:
            self.player_total_scores[1] += abs(round_score)
            self.round_wins[1] += 1

        self.current_round += 1

        if self.current_round > self.MAX_ROUNDS:
            self.game_state = "pre_ending"
            self.pre_ending_timer = 5 * 30
        else:
            self.winner = -1
            if round_score > 0:
                self.winner = 0
            elif round_score < 0:
                self.winner = 1

            if self.winner != -1:
                if self.winner == 0:
                    pyxel.play(0, 11)
                elif self.winner == 1:
                    pyxel.play(0, 10)

                self.message = f"Round Win: Player {self.winner + 1}! (Click to Next)"
                self.message_color = PLAYER_COLORS[self.winner]
            else:
                self.message = "Round Draw. (Click to Next)"
                self.message_color = 7
            
            self.game_state = "round_over"
            self.message_flash_timer = 0

    def end_match(self):
        p1_wins = self.round_wins[0]
        p2_wins = self.round_wins[1]

        if p1_wins > p2_wins:
            self.winner = 0
        elif p2_wins > p1_wins:
            self.winner = 1
        else:
            p1_score = self.player_total_scores[0]
            p2_score = self.player_total_scores[1]
            if p1_score > p2_score:
                self.winner = 0
            elif p2_score > p1_score:
                self.winner = 1
            else:
                self.winner = -1

        if self.winner != -1:
            self.message = f"MATCH WINNER: PLAYER {self.winner + 1}! (Click to Title)"
            self.message_color = PLAYER_COLORS[self.winner]
            if self.winner == 0:
                pyxel.play(0, 12)
            elif self.winner == 1:
                pyxel.play(0, 0)
                pyxel.play(1, 10)
                self.defeat_flash_timer = 30
        else:
            self.message = "MATCH DRAW! (Click to Title)"
            self.message_color = 7
            pyxel.play(0, 10)
        
        self.game_state = "match_over"
        self.message_flash_timer = 0

    def check_yaku(self):
        player_captured = self.captured_cards[self.current_player]
        achieved_yaku = self.achieved_yaku[self.current_player]
        yaku_formed_this_turn = False
        points_this_turn = 0
        formed_yaku_names = []
        formed_yaku_effects = []
        newly_formed_cards = []

        # INOSHIKACHO
        if "inoshikacho" not in achieved_yaku:
            boar = next((c for c in player_captured if c.month == 6 and c.kind == 'tane'), None)
            deer = next((c for c in player_captured if c.month == 7 and c.kind == 'tane'), None)
            butterfly = next((c for c in player_captured if c.month == 10 and c.kind == 'tane'), None)
            if boar and deer and butterfly:
                achieved_yaku.append("inoshikacho")
                points_this_turn += 50
                formed_yaku_names.append("INOSHIKACHO")
                newly_formed_cards.extend([boar, deer, butterfly])
                yaku_formed_this_turn = True

        # AKATAN
        if "akatan" not in achieved_yaku:
            cards = [c for c in player_captured if c.kind == 'tan' and c.ribbon_color == 'red']
            if len(cards) == 3:
                achieved_yaku.append("akatan")
                points_this_turn += 50
                formed_yaku_names.append("AKATAN")
                newly_formed_cards.extend(cards)
                yaku_formed_this_turn = True

        # AOTAN
        if "aotan" not in achieved_yaku:
            cards = [c for c in player_captured if c.kind == 'tan' and c.ribbon_color == 'blue']
            if len(cards) == 3:
                achieved_yaku.append("aotan")
                points_this_turn += 50
                formed_yaku_names.append("AOTAN")
                newly_formed_cards.extend(cards)
                yaku_formed_this_turn = True

        # HANAMI
        if "hanami" not in achieved_yaku:
            card1 = next((c for c in player_captured if c.month == 3 and c.kind == 'hikari'), None)
            card2 = next((c for c in player_captured if c.month == 9 and c.kind == 'tane'), None)
            if card1 and card2:
                achieved_yaku.append("hanami")
                points_this_turn += 50
                formed_yaku_names.append("HANAMI")
                newly_formed_cards.extend([card1, card2])
                yaku_formed_this_turn = True

        # TSUKIMI
        if "tsukimi" not in achieved_yaku:
            card1 = next((c for c in player_captured if c.month == 8 and c.kind == 'hikari'), None)
            card2 = next((c for c in player_captured if c.month == 9 and c.kind == 'tane'), None)
            if card1 and card2:
                achieved_yaku.append("tsukimi")
                points_this_turn += 50
                formed_yaku_names.append("TSUKIMI")
                newly_formed_cards.extend([card1, card2])
                yaku_formed_this_turn = True

        # Hikari yaku
        hikari_cards = [c for c in player_captured if c.kind == 'hikari']
        hikari_count = len(hikari_cards)
        is_rainman_present = any(c.month == 11 for c in hikari_cards)
        
        potential_points = 0
        potential_yaku_name = ""
        if hikari_count == 5:
            potential_points, potential_yaku_name = 100, "goko"
        elif hikari_count == 4 and not is_rainman_present:
            potential_points, potential_yaku_name = 80, "shiko"
        elif hikari_count == 4 and is_rainman_present:
            potential_points, potential_yaku_name = 70, "ameshiko"
        elif hikari_count == 3 and not is_rainman_present:
            potential_points, potential_yaku_name = 50, "sanko"

        awarded_points = 0
        if "sanko" in achieved_yaku: awarded_points = 50
        if "ameshiko" in achieved_yaku: awarded_points = 70
        if "shiko" in achieved_yaku: awarded_points = 80
        if "goko" in achieved_yaku: awarded_points = 100

        if potential_points > awarded_points:
            points_this_turn += potential_points - awarded_points
            
            if potential_yaku_name not in achieved_yaku:
                achieved_yaku.append(potential_yaku_name)
            
            if potential_yaku_name in ["shiko", "ameshiko", "goko"] and "sanko" in achieved_yaku:
                 achieved_yaku.remove("sanko")
            if potential_yaku_name == "goko" and "shiko" in achieved_yaku:
                 achieved_yaku.remove("shiko")
            if potential_yaku_name == "goko" and "ameshiko" in achieved_yaku:
                 achieved_yaku.remove("ameshiko")
            
            formed_yaku_names.append(potential_yaku_name.upper())
            yaku_formed_this_turn = True
            
            current_yaku_hikari_cards = [c for c in hikari_cards if not (potential_yaku_name == "sanko" and c.month == 11)]
            newly_formed_cards.extend(current_yaku_hikari_cards)

            if potential_yaku_name == "goko":
                formed_yaku_effects.append("instant_win")

        if yaku_formed_this_turn and formed_yaku_names:
            self.yaku_message = " & ".join(formed_yaku_names)
            self.yaku_message_timer = 90
            self.yaku_message_cards = list(dict.fromkeys(newly_formed_cards))
            self.yaku_formed_by_player = self.current_player
            if self.current_player == 0:
                pyxel.play(2, 17)
            else:
                pyxel.play(2, 0)

        return yaku_formed_this_turn, points_this_turn, formed_yaku_names, formed_yaku_effects

    def draw(self):
        pyxel.pal()
        
        if self.game_state == "pre_ending":
            VisualEffects.apply_white_out_palette(self.pre_ending_timer, 5 * 30)

        pyxel.cls(0)

        if self.game_state == "title_screen":
            self.draw_title_screen()
            return

        if self.game_state == "game_over_screen":
            self.draw_game_over_screen()
            self.draw_mouse_cursor()
            return

        if self.game_state == "match_over":
            if self.winner == 1 and VisualEffects.flash_white(self.defeat_flash_timer, pyxel.frame_count):
                pyxel.cls(7)
                return

            if self.winner == 0:
                self.draw_victory_screen()
            elif self.winner == 1:
                self.draw_defeat_screen()
            else:
                self.draw_draw_screen()
            
            self.draw_mouse_cursor()
            return

        round_num_to_show = self.round_for_display if self.game_state in ["round_over", "pre_ending"] else self.current_round
        stage_name = self.STAGE_NAMES[round_num_to_show - 1]
        round_text = f"ROUND {round_num_to_show} - {stage_name}"
        text_width = len(round_text) * pyxel.FONT_WIDTH
        pyxel.text((SCREEN_WIDTH - text_width) / 2, 5, round_text, 7)

        p1_wins_text = f"P1 WINS: {self.round_wins[0]}"
        pyxel.text(5, 5, p1_wins_text, PLAYER_COLORS[0])
        p2_wins_text = f"P2 WINS: {self.round_wins[1]}"
        p2_wins_text_width = len(p2_wins_text) * pyxel.FONT_WIDTH
        pyxel.text(SCREEN_WIDTH - p2_wins_text_width - 5, 5, p2_wins_text, PLAYER_COLORS[1])

        self.draw_gauge()

        for i, pos in enumerate(BOARD_POSITIONS):
            item = self.board[i]
            if item:
                player, card = item
                card.draw_large(pos[0], pos[1])
                pyxel.rectb(pos[0]-1, pos[1]-1, LARGE_CARD_WIDTH+2, LARGE_CARD_HEIGHT+2, PLAYER_COLORS[player])

                is_strongest_for_month = card.kind == self.strongest_card_kind_by_month.get(card.month)
                target_round_for_jin_slot = self.round_for_display if self.game_state in ["round_over", "pre_ending"] else self.current_round
                is_jin_card = self.jin_effect_active[player] and card.month == target_round_for_jin_slot and is_strongest_for_month
                if is_jin_card:
                    VisualEffects.flash_border(pos[0], pos[1], LARGE_CARD_WIDTH, LARGE_CARD_HEIGHT, 10, pyxel.frame_count)
            else:
                target_round_for_jin_slot = self.round_for_display if self.game_state in ["round_over", "pre_ending"] else self.current_round
                if (i + 1) == target_round_for_jin_slot:
                    strongest_card = self.strongest_card_objects.get(target_round_for_jin_slot)
                    if strongest_card:
                        pyxel.pal(1, 1)
                        pyxel.pal(2, 1)
                        pyxel.pal(3, 1)
                        pyxel.pal(4, 5)
                        pyxel.pal(5, 5)
                        pyxel.pal(6, 5)
                        pyxel.pal(8, 1)
                        pyxel.pal(9, 5)
                        pyxel.pal(10, 6)
                        pyxel.pal(11, 1)
                        pyxel.pal(12, 1)
                        pyxel.pal(13, 6)
                        pyxel.pal(15, 5)
                        
                        strongest_card.draw_large(pos[0], pos[1])
                        pyxel.pal()

                is_hovered = len(self.selected_card_indices) == 1 and self.is_mouse_over(pos[0], pos[1], LARGE_CARD_WIDTH, LARGE_CARD_HEIGHT)
                pyxel.rectb(pos[0], pos[1], LARGE_CARD_WIDTH, LARGE_CARD_HEIGHT, 13 if is_hovered else 7)
                month_str = str(i + 1)
                pyxel.text(pos[0] + (LARGE_CARD_WIDTH - len(month_str)*pyxel.FONT_WIDTH)/2, pos[1] + 24, month_str, 7)

        if self.game_state != 'gameover':
            pyxel.text(194, 178, f"TURN: PLAYER {self.current_player + 1}", PLAYER_COLORS[self.current_player])

        char_x = 5
        char_y = SCREEN_HEIGHT - 16 - 7
        pyxel.blt(char_x, char_y, 0, 0, 192, 16, 16, 14)
        pyxel.rectb(char_x - 1, char_y - 1, 16 + 2, 16 + 2, 7)

        text_x = char_x + 16 + 2
        current_message_color = self.message_color
        if self.message_flash_timer > 0:
            if (pyxel.frame_count // 5) % 2 == 0:
                current_message_color = 7
            else:
                current_message_color = 10
        
        pyxel.text(text_x, SCREEN_HEIGHT - 13, self.message, current_message_color)

        player1_hand = self.player_hands[0]
        player1_hand_width = len(player1_hand) * SMALL_CARD_WIDTH + (len(player1_hand) - 1) * 4
        player1_start_x = (SCREEN_WIDTH - player1_hand_width) / 2
        for index, card in enumerate(player1_hand):
            x = player1_start_x + index * (SMALL_CARD_WIDTH + 4)
            y = SCREEN_HEIGHT - SMALL_CARD_HEIGHT - 20
            if self.current_player == 0 and index in self.selected_card_indices: y -= 5
            card.draw_small(x, y)

        if self.current_player == 0:
            pass_button_x = SCREEN_WIDTH - PASS_BUTTON_WIDTH - 5
            pass_button_y = SCREEN_HEIGHT - PASS_BUTTON_HEIGHT - 5
            next_button_x = pass_button_x

            is_pass_hovered = self.is_mouse_over(pass_button_x, pass_button_y, PASS_BUTTON_WIDTH, PASS_BUTTON_HEIGHT)
            pyxel.rectb(pass_button_x, pass_button_y, PASS_BUTTON_WIDTH, PASS_BUTTON_HEIGHT, 13 if is_pass_hovered else 7)
            pyxel.text(pass_button_x + 4, pass_button_y + 4, "PASS", 7)

            selected_kasu_count = sum(1 for idx in self.selected_card_indices if self.player_hands[0][idx].kind == 'kasu')
            kasu_attack_possible = len(self.selected_card_indices) == 5 and selected_kasu_count == 5 and not self.kasu_attack_used[0]
            if kasu_attack_possible:
                attack_button_x = next_button_x - ATTACK_BUTTON_WIDTH - ATTACK_BUTTON_MARGIN_X
                is_attack_hovered = self.is_mouse_over(attack_button_x, pass_button_y, ATTACK_BUTTON_WIDTH, ATTACK_BUTTON_HEIGHT)
                
                if is_attack_hovered:
                    button_color, text_color = 13, 7
                else:
                    flashing_color = VisualEffects.get_flashing_color(pyxel.frame_count)
                    button_color, text_color = flashing_color, flashing_color
                
                pyxel.rectb(attack_button_x, pass_button_y, ATTACK_BUTTON_WIDTH, ATTACK_BUTTON_HEIGHT, button_color)
                pyxel.text(attack_button_x + 4, pass_button_y + 4, "ATTACK", text_color)
                next_button_x = attack_button_x

            if self.formed_hand_yaku:
                yaku_button_x = next_button_x - YAKU_BUTTON_WIDTH - YAKU_BUTTON_MARGIN_X
                is_yaku_hovered = self.is_mouse_over(yaku_button_x, pass_button_y, YAKU_BUTTON_WIDTH, YAKU_BUTTON_HEIGHT)

                if is_yaku_hovered:
                    button_color, text_color = 13, 7
                else:
                    flashing_color = VisualEffects.get_flashing_color(pyxel.frame_count)
                    button_color, text_color = flashing_color, flashing_color

                pyxel.rectb(yaku_button_x, pass_button_y, YAKU_BUTTON_WIDTH, YAKU_BUTTON_HEIGHT, button_color)
                pyxel.text(yaku_button_x + 4, pass_button_y + 4, "YAKU", text_color)
                next_button_x = yaku_button_x

            is_counter_card_selected = False
            if len(self.selected_card_indices) == 1:
                selected_card = self.player_hands[0][self.selected_card_indices[0]]
                if selected_card.month == 11 and selected_card.kind == 'kasu':
                    is_counter_card_selected = True

            if is_counter_card_selected:
                counter_button_x = next_button_x - COUNTER_BUTTON_WIDTH - COUNTER_BUTTON_MARGIN_X
                is_counter_hovered = self.is_mouse_over(counter_button_x, pass_button_y, COUNTER_BUTTON_WIDTH, COUNTER_BUTTON_HEIGHT)

                if is_counter_hovered:
                    button_color, text_color = 13, 7
                else:
                    flashing_color = VisualEffects.get_flashing_color(pyxel.frame_count)
                    button_color, text_color = flashing_color, flashing_color

                pyxel.rectb(counter_button_x, pass_button_y, COUNTER_BUTTON_WIDTH, COUNTER_BUTTON_HEIGHT, button_color)
                pyxel.text(counter_button_x + 4, pass_button_y + 4, "COUNTER", text_color)

        player2_hand = self.player_hands[1]
        player2_hand_width = len(player2_hand) * SMALL_CARD_WIDTH + (len(player2_hand) - 1) * 4
        player2_start_x = (SCREEN_WIDTH - player2_hand_width) / 2
        for i in range(len(player2_hand)):
            Card.draw_back(player2_start_x + i * (SMALL_CARD_WIDTH + 4), 15)

        if self.draw_pile:
            draw_pile_x = SCREEN_WIDTH - SMALL_CARD_WIDTH - 10
            draw_pile_y = 15
            Card.draw_back(draw_pile_x, draw_pile_y)
            text_content = str(len(self.draw_pile))
            text_x = draw_pile_x + (SMALL_CARD_WIDTH - len(text_content) * pyxel.FONT_WIDTH) / 2
            text_y = draw_pile_y + (SMALL_CARD_HEIGHT - pyxel.FONT_HEIGHT) / 2
            pyxel.text(text_x, text_y, text_content, 7)
            
        if self.game_state == "start_screen":
            start_msg = "GET READY"
            msg_width = len(start_msg) * pyxel.FONT_WIDTH
            rect_x, rect_y, rect_w, rect_h = SCREEN_WIDTH/2 - msg_width/2 - 4, SCREEN_HEIGHT/2 - 10, msg_width + 8, 16
            pyxel.rect(rect_x, rect_y, rect_w, rect_h, 0)
            pyxel.rectb(rect_x, rect_y, rect_w, rect_h, 7)
            pyxel.text(SCREEN_WIDTH/2 - msg_width/2, SCREEN_HEIGHT/2 - 4, start_msg, 7)

        if self.game_state == "round_over":
            msg_width = len(self.message) * pyxel.FONT_WIDTH
            pyxel.rect(SCREEN_WIDTH/2 - msg_width/2 - 4, SCREEN_HEIGHT/2 - 10, msg_width + 8, 16, 0)
            pyxel.text(int(SCREEN_WIDTH/2 - msg_width/2), int(SCREEN_HEIGHT/2 - 4), self.message, self.message_color)

        if self.yaku_message_timer > 0:
            msg = self.yaku_message
            msg_width = len(msg) * pyxel.FONT_WIDTH
            flashing_color = VisualEffects.get_flashing_color(pyxel.frame_count)

            if self.yaku_message_cards:
                num_cards = len(self.yaku_message_cards)
                card_w, card_h = LARGE_CARD_WIDTH, LARGE_CARD_HEIGHT
                
                total_width = num_cards * card_w + (num_cards - 1) * 4
                start_x = (SCREEN_WIDTH - total_width) / 2
                card_y = (SCREEN_HEIGHT / 2) - (card_h / 2) - 10

                for i, card in enumerate(self.yaku_message_cards):
                    card.draw_large(start_x + i * (card_w + 4), card_y)

                if self.yaku_formed_by_player is not None:
                    player_color = PLAYER_COLORS[self.yaku_formed_by_player]
                    for i, card in enumerate(self.yaku_message_cards):
                        card_x = start_x + i * (card_w + 4)
                        VisualEffects.flash_rectangle(card_x, card_y, card_w, card_h, player_color, pyxel.frame_count)
                
                text_y = card_y + card_h + 8
                rect_x, rect_y, rect_w, rect_h = SCREEN_WIDTH/2 - msg_width/2 - 4, text_y - 2, msg_width + 8, 12
                pyxel.rect(rect_x, rect_y, rect_w, rect_h, 0)
                pyxel.rectb(rect_x, rect_y, rect_w, rect_h, 7)
                pyxel.text(int(SCREEN_WIDTH/2 - msg_width/2), text_y, msg, flashing_color)
            else:
                rect_x, rect_y, rect_w, rect_h = SCREEN_WIDTH/2 - msg_width/2 - 4, SCREEN_HEIGHT/2 - 10, msg_width + 8, 16
                pyxel.rect(rect_x, rect_y, rect_w, rect_h, 0)
                pyxel.rectb(rect_x, rect_y, rect_w, rect_h, 7)
                pyxel.text(int(SCREEN_WIDTH/2 - msg_width/2), int(SCREEN_HEIGHT/2 - 4), msg, flashing_color)

            if self.counter_card_display_active:
                kasu_card_x = (SCREEN_WIDTH - LARGE_CARD_WIDTH) / 2
                kasu_card_y = (SCREEN_HEIGHT - LARGE_CARD_HEIGHT) / 2
                self.eleven_month_kasu_card.draw_large(kasu_card_x, kasu_card_y)
                VisualEffects.flash_border(kasu_card_x, kasu_card_y, LARGE_CARD_WIDTH, LARGE_CARD_HEIGHT, 10, pyxel.frame_count)

        # パーティクルシステムを使用して描画
        self.particle_system.draw_all()

        self.draw_mouse_cursor()

    def draw_title_screen(self):
        pyxel.cls(0)
        pyxel.blt(0, 0, 0, 0, 208, SCREEN_WIDTH, 50, 0)
        
        subtitle_text = "- Gekka no jin -"
        subtitle_width = len(subtitle_text) * pyxel.FONT_WIDTH
        pyxel.text(int((SCREEN_WIDTH - subtitle_width) / 2), 60, subtitle_text, 7)

        story_text = [
            "A.D. 1274 - TSUSHIMA -",
            "",
            "The Mongol horde is upon us.",
            "As the lord of this island, you command your samurai:",
            '"Now is the time to defend our homeland!',
            'Warriors of Tsushima, rise!',
            'Defend this land with all your might!"'
        ]
        
        line_y = 90
        for line in story_text:
            line_width = len(line) * pyxel.FONT_WIDTH
            pyxel.text(int((SCREEN_WIDTH - line_width) / 2), line_y, line, 7)
            line_y += 10

        start_msg = "CLICK TO START"
        msg_width = len(start_msg) * pyxel.FONT_WIDTH
        if (pyxel.frame_count // 15) % 2 == 0:
            pyxel.text(int((SCREEN_WIDTH - msg_width) / 2), 180, start_msg, 13)

        credit_line1 = "(V) 2.4"
        credit_line2 = "(C) 2025 Saizo"
        
        line2_width = len(credit_line2) * pyxel.FONT_WIDTH
        pyxel.text(SCREEN_WIDTH - line2_width - 5, SCREEN_HEIGHT - 12, credit_line2, 7)
        
        line1_width = len(credit_line1) * pyxel.FONT_WIDTH
        pyxel.text(SCREEN_WIDTH - line1_width - 5, SCREEN_HEIGHT - 21, credit_line1, 7)

        self.draw_mouse_cursor()

    def draw_victory_screen(self):
        pyxel.cls(0)
        pyxel.blt(0, 0, 1, 0, 208, SCREEN_WIDTH, 50, 0)
        
        title_text = "VICTORY"
        title_width = len(title_text) * pyxel.FONT_WIDTH
        pyxel.text(int((SCREEN_WIDTH - title_width) / 2), 60, title_text, 10)

        victory_text = [
            "The Mongol horde has retreated.",
            "Peace has been restored to Tsushima.",
            "",
            "Our proud samurai have fought with honor,",
            "and fulfilled their duty to protect this land!"
        ]
        
        line_y = 100
        for line in victory_text:
            line_width = len(line) * pyxel.FONT_WIDTH
            pyxel.text(int((SCREEN_WIDTH - line_width) / 2), line_y, line, 7)
            line_y += 10

        continue_msg = "CLICK TO RETURN TO TITLE"
        msg_width = len(continue_msg) * pyxel.FONT_WIDTH
        if (pyxel.frame_count // 15) % 2 == 0:
            pyxel.text(int((SCREEN_WIDTH - msg_width) / 2), 190, continue_msg, 13)

    def draw_defeat_screen(self):
        pyxel.cls(0)
        pyxel.blt(0, 0, 2, 0, 208, SCREEN_WIDTH, 50, 0)
        
        title_text = "DEFEAT"
        title_width = len(title_text) * pyxel.FONT_WIDTH
        pyxel.text(int((SCREEN_WIDTH - title_width) / 2), 60, title_text, 8)

        defeat_text = [
            "Tsushima has fallen to the Mongol horde.",
            "The spirit of the samurai is broken,",
            "their swords shattered.",
            "",
            "Their duty to protect this land remains unfulfilled.",
            "",
            "What future awaits Tsushima, alone beneath the moon...?"
        ]
        
        line_y = 100
        for line in defeat_text:
            line_width = len(line) * pyxel.FONT_WIDTH
            pyxel.text(int((SCREEN_WIDTH - line_width) / 2), line_y, line, 7)
            line_y += 10

        continue_msg = "CLICK TO RETURN TO TITLE"
        msg_width = len(continue_msg) * pyxel.FONT_WIDTH
        if (pyxel.frame_count // 15) % 2 == 0:
            pyxel.text(int((SCREEN_WIDTH - msg_width) / 2), 190, continue_msg, 13)

    def draw_draw_screen(self):
        pyxel.cls(0)
        
        title_text = "DRAW"
        title_width = len(title_text) * pyxel.FONT_WIDTH
        pyxel.text(int((SCREEN_WIDTH - title_width) / 2), 60, title_text, 7)

        draw_text = [
            "Tsushima and the Mongols are evenly matched,",
            "the back-and-forth struggle continues.",
            "",
            "As the lord of this island, you inspire your comrades:",
            "'With all your might! For the future of Tsushima,",
            "we will not be defeated!'"
        ]
        
        line_y = 100
        for line in draw_text:
            line_width = len(line) * pyxel.FONT_WIDTH
            pyxel.text(int((SCREEN_WIDTH - line_width) / 2), line_y, line, 7)
            line_y += 10

        continue_msg = "CLICK TO RETURN TO TITLE"
        msg_width = len(continue_msg) * pyxel.FONT_WIDTH
        if (pyxel.frame_count // 15) % 2 == 0:
            pyxel.text(int((SCREEN_WIDTH - msg_width) / 2), 190, continue_msg, 13)

    def draw_game_over_screen(self):
        pyxel.cls(0)
        
        msg1 = "Game over"
        msg2 = "Thank you for playing!"
        
        msg1_width = len(msg1) * pyxel.FONT_WIDTH
        msg2_width = len(msg2) * pyxel.FONT_WIDTH
        
        pyxel.text(int((SCREEN_WIDTH - msg1_width) / 2), 110, msg1, 7)
        pyxel.text(int((SCREEN_WIDTH - msg2_width) / 2), 120, msg2, 7)

        continue_msg = "CLICK TO RETURN TO TITLE"
        msg_width = len(continue_msg) * pyxel.FONT_WIDTH
        if (pyxel.frame_count // 15) % 2 == 0:
            pyxel.text(int((SCREEN_WIDTH - msg_width) / 2), 190, continue_msg, 13)

    def draw_gauge(self):
        GAUGE_WIDTH = 200
        GAUGE_HEIGHT = 8
        x = (SCREEN_WIDTH - GAUGE_WIDTH) / 2
        y = 48

        pyxel.rect(x, y, GAUGE_WIDTH, GAUGE_HEIGHT, 1)
        pyxel.rectb(x, y, GAUGE_WIDTH, GAUGE_HEIGHT, 7)

        center_x = x + GAUGE_WIDTH / 2

        if self.gauge_value > 0:
            bar_width = (self.gauge_value / 100) * (GAUGE_WIDTH / 2)
            pyxel.rect(center_x, y, bar_width, GAUGE_HEIGHT, 12)
        elif self.gauge_value < 0:
            bar_width = (-self.gauge_value / 100) * (GAUGE_WIDTH / 2)
            pyxel.rect(center_x - bar_width, y, bar_width, GAUGE_HEIGHT, 8)
        
        pyxel.line(int(center_x), y, int(center_x), y + GAUGE_HEIGHT -1, 7)

    def update_gauge(self, value):
        if self.current_player == 0:
            self.gauge_value += value
        else:
            self.gauge_value -= value
        
        self.gauge_value = max(-100, min(100, self.gauge_value))

        if self.gauge_value >= 100 or self.gauge_value <= -100:
            self.end_round()

    def draw_mouse_cursor(self):
        x, y, col = pyxel.mouse_x, pyxel.mouse_y, 7
        pyxel.pset(x, y, col)
        pyxel.line(x - 2, y, x + 2, y, col)
        pyxel.line(x, y - 2, x, y + 2, col)

if __name__ == "__main__":
    App()