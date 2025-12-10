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

    # border crossing -> move between rooms instead of clamping (left-right only, no top-bottom)
    if nx <= 0:
        # if multi-room world is available, move to previous room (non-wrapping)
        if getattr(state, 'rooms', None) and len(state.rooms) > 0 and state.current_room_index > 0:
            dest = state.current_room_index - 1
            state.load_room(dest)
            state.player_y = max(1, min(state.ROOM_HEIGHT - 2, ny))
            state.player_x = state.ROOM_WIDTH - 2
            state.last_move_time = now
            render.render_map()
            return
        # fallback: clamp to inner edge
        nx = 1
    if nx >= state.ROOM_WIDTH - 1:
        if getattr(state, 'rooms', None) and len(state.rooms) > 0 and state.current_room_index < len(state.rooms) - 1:
            dest = state.current_room_index + 1
            state.load_room(dest)
            state.player_y = max(1, min(state.ROOM_HEIGHT - 2, ny))
            state.player_x = 1
            state.last_move_time = now
            render.render_map()
            return
        # If at last room (index len-1), allow moving to next floor only if floor boss was defeated
        elif getattr(state, 'rooms', None) and len(state.rooms) > 0 and state.current_room_index == len(state.rooms) - 1:
            # check for any remaining boss in the current rooms
            boss_alive = False
            try:
                for r in getattr(state, 'rooms', []):
                    for e in r.get('enemies', {}).values():
                        if isinstance(e, dict) and e.get('is_boss'):
                            boss_alive = True
                            break
                    if boss_alive:
                        break
            except Exception:
                boss_alive = False
            if boss_alive:
                render.flash_message('Defeat the floor boss before progressing to the next floor')
                return
            # Do not allow floors beyond 5 (final floor)
            if getattr(state, 'current_floor', 1) >= 5:
                render.flash_message('You have reached the final floor. No further floors.')
                return
            # Advance to next floor and generate new rooms
            state.map_visit_count = getattr(state, 'map_visit_count', 0) + 1
            # increment explicit floor counter
            try:
                state.current_floor = int(getattr(state, 'current_floor', 1)) + 1
            except Exception:
                state.current_floor = getattr(state, 'current_floor', 1) + 1
            state.rooms = state.create_rooms(5, visits=state.map_visit_count)
            state.current_room_index = 0
            state.load_room(0)
            state.player_y = max(1, min(state.ROOM_HEIGHT - 2, ny))
            state.player_x = 1
            state.last_move_time = now
            render.render_map()
            return
        nx = state.ROOM_WIDTH - 2
    # clamp top-bottom borders (no room transitions for vertical movement)
    if ny <= 0:
        ny = 1
    if ny >= state.ROOM_HEIGHT - 1:
        ny = state.ROOM_HEIGHT - 2

    ny = max(0, min(state.ROOM_HEIGHT - 1, ny))
    nx = max(0, min(state.ROOM_WIDTH - 1, nx))

    # stepping into wall or rock? abort (walls and rocks are impassable)
    try:
        if state.current_map[ny][nx] in (state.WALL_CHAR, getattr(state, 'H_WALL_CHAR', state.WALL_CHAR), '^'):
            return
    except Exception:
        # fallback to previous behavior
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


def _battle_win():
    enemy = state.current_battle_enemy or {}
    reward = enemy.get('reward', 0)
    state.count += reward
    # show victory splash with earned resources
    try:
        render.display_victory_splash(reward)
        time.sleep(2)
    except Exception:
        pass
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
    state.current_battle_status = {}
    # if this was a boss, move to the last room of the current floor (room 5 out of 5)
    # and prepare for the next floor on the next room transition
    try:
        if enemy.get('is_boss'):
            # Place player at room index 4 (the 5th room - room "5" of the floor)
            state.current_room_index = 4
            render.flash_message(f'Boss defeated! You may now progress to the next floor.')
            # mark this floor's boss as defeated and remove boss from the persistent room data
            try:
                # remove boss from the room data structure for the current room index
                cri = int(getattr(state, 'current_room_index', 0))
                if getattr(state, 'rooms', None) and 0 <= cri < len(state.rooms):
                    try:
                        state.rooms[cri].get('enemies', {}).pop(state.current_battle_pos, None)
                    except Exception:
                        pass
                # mark boss defeated for this floor
                fb = getattr(state, 'floor_boss_defeated', {})
                try:
                    floor = int(getattr(state, 'current_floor', 1))
                except Exception:
                    floor = getattr(state, 'current_floor', 1)
                fb[floor] = True
                state.floor_boss_defeated = fb
            except Exception:
                pass
            # upgrade shop contents for deeper floors (append stronger items once)
            try:
                existing_names = {i.get('name') for i in state.shop_items}
                high_items = [
                    {'key': '9', 'name': 'Greater Sword', 'cost': 800, 'type': 'weapon', 'amount': 20, 'purchased': False},
                    {'key': '10', 'name': 'Elite Armour', 'cost': 700, 'type': 'armour', 'amount': 20, 'purchased': False},
                    {'key': '11', 'name': 'Mega Potion', 'cost': 450, 'type': 'consumable', 'subtype': 'heal', 'amount': 400, 'purchased': False},
                ]
                for it in high_items:
                    if it['name'] not in existing_names:
                        state.shop_items.append(it)
            except Exception:
                pass
            # increase the ceiling on action upgrades so players can progress further
            try:
                for a in getattr(state, 'action_upgrades', []):
                    a['max_level'] = int(a.get('max_level', 1)) + 1
            except Exception:
                pass
    except Exception:
        pass
    state.game_state = 'explore'
    render.clear_screen()
    render.render_map()
    persistence.save_game()


