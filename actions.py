import time
import os
import random
import state
import render
import persistence


def on_space():
    """Handle space key presses once per physical press.

    Prevents holding space from repeatedly granting resources by
    ignoring repeated events until a release is detected.
    Also keeps a small rate limit as a safety net.
    """
    if state.space_pressed:
        return
    state.space_pressed = True
    now = time.time()
    min_interval = 1.0 / 15.0
    if now - state.last_space_time < min_interval:
        return
    state.last_space_time = now
    state.count += state.per_click
    try:
        if state.count > getattr(state, 'run_max_count', 0):
            state.run_max_count = state.count
    except Exception:
        pass
    if state.game_state == 'incremental':
        render.display_incremental()


def on_space_release():
    state.space_pressed = False


def start_new_game():
    if state.game_state != 'start_menu':
        return
    persistence.reset_game()
    state.game_state = 'menu'
    render.display_menu()


def load_game_from_menu():
    if state.game_state != 'start_menu':
        return
    if not persistence.has_save_file():
        return
    persistence.load_game()
    state.game_state = 'menu'
    render.display_menu()


def buy_upgrade_key(key: str):
    if state.game_state != 'incremental':
        return
    for upg in state.upgrades:
        if upg['key'] == key:
            if upg['purchased']:
                return
            meta_req = upg.get('meta_req')
            if meta_req and not state.meta_upgrades_state.get(meta_req, False):
                render.flash_message('Upgrade locked. Unlock via Meta Upgrades')
                return
            if state.count < upg['cost']:
                return
            state.count -= upg['cost']
            if upg['type'] == 'add':
                state.per_click += upg['amount']
            else:
                state.per_click *= upg['amount']
            upg['purchased'] = True
            break
    persistence.save_game()
    render.display_incremental()


def buy_shop_item(key: str):
    if state.game_state != 'shop':
        return
    for item in state.shop_items:
        if item['key'] == key:
            if item['purchased']:
                return
            if state.count < item['cost']:
                return
            state.count -= item['cost']
            item['purchased'] = True
            item_obj = {
                'name': item['name'],
                'type': item['type'],
                'level': 1,
                'ascii': ''
            }
            if item['type'] == 'weapon':
                ascii_path = os.path.join(os.path.dirname(__file__), 'ascii', 'dart_monkey_small.txt')
                try:
                    with open(ascii_path, 'r', encoding='utf-8') as af:
                        item_obj['ascii'] = af.read().rstrip('\n')
                except Exception:
                    item_obj['ascii'] = (
                        '  /|\n'
                        ' /_|_\n'
                        '   |\n'
                        '   |\n'
                    )
            elif item['type'] == 'armour':
                item_obj['ascii'] = (
                    '  ___\n'
                    ' /___\n'
                    ' |   |\n'
                    ' |___|\n'
                )
            elif item['type'] == 'bag':
                item_obj['ascii'] = (
                    '  ____\n'
                    ' /___/\\\n'
                    ' |___|\n'
                )
            if item['type'] == 'bag':
                state.has_bag = True
                state.inventory_capacity += item['amount'] * 10
            state.inventory.append(item_obj)
            persistence.save_game()
            break
    render.display_shop()


def equip_inventory_index(key: str):
    if state.game_state != 'inventory':
        return
    try:
        idx = int(key) - 1
    except Exception:
        return
    if idx < 0 or idx >= len(state.inventory):
        return
    item = state.inventory[idx]
    if not isinstance(item, dict):
        return
    itype = item.get('type')
    if itype == 'weapon':
        lvl = int(item.get('level', 1))
        atk = int(state.compute_weapon_attack(lvl))
        state.equipped_weapon = dict(item, equipped=True)
        state.attack = atk
        persistence.save_game()
        render.display_inventory()
    elif itype == 'armour':
        lvl = int(item.get('level', 1))
        df = int(state.compute_armour_defense(lvl))
        state.equipped_armour = dict(item, equipped=True)
        state.defense = df
        persistence.save_game()
        render.display_inventory()


def enter_feature(name: str):
    state.prev_state = state.game_state
    state.prev_player_pos = (state.player_y, state.player_x)
    if name == 'shop':
        state.game_state = 'shop'
        render.display_shop()


