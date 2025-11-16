import time
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
    min_interval = 1.0 / 6.0
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
            if item['type'] == 'weapon':
                state.attack += item['amount']
            elif item['type'] == 'armour':
                state.defense += item['amount']
            elif item['type'] == 'bag':
                state.has_bag = True
                state.inventory_capacity += item['amount'] * 10
            try:
                state.inventory.append(item['name'])
            except Exception:
                pass
            persistence.save_game()
            break
    render.display_shop()


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