def _battle_lose():
    render.display_death_splash()
    time.sleep(3)
    try:
        run_best = int(getattr(state, 'run_max_count', 0))
    except Exception:
        run_best = 0
    meta_reward = max(1, run_best // 1000)
    state.meta_currency = getattr(state, 'meta_currency', 0) + meta_reward
    persistence.save_game()
    state.current_battle_enemy = None
    state.current_battle_pos = None
    state.current_battle_status = {}
    state.game_state = 'meta'
    render.display_meta_upgrades(meta_reward)


def _enemy_retaliate(enemy):
    # compute enemy attack after debuff
    atk = max(0, enemy.get('atk', 0) - state.current_battle_status.get('enemy_debuff', 0))
    # compute block from defence and shield
    shield = state.current_battle_status.get('player_shield', 0)
    defense = getattr(state, 'defense', 0)
    damage = max(0, atk - (defense + shield))
    # consume shield
    state.current_battle_status['player_shield'] = max(0, shield - max(0, atk - defense))
    if damage > 0:
        state.player_hp -= damage
    # enemy may have special effects (e.g., Teto stun)
    try:
        special = enemy.get('special')
    except Exception:
        special = None
    if special and isinstance(special, dict):
        if special.get('type') == 'stun':
            try:
                import random as _random
                if _random.random() < float(special.get('chance', 0)):
                    # apply stun: mark player stunned for duration turns
                    dur = int(special.get('duration', 1))
                    state.current_battle_status['player_stunned'] = True
                    state.current_battle_status['stun_duration'] = dur
                    render.flash_message(f"{enemy.get('name','Enemy')} stunned you for {dur} turn(s)!")
            except Exception:
                pass
    # check death
    if state.player_hp <= 0:
        _battle_lose()
        return False
    return True


def _get_action_upgrade_bonus(action_id: str) -> int:
    """Return the cumulative bonus amount for an action upgrade id."""
    try:
        total = 0
        for upg in getattr(state, 'action_upgrades', []):
            if upg.get('id') == action_id:
                total += int(upg.get('level', 0)) * int(upg.get('amount', 0))
        return total
    except Exception:
        return 0


def execute_code():
    """Red: direct attack (resourceless)."""
    if state.game_state != 'battle' or not state.current_battle_enemy:
        return
    # if stunned, player cannot perform this action (but enemy still retaliates)
    if state.current_battle_status.get('player_stunned', False):
        # consume one stun turn
        state.current_battle_status['stun_duration'] = state.current_battle_status.get('stun_duration', 0) - 1
        if state.current_battle_status['stun_duration'] <= 0:
            state.current_battle_status['player_stunned'] = False
            state.current_battle_status['stun_duration'] = 0
        render.flash_message('You are stunned and cannot act this turn!')
        alive = _enemy_retaliate(state.current_battle_enemy)
        if alive:
            render.display_battle()
        return
    cost = 1
    sp = state.current_battle_status.get('skill_points', 0)
    if sp < cost:
        render.flash_message('Not enough Skill Points')
        return
    state.current_battle_status['skill_points'] = sp - cost
    enemy = state.current_battle_enemy
    # base damage from weapon/attack plus player buff and execute upgrades
    base = int(state.attack + state.current_battle_status.get('player_buff', 0))
    bonus = _get_action_upgrade_bonus('execute_power')
    damage = max(1, int(base + bonus))
    enemy['hp'] -= damage
    render.flash_message(f'Execute Code deals {damage} damage (-{cost} SP)')
    if enemy['hp'] <= 0:
        _battle_win()
        return
    # enemy retaliates
    alive = _enemy_retaliate(enemy)
    if alive:
        render.display_battle()


def defend_code():
    """Blue: gain a temporary shield that blocks incoming damage."""
    if state.game_state != 'battle' or not state.current_battle_enemy:
        return
    # if stunned, player cannot perform this action (but enemy still retaliates)
    if state.current_battle_status.get('player_stunned', False):
        state.current_battle_status['stun_duration'] = state.current_battle_status.get('stun_duration', 0) - 1
        if state.current_battle_status['stun_duration'] <= 0:
            state.current_battle_status['player_stunned'] = False
            state.current_battle_status['stun_duration'] = 0
        render.flash_message('You are stunned and cannot act this turn!')
        alive = _enemy_retaliate(state.current_battle_enemy)
        if alive:
            render.display_battle()
        return
    cost = 2
    sp = state.current_battle_status.get('skill_points', 0)
    if sp < cost:
        render.flash_message('Not enough Skill Points')
        return
    state.current_battle_status['skill_points'] = sp - cost
    # shield scales with player's defense stat plus defend upgrades
    base = 8
    shield_amount = base + int(getattr(state, 'defense', 0) * 0.5)
    shield_amount += _get_action_upgrade_bonus('defend_power')
    state.current_battle_status['player_shield'] = state.current_battle_status.get('player_shield', 0) + shield_amount
    render.flash_message(f'Defend Code grants {shield_amount} shield (-{cost} SP)')
    # enemy retaliates (shield will absorb)
    alive = _enemy_retaliate(state.current_battle_enemy)
    if alive:
        render.display_battle()


def recover():
    """White: heal the player."""
    if state.game_state != 'battle' or not state.current_battle_enemy:
        return
    # Recover: regenerate skill points (does not heal HP)
    sp = state.current_battle_status.get('skill_points', 0)
    sp_max = state.current_battle_status.get('skill_points_max', sp)
    regen = 3 + _get_action_upgrade_bonus('recover_power')
    new_sp = min(sp_max, sp + regen)
    gained = new_sp - sp
    if gained <= 0:
        render.flash_message('Skill Points already full')
        return
    state.current_battle_status['skill_points'] = new_sp
    render.flash_message(f'Recover restores {gained} SP (+{gained} SP)')
    # if player was stunned, this counts as the allowed action and reduces stun duration
    if state.current_battle_status.get('player_stunned', False):
        state.current_battle_status['stun_duration'] = state.current_battle_status.get('stun_duration', 0) - 1
        if state.current_battle_status['stun_duration'] <= 0:
            state.current_battle_status['player_stunned'] = False
            state.current_battle_status['stun_duration'] = 0
    # enemy retaliates
    alive = _enemy_retaliate(state.current_battle_enemy)
    if alive:
        render.display_battle()


def hack():
    """Black: debuff enemy attack (reduce enemy atk for the fight)."""
    if state.game_state != 'battle' or not state.current_battle_enemy:
        return
    # if stunned, player cannot perform this action (but enemy still retaliates)
    if state.current_battle_status.get('player_stunned', False):
        state.current_battle_status['stun_duration'] = state.current_battle_status.get('stun_duration', 0) - 1
        if state.current_battle_status['stun_duration'] <= 0:
            state.current_battle_status['player_stunned'] = False
            state.current_battle_status['stun_duration'] = 0
        render.flash_message('You are stunned and cannot act this turn!')
        alive = _enemy_retaliate(state.current_battle_enemy)
        if alive:
            render.display_battle()
        return
    cost = 2
    sp = state.current_battle_status.get('skill_points', 0)
    if sp < cost:
        render.flash_message('Not enough Skill Points')
        return
    state.current_battle_status['skill_points'] = sp - cost
    reduce_amount = 3 + int(state.map_visit_count * 0.5) + _get_action_upgrade_bonus('hack_power')
    # apply debuff but cap the total enemy_debuff to 10
    prev = state.current_battle_status.get('enemy_debuff', 0)
    new_debuff = prev + reduce_amount
    DEBUFF_CAP = 10
    if new_debuff > DEBUFF_CAP:
        new_debuff = DEBUFF_CAP
    state.current_battle_status['enemy_debuff'] = new_debuff
    render.flash_message(f'Hack reduces enemy attack by {reduce_amount} (total debuff {new_debuff}/{DEBUFF_CAP}) (-{cost} SP)')
    # enemy retaliates with reduced attack
    alive = _enemy_retaliate(state.current_battle_enemy)
    if alive:
        render.display_battle()


def debug_action():
    """Green: buff player's attack for the fight."""
    if state.game_state != 'battle' or not state.current_battle_enemy:
        return
    # if stunned, player cannot perform this action (but enemy still retaliates)
    if state.current_battle_status.get('player_stunned', False):
        state.current_battle_status['stun_duration'] = state.current_battle_status.get('stun_duration', 0) - 1
        if state.current_battle_status['stun_duration'] <= 0:
            state.current_battle_status['player_stunned'] = False
            state.current_battle_status['stun_duration'] = 0
        render.flash_message('You are stunned and cannot act this turn!')
        alive = _enemy_retaliate(state.current_battle_enemy)
        if alive:
            render.display_battle()
        return
    cost = 2
    sp = state.current_battle_status.get('skill_points', 0)
    if sp < cost:
        render.flash_message('Not enough Skill Points')
        return
    state.current_battle_status['skill_points'] = sp - cost
    buff = max(1, int(state.attack * 0.4)) + _get_action_upgrade_bonus('debug_power')
    state.current_battle_status['player_buff'] = state.current_battle_status.get('player_buff', 0) + buff
    render.flash_message(f'Debug increases your attack by {buff} (-{cost} SP)')
    # enemy retaliates
    alive = _enemy_retaliate(state.current_battle_enemy)
    if alive:
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

