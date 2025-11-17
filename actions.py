import time
import os
import state
import render
import persistence


def on_space():
    """Handle space key presses once per physical press.

    Prevents holding space from repeatedly granting resources by
    ignoring repeated events until a release is detected.
    Also keeps a small rate limit as a safety net.
    """
    # if space is already considered pressed, ignore (handles OS key-repeat)
    if state.space_pressed:
        return
    state.space_pressed = True
    now = time.time()
    min_interval = 1.0 / 10.0
    if now - state.last_space_time < min_interval:
        return
    state.last_space_time = now
    state.count += state.per_click
    if state.game_state == 'incremental':
        render.display_incremental()


def on_space_release():
    """Handler to be called when the space key is released.

    Resets the `space_pressed` flag so the next keydown will be handled.
    """
    state.space_pressed = False


def start_new_game():
    """Start a new game."""
    if state.game_state != 'start_menu':
        return
    persistence.reset_game()
    state.game_state = 'menu'
    render.display_menu()


def load_game_from_menu():
    """Load game from the start menu."""
    if state.game_state != 'start_menu':
        return
    if not persistence.has_save_file():
        return
    persistence.load_game()
    state.game_state = 'menu'
    render.display_menu()


def buy_upgrade_key(key: str):
    """Buy an upgrade when in incremental view."""
    if state.game_state != 'incremental':
        return
    for upg in state.upgrades:
        if upg['key'] == key:
            if upg['purchased']:
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
    """Buy an item from the shop when in shop view."""
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
            # add structured inventory entry with ascii art and level
            item_obj = {
                'name': item['name'],
                'type': item['type'],
                'level': 1,
                'ascii': ''
            }
            if item['type'] == 'weapon':
                # Use the small dart monkey ascii if present
                ascii_path = os.path.join(os.path.dirname(__file__), 'ascii', 'dart_monkey_small.txt')
                try:
                    with open(ascii_path, 'r', encoding='utf-8') as af:
                        item_obj['ascii'] = af.read().rstrip('\n')
                except Exception:
                    # fallback to a simple sword ascii
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
    """Equip an inventory item by numeric key when inventory view is open.
    key is a string like '1','2',...
    """
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
        # equip weapon: compute attack
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


def move(dx, dy):
    now = time.time()
    # enforce movement cooldown
    if now - state.last_move_time < state.MOVE_INTERVAL:
        return
    with state.movement_lock:
        new_x = state.player_x + dx
        new_y = state.player_y + dy
        valid_x = 0 <= new_x < state.ROOM_WIDTH
        valid_y = 0 <= new_y < state.ROOM_HEIGHT
        if not (valid_x and valid_y):
            return  # Block invalid movement
        if state.current_map[new_y][new_x] == state.WALL_CHAR:
            return  # Block movement into walls
        state.player_x = new_x
        state.player_y = new_y
        state.last_move_time = now
        feature = state.TELEPORTS.get((state.player_y, state.player_x))
        if feature:
            enter_feature(feature)
            return
        # check for enemy encounter
        pos = (state.player_y, state.player_x)
        if pos in state.enemies:
            enter_battle(pos)
            return


def enter_feature(name: str):
    state.prev_state = state.game_state
    state.prev_player_pos = (state.player_y, state.player_x)
    if name == 'shop':
        state.game_state = 'shop'
        render.display_shop()


def return_from_shop():
    if state.game_state != 'shop':
        return
    prev_pos = state.prev_player_pos
    if isinstance(prev_pos, tuple) and len(prev_pos) == 2:
        py, px = prev_pos  # type: ignore
        state.player_x = px
        state.player_y = py
    state.game_state = 'explore'
    render.clear_screen()
    render.render_map()


def toggle_inventory():
    if not state.has_bag:
        return
    if state.game_state == 'inventory':
        # Return to menu instead of map
        render.switch_to_menu()
    else:
        state.game_state = 'inventory'
        render.display_inventory()


def enter_battle(pos):
    """Begin a battle with the enemy at pos."""
    state.prev_state = state.game_state
    state.prev_player_pos = (state.player_y, state.player_x)
    enemy = state.enemies.get(pos)
    if not enemy:
        return
    # copy enemy data for current battle
    state.current_battle_enemy = dict(enemy)
    state.current_battle_pos = pos
    state.game_state = 'battle'
    render.display_battle()


def battle_attack():
    """Player attacks the current enemy; simple turn-based exchange."""
    if state.game_state != 'battle' or not state.current_battle_enemy:
        return
    enemy = state.current_battle_enemy
    # player's damage (ensure at least 1)
    damage = max(1, state.attack)
    enemy['hp'] -= damage
    if enemy['hp'] <= 0:
        # enemy defeated
        reward = enemy.get('reward', 0)
        state.count += reward
        # remove enemy from map
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

    # enemy retaliates
    state.player_hp -= enemy.get('atk', 0)
    if state.player_hp <= 0:
        # player defeated: show death splash, perform roguelite reset
        render.display_death_splash()
        # give player a moment to see the splash
        time.sleep(3)
        # reset everything (currencies, inventory, upgrades, equipped, etc.)
        persistence.reset_game()
        # ensure HP is restored for next run
        state.player_hp = state.player_max_hp
        # persist reset state (overwrites any previous save)
        persistence.save_game()
        # return to start menu
        state.game_state = 'start_menu'
        render.display_start_menu()
        return

    # still alive: update battle screen
    render.display_battle()


def flee_battle():
    """Flee the battle and return to where player was before encounter (menu or map)."""
    if state.game_state != 'battle':
        return
    # restore previous position if available
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
    """Dispatch numeric key based on current view.

    - start_menu: 1 = new, 2 = load
    - inventory: equip slot
    - shop: buy shop item
    - incremental: buy upgrade
    """
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