def move(dx, dy):
    now = time.time()
    if now - state.last_move_time < state.MOVE_INTERVAL:
        return

    ny = state.player_y + dy
    nx = state.player_x + dx

    # border crossing -> move between rooms instead of clamping
    if nx <= 0:
        # if multi-room world is available, move to previous room
        if getattr(state, 'rooms', None) and len(state.rooms) > 0:
            dest = (state.current_room_index - 1) % len(state.rooms)
            state.load_room(dest)
            state.player_y = max(1, min(state.ROOM_HEIGHT - 2, ny))
            state.player_x = state.ROOM_WIDTH - 2
            state.last_move_time = now
            render.render_map()
            return
        # fallback: clamp to inner edge
        nx = 1
    if nx >= state.ROOM_WIDTH - 1:
        if getattr(state, 'rooms', None) and len(state.rooms) > 0:
            dest = (state.current_room_index + 1) % len(state.rooms)
            state.load_room(dest)
            state.player_y = max(1, min(state.ROOM_HEIGHT - 2, ny))
            state.player_x = 1
            state.last_move_time = now
            render.render_map()
            return
        nx = state.ROOM_WIDTH - 2
    if ny <= 0:
        if getattr(state, 'rooms', None) and len(state.rooms) > 0:
            dest = (state.current_room_index - 1) % len(state.rooms)
            state.load_room(dest)
            state.player_y = state.ROOM_HEIGHT - 2
            state.player_x = max(1, min(state.ROOM_WIDTH - 2, nx))
            state.last_move_time = now
            render.render_map()
            return
        ny = state.ROOM_HEIGHT - 2
    if ny >= state.ROOM_HEIGHT - 1:
        if getattr(state, 'rooms', None) and len(state.rooms) > 0:
            dest = (state.current_room_index + 1) % len(state.rooms)
            state.load_room(dest)
            state.player_y = 1
            state.player_x = max(1, min(state.ROOM_WIDTH - 2, nx))
            state.last_move_time = now
            render.render_map()
            return
        ny = 1

    ny = max(0, min(state.ROOM_HEIGHT - 1, ny))
    nx = max(0, min(state.ROOM_WIDTH - 1, nx))

    # stepping into wall? abort
    if state.current_map[ny][nx] == state.WALL_CHAR:
        return

    state.player_y, state.player_x = ny, nx
    state.last_move_time = now

    # teleports
    if (state.player_y, state.player_x) in state.TELEPORTS:
        tp = state.TELEPORTS[(state.player_y, state.player_x)]
        if tp == 'shop':
            enter_feature('shop')
            return

    # fountain
    if state.current_map[state.player_y][state.player_x] == 'H':
        trigger_healing((state.player_y, state.player_x))
        return

    # exclaim events
    if state.current_map[state.player_y][state.player_x] == '!':
        trigger_exclaim((state.player_y, state.player_x))
        return

    # enemy encounter
    pos = (state.player_y, state.player_x)
    if pos in state.enemies:
        enter_battle(pos)


def trigger_exclaim(pos):
    try:
        y, x = pos
    except Exception:
        return
    try:
        if state.current_map[y][x] != '!':
            return
    except Exception:
        return
    state.current_map[y][x] = state.FLOOR_CHAR
    if random.random() < 0.5:
        reward = random.randint(50, 200) + max(0, state.map_visit_count) * 20
        state.count += reward
        try:
            if state.count > getattr(state, 'run_max_count', 0):
                state.run_max_count = state.count
        except Exception:
            pass
        persistence.save_game()
        render.flash_message(f'Treasure found! +{reward} coins')
        if state.game_state == 'explore':
            render.render_map()
        return
    visits = max(0, state.map_visit_count)
    if random.random() < 0.6:
        enemy = {
            'name': 'Ambusher',
            'hp': 100 + visits * 12,
            'atk': 6 + visits,
            'reward': int(150 * (1 + 0.2 * visits)),
            'ascii': "(>_<)"
        }
    else:
        enemy = {
            'name': 'Angry Monkey',
            'hp': 140 + visits * 18,
            'atk': 10 + visits * 2,
            'reward': int(300 * (1 + 0.2 * visits)),
            'ascii': "(~)"
        }
    state.enemies[(y, x)] = enemy
    enter_battle((y, x))


