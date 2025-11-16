import json
import os
import state


def save_game():
    """Save player state to disk (JSON)."""
    try:
        state_dict = {
            'count': state.count,
            'per_click': state.per_click,
            'player_x': state.player_x,
            'player_y': state.player_y,
            'upgrades': {
                    upg['key']: upg['purchased']
                    for upg in state.upgrades},
            'shop': {
                item['key']: item['purchased']
                for item in state.shop_items},
            'attack': state.attack,
            'defense': state.defense,
            'has_bag': state.has_bag,
            'inventory': state.inventory,
            'inventory_capacity': state.inventory_capacity,
        }
        with open(state.SAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state_dict, f)
    except Exception:
        pass


def load_game():
    """Load player state from disk if present."""
    if not os.path.exists(state.SAVE_FILE):
        return
    try:
        with open(state.SAVE_FILE, 'r', encoding='utf-8') as f:
            s = json.load(f)
        state.count = int(s.get('count', state.count))
        state.per_click = int(s.get('per_click', state.per_click))
        px = int(s.get('player_x', state.player_x))
        py = int(s.get('player_y', state.player_y))
        if 0 <= px < state.ROOM_WIDTH and 0 <= py < state.ROOM_HEIGHT:
            state.player_x = px
            state.player_y = py
        saved_upgrades = s.get('upgrades', {})
        for upg in state.upgrades:
            upg['purchased'] = bool(saved_upgrades.get(upg['key'], False))
        shop_state = s.get('shop', {})
        for item in state.shop_items:
            item['purchased'] = bool(shop_state.get(item['key'], False))
        state.attack = int(s.get('attack', state.attack))
        state.defense = int(s.get('defense', state.defense))
        state.has_bag = bool(s.get('has_bag', state.has_bag))
        state.inventory = s.get('inventory', state.inventory)
        state.inventory_capacity = int(
            s.get('inventory_capacity', state.inventory_capacity))
    except Exception:
        return


def has_save_file():
    """Check if a save file exists."""
    return os.path.exists(state.SAVE_FILE)


def reset_game():
    """Reset all game state to defaults for a new game."""
    state.count = 0
    state.per_click = 1
    state.player_x = state.ROOM_WIDTH // 2
    state.player_y = state.ROOM_HEIGHT // 2
    state.attack = 0
    state.defense = 0
    state.has_bag = False
    state.inventory = []
    state.inventory_capacity = 0
    for upg in state.upgrades:
        upg['purchased'] = False
    for item in state.shop_items:
        item['purchased'] = False
