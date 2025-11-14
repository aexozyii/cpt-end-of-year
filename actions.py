import time
import state
import render
import persistence


def on_space():
    """Handle space presses with a rate limit (max ~6 clicks/sec)."""
    now = time.time()
    min_interval = 1.0 / 6.0
    if now - state.last_space_time < min_interval:
        return
    state.last_space_time = now
    state.count += state.per_click
    if state.game_state == 'incremental':
        render.display_incremental()


def buy_upgrade_key(key: str):
    """Buy the upgrade with the given numeric key (if possible). Only in incremental view."""
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
    with state.movement_lock:
        new_x = state.player_x + dx
        new_y = state.player_y + dy
        if 0 <= new_x < state.ROOM_WIDTH and 0 <= new_y < state.ROOM_HEIGHT and state.current_map[new_y][new_x] != state.WALL_CHAR:
            state.player_x = new_x
            state.player_y = new_y
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
    try:
        py, px = state.prev_player_pos
        state.player_x = px
        state.player_y = py
    except Exception:
        pass
    state.game_state = 'explore'
    render.clear_screen()
    render.render_map()


def toggle_inventory():
    if not state.has_bag:
        return
    if state.game_state == 'inventory':
        state.game_state = 'explore'
        render.clear_screen()
        render.render_map()
    else:
        state.game_state = 'inventory'
        render.display_inventory()
