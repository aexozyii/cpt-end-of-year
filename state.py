import threading

# --- Shared game state ---
count = 0
per_click = 1
# view state: 'menu', 'incremental', 'explore', 'shop', 'inventory'
game_state = 'menu'

movement_lock = threading.Lock()
last_space_time = 0.0

import os
SAVE_FILE = os.path.join(os.path.dirname(__file__), 'save.json')

# incremental upgrades
upgrades = [
    {'key': '1', 'name': 'Better Fingers', 'cost': 10,  'type': 'add',  'amount': 1, 'purchased': False},
    {'key': '2', 'name': 'Auto Clicker',  'cost': 50,  'type': 'add',  'amount': 5, 'purchased': False},
    {'key': '3', 'name': 'Double Tap',    'cost': 200, 'type': 'mult', 'amount': 2, 'purchased': False},
]

# Shop items
shop_items = [
    {'key': '1', 'name': 'Sword', 'cost': 100, 'type': 'weapon', 'amount': 5, 'purchased': False},
    {'key': '2', 'name': 'Armour', 'cost': 80,  'type': 'armour', 'amount': 5, 'purchased': False},
    {'key': '3', 'name': 'Bag',    'cost': 50,  'type': 'bag',    'amount': 1, 'purchased': False},
]

# Player combat/stats and inventory
attack = 0
defense = 0
has_bag = False
inventory = []
inventory_capacity = 0

# Map constants
ROOM_WIDTH = 20
ROOM_HEIGHT = 10
PLAYER_CHAR = '~'
WALL_CHAR = '|'
FLOOR_CHAR = '.'
player_y, player_x = 4, 10


def create_map():
    game_map = [[FLOOR_CHAR for _ in range(ROOM_WIDTH)] for _ in range(ROOM_HEIGHT)]
    for x in range(ROOM_WIDTH):
        game_map[0][x] = WALL_CHAR
        game_map[ROOM_HEIGHT - 1][x] = WALL_CHAR
    for y in range(ROOM_HEIGHT):
        game_map[y][0] = WALL_CHAR
        game_map[y][ROOM_WIDTH - 1] = WALL_CHAR
    return game_map

current_map = create_map()

# Teleport tiles: (y,x) -> feature
TELEPORTS = {
    (1, ROOM_WIDTH // 2): 'shop'
}

# temporary holders for feature transitions
prev_state = None
prev_player_pos = None