def trigger_healing(pos):
    try:
        y, x = pos
    except Exception:
        return
    try:
        if state.current_map[y][x] != 'H':
            return
    except Exception:
        return
    heal = min(state.player_max_hp - state.player_hp, 10)
    if heal <= 0:
        if state.game_state == 'explore':
            render.render_map()
        return
    state.player_hp = min(state.player_max_hp, state.player_hp + heal)
    render.flash_message(f'Healed +{heal} HP')
    if state.game_state == 'explore':
        render.render_map()


def return_from_shop():
    if state.game_state != 'shop':
        if state.game_state == 'meta':
            state.player_hp = state.player_max_hp
            persistence.reset_run()
            persistence.save_game()
            state.game_state = 'menu'
            render.display_menu()
        return
    prev_pos = state.prev_player_pos
    if isinstance(prev_pos, tuple) and len(prev_pos) == 2:
        py, px = prev_pos
        state.player_x = px
        state.player_y = py
    state.game_state = 'explore'
    render.clear_screen()
    render.render_map()


def buy_meta_upgrade(key: str):
    if state.game_state != 'meta':
        return
    for m in state.meta_upgrades:
        if m['key'] == key:
            if m.get('purchased'):
                return
            cost = int(m.get('cost', 0))
            if state.meta_currency < cost:
                return
            state.meta_currency -= cost
            m['purchased'] = True
            mid = m.get('id')
            if mid == 'unlock_tier1':
                state.meta_upgrades_state['unlock_tier1'] = True
            if mid == 'unlock_tier2':
                state.meta_upgrades_state['unlock_tier2'] = True
            if mid == 'start_per_click':
                state.meta_start_per_click = int(state.meta_start_per_click) + 1
            if mid == 'start_attack':
                state.meta_start_attack = int(state.meta_start_attack) + 5
            persistence.save_game()
            break
    render.display_meta_upgrades(0)


def toggle_inventory():
    if not state.has_bag:
        return
    if state.game_state == 'inventory':
        render.switch_to_menu()
        return
    if state.game_state != 'menu':
        return
    state.game_state = 'inventory'
    render.display_inventory()


def enter_battle(pos):
    state.prev_state = state.game_state
    state.prev_player_pos = (state.player_y, state.player_x)
    enemy = state.enemies.get(pos)
    if not enemy:
        return
    state.current_battle_enemy = dict(enemy)
    state.current_battle_pos = pos
    state.game_state = 'battle'
    render.display_battle()


def battle_attack():
    if state.game_state != 'battle' or not state.current_battle_enemy:
        return
    enemy = state.current_battle_enemy
    damage = max(1, state.attack)
    enemy['hp'] -= damage
    if enemy['hp'] <= 0:
        reward = enemy.get('reward', 0)
        state.count += reward
        try:
            if state.count > getattr(state, 'run_max_count', 0):
                state.run_max_count = state.count
        except Exception:
            pass
        try:
            del state.enemies[state.current_battle_pos]
        except Exception:
            pass
        state.current_battle_enemy = None
        state.current_battle_pos = None
        state.game_state = 'explore'
        render.clear_screen()
        render.render_map()
        persistence.save_game()
        return

    state.player_hp -= enemy.get('atk', 0)
    if state.player_hp <= 0:
        render.display_death_splash()
        time.sleep(3)
        try:
            run_best = int(getattr(state, 'run_max_count', 0))
        except Exception:
            run_best = 0
        meta_reward = max(1, run_best // 1000)
        state.meta_currency = getattr(state, 'meta_currency', 0) + meta_reward
        persistence.save_game()
        state.game_state = 'meta'
        render.display_meta_upgrades(meta_reward)
        return
    render.display_battle()


def flee_battle():
    if state.game_state != 'battle':
        return
    try:
        py, px = state.prev_player_pos
        state.player_x = px
        state.player_y = py
    except Exception:
        pass
    state.current_battle_enemy = None
    state.current_battle_pos = None
    state.game_state = 'explore'
    render.clear_screen()
    render.render_map()


def handle_number_key(key: str):
    if state.game_state == 'start_menu':
        if key == '1':
            start_new_game()
        elif key == '2':
            load_game_from_menu()
        return
    if state.game_state == 'inventory':
        equip_inventory_index(key)
        return
    if state.game_state == 'shop':
        buy_shop_item(key)
        return
    if state.game_state == 'incremental':
        buy_upgrade_key(key)
        return
    if state.game_state == 'meta':
        buy_meta_upgrade(key)
        return

