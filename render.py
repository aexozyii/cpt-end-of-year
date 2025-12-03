# state.py (fixed, preserves original design but repaired bugs and fragile imports)

import threading
import random
import os
import sys

# Import enemy templates if available (enemies_data should export ENEMY_TEMPLATES)
try:
    from enemies_data import ENEMY_TEMPLATES
except Exception:
    ENEMY_TEMPLATES = {}

# Colorama: optional, best-effort; DO NOT attempt to pip-install at import time.
try:
    from colorama import Fore, Style, init as _colorama_init
    _colorama_init(autoreset=True)
except Exception:
    class _NoStyle:
        RESET_ALL = ''
    class _NoFore:
        LIGHTGREEN_EX = RED = BLUE = YELLOW = CYAN = LIGHTRED_EX = WHITE = BLACK = LIGHTBLUE_EX = ''
    Fore = _NoFore()
    Style = _NoStyle()

# Map constants
ROOM_WIDTH = 50
ROOM_HEIGHT = 50
PLAYER_CHAR = f'{Fore.LIGHTRED_EX}~{Style.RESET_ALL}'
WALL_CHAR = '│'
H_WALL_CHAR = '─'
FLOOR_CHAR = '.'

# UI flags
showing_battle_descriptions = False

# Default player position
player_y, player_x = 4, 10

# How many times player visited map (increases difficulty)
map_visit_count = 0

# Multi-room world data structures
rooms = []
current_room_index = 0

# Create a single room with decorations, enemies, teleports etc.
def create_room(visits: int = 0):
    game_map = [[FLOOR_CHAR for _ in range(ROOM_WIDTH)] for _ in range(ROOM_HEIGHT)]
    # outer walls
    for x in range(ROOM_WIDTH):
        game_map[0][x] = H_WALL_CHAR
        game_map[ROOM_HEIGHT - 1][x] = H_WALL_CHAR
    for y in range(ROOM_HEIGHT):
        game_map[y][0] = WALL_CHAR
        game_map[y][ROOM_WIDTH - 1] = WALL_CHAR

    exits = {}

    # scale counts by visits (clamped)
    num_exclaims = random.randint(1, max(1, min(6, 1 + visits)))
    num_enemies = random.randint(2 + visits, min(12, 3 + visits * 2))
    num_rocks = random.randint(8, max(12, 15 + visits))
    num_trees = random.randint(6, max(10, 12 + visits))
    num_water = random.randint(3, max(6, 7 + visits // 2))

    # available interior cells (not walls)
    avail = [(y, x) for y in range(1, ROOM_HEIGHT - 1) for x in range(1, ROOM_WIDTH - 1)]
    random.shuffle(avail)

    exclaim_positions = avail[:num_exclaims]
    enemy_positions = avail[num_exclaims:num_exclaims + num_enemies]
    rock_positions = avail[num_exclaims + num_enemies:num_exclaims + num_enemies + num_rocks]
    tree_positions = avail[num_exclaims + num_enemies + num_rocks:num_exclaims + num_enemies + num_rocks + num_trees]
    water_positions = avail[num_exclaims + num_enemies + num_rocks + num_trees:num_exclaims + num_enemies + num_rocks + num_trees + num_water]

    for (ey, ex) in exclaim_positions:
        game_map[ey][ex] = '!'

    # large trees (decorative but passable)
    for (ty, tx) in tree_positions:
        game_map[ty][tx] = 'T'
        if random.random() < 0.5:
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ny, nx = ty + dy, tx + dx
                if 1 <= ny < ROOM_HEIGHT - 1 and 1 <= nx < ROOM_WIDTH - 1:
                    if game_map[ny][nx] == FLOOR_CHAR:
                        game_map[ny][nx] = 'T'

    # water tiles (impassable)
    for (wy, wx) in water_positions:
        game_map[wy][wx] = '≈'
        if random.random() < 0.3:
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ny, nx = wy + dy, wx + dx
                if 1 <= ny < ROOM_HEIGHT - 1 and 1 <= nx < ROOM_WIDTH - 1:
                    if game_map[ny][nx] == FLOOR_CHAR:
                        game_map[ny][nx] = '≈'

    # rocks (obstacles)
    for (ry, rx) in rock_positions:
        game_map[ry][rx] = '^'
        if random.random() < 0.4:
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ny, nx = ry + dy, rx + dx
                if 1 <= ny < ROOM_HEIGHT - 1 and 1 <= nx < ROOM_WIDTH - 1:
                    if game_map[ny][nx] == FLOOR_CHAR:
                        game_map[ny][nx] = '^'

    # torches on walls
    for i in range(min(6, 4 + visits)):
        torch_y = random.choice([1, ROOM_HEIGHT - 2])
        torch_x = random.randint(2, ROOM_WIDTH - 3)
        if 0 <= torch_y < ROOM_HEIGHT and 0 <= torch_x < ROOM_WIDTH:
            if game_map[torch_y][torch_x] in (FLOOR_CHAR, H_WALL_CHAR):
                game_map[torch_y][torch_x] = '*'

    # create enemies dict for this room
    enemies_local = {}
    for (ey, ex) in enemy_positions:
        if game_map[ey][ex] not in (FLOOR_CHAR, '!'):
            continue
        if random.random() < 0.6:
            enemies_local[(ey, ex)] = {
                'name': 'Human',
                'hp': 80 + visits * 10,
                'atk': 4 + visits,
                'reward': int(200 * (1 + 0.2 * visits)),
                'ascii': '  ,      ,\n (\\_/)\n (o.o)\n  >^ '
            }
        else:
            enemies_local[(ey, ex)] = {
                'name': 'Dart Monkey',
                'hp': 130 + visits * 18,
                'atk': 12 + visits * 2,
                'reward': int(450 * (1 + 0.2 * visits)),
                'ascii': "  ,--.\n (____)\n /||\\\\\n  ||"
            }

    # optional fountain
    fountain_pos = None
    tail_idx = num_exclaims + num_enemies + num_rocks + num_trees + num_water
    if len(avail) > tail_idx:
        fpos = avail[tail_idx]
        fy, fx = fpos
        game_map[fy][fx] = 'H'
        fountain_pos = (fy, fx)

    teleport = {}

    return {'map': game_map, 'enemies': enemies_local, 'teleport': teleport, 'fountain': fountain_pos, 'exits': exits}


def create_rooms(n: int = 5, visits: int = 0):
    """Generate n rooms, assign shop and action_upgrades rooms, place boss in final room."""
    n = max(1, min(int(n), 5))
    rs = [create_room(visits) for _ in range(n)]

    # pick a shop room and carve center
    shop_idx = random.randrange(len(rs))
    rm = rs[shop_idx]
    sx = ROOM_WIDTH // 2
    sy = ROOM_HEIGHT // 2
    rm['teleport'] = {(sy, sx): 'shop'}

    # ensure shop tile is free of enemies/events
    try:
        to_remove = []
        for (ey, ex) in list(rm.get('enemies', {}).keys()):
            if abs(ey - sy) <= 1 and abs(ex - sx) <= 1:
                to_remove.append((ey, ex))
        for k in to_remove:
            rm['enemies'].pop(k, None)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                cy, cx = sy + dy, sx + dx
                if 0 <= cy < ROOM_HEIGHT and 0 <= cx < ROOM_WIDTH:
                    if rm['map'][cy][cx] in ('!', 'H'):
                        rm['map'][cy][cx] = FLOOR_CHAR
        rm['map'][sy][sx] = FLOOR_CHAR
    except Exception:
        pass

    # action-upgrade room (different from shop if possible)
    try:
        candidates = [i for i in range(len(rs)) if i != shop_idx]
        if candidates:
            upgrade_idx = random.choice(candidates)
            urm = rs[upgrade_idx]
            ux = ROOM_WIDTH // 2
            uy = ROOM_HEIGHT // 2 - 3
            urm['teleport'] = urm.get('teleport', {})
            urm['teleport'][(uy, ux)] = 'action_upgrades'
            try:
                urm['map'][uy][ux] = 'U'
            except Exception:
                pass
    except Exception:
        pass

    # ensure boss is in final room (index len(rs)-1); if shop chosen as last room, move shop
    boss_idx = len(rs) - 1
    if shop_idx == boss_idx and len(rs) > 1:
        # move shop to another room
        for i in range(len(rs)):
            if i != boss_idx:
                # clear old shop and assign new
                rs[shop_idx]['teleport'] = {}
                shop_idx = i
                rm = rs[shop_idx]
                rm['teleport'] = {(ROOM_HEIGHT // 2, ROOM_WIDTH // 2): 'shop'}
                break

    # place boss using create_enemy_instance helper (safe)
    try:
        brow = rs[boss_idx]
        bx = random.randint(2, ROOM_WIDTH - 3)
        by = random.randint(2, ROOM_HEIGHT - 3)
        boss_key = 'teto_boss'
        boss_instance = create_enemy_instance(boss_key, visits)
        boss_instance['is_boss'] = True
        # scale boss further
        boss_instance['hp'] = boss_instance.get('hp', 300) + visits * 80
        boss_instance['atk'] = boss_instance.get('atk', 20) + visits * 5
        boss_instance['reward'] = int(boss_instance.get('reward', 1500) * (1 + 0.5 * visits))
        brow['enemies'][(by, bx)] = boss_instance
    except Exception:
        brow['enemies'][(by, bx)] = {
            'name': 'Room Boss',
            'hp': 350 + visits * 50,
            'atk': 20 + visits * 3,
            'reward': int(1500 * (1 + 0.25 * visits)),
            'ascii': '(#B#)',
            'is_boss': True
        }

    # Link rooms left-right: carve openings and set 'exits'
    opening_size = 3
    half = opening_size // 2
    cy = ROOM_HEIGHT // 2
    for i in range(len(rs)):
        rs[i]['exits'] = {}
    for i in range(len(rs)):
        rm = rs[i]
        if i > 0:
            left_room = rs[i - 1]
            for dy in range(-half, half + 1):
                oy = cy + dy
                ox = 0
                if 0 <= oy < ROOM_HEIGHT:
                    rm['map'][oy][ox] = FLOOR_CHAR
                    rm['exits'][(oy, ox)] = 'left'
                    left_room['map'][oy][ROOM_WIDTH - 1] = FLOOR_CHAR
                    left_room['exits'][(oy, ROOM_WIDTH - 1)] = 'right'
                    rm['enemies'].pop((oy, ox), None)
                    left_room['enemies'].pop((oy, ROOM_WIDTH - 1), None)
                    if rm['map'][oy][ox] in ('!', 'H'):
                        rm['map'][oy][ox] = FLOOR_CHAR
                    if left_room['map'][oy][ROOM_WIDTH - 1] in ('!', 'H'):
                        left_room['map'][oy][ROOM_WIDTH - 1] = FLOOR_CHAR
        if i < len(rs) - 1:
            right_room = rs[i + 1]
            for dy in range(-half, half + 1):
                oy = cy + dy
                ox = ROOM_WIDTH - 1
                if 0 <= oy < ROOM_HEIGHT:
                    rm['map'][oy][ox] = FLOOR_CHAR
                    rm['exits'][(oy, ox)] = 'right'
                    right_room['map'][oy][0] = FLOOR_CHAR
                    right_room['exits'][(oy, 0)] = 'left'
                    rm['enemies'].pop((oy, ox), None)
                    right_room['enemies'].pop((oy, 0), None)
                    if rm['map'][oy][ox] in ('!', 'H'):
                        rm['map'][oy][ox] = FLOOR_CHAR
                    if right_room['map'][oy][0] in ('!', 'H'):
                        right_room['map'][oy][0] = FLOOR_CHAR

    return rs


def load_room(idx: int):
    """Load a room into the legacy globals used elsewhere (current_map, enemies, TELEPORTS)."""
    global current_room_index, rooms, current_map, enemies, TELEPORTS, EXITS
    current_room_index = idx
    room = rooms[idx]
    current_map = room.get('map', create_room(0)['map'])
    enemies = dict(room.get('enemies', {}))
    TELEPORTS = dict(room.get('teleport', {}))
    EXITS = dict(room.get('exits', {}))
    return


# core run state (incremental + exploration)
count = 0
per_click = 1
run_max_count = 0
game_state = 'start_menu'

movement_lock = threading.Lock()
last_space_time = 0.0
MOVE_INTERVAL = 0.06
last_move_time = 0.0
space_pressed = False

SAVE_FILE = os.path.join(os.path.dirname(__file__), 'save.json')

# incremental upgrades (original content preserved)
upgrades = [
    {'key': '1', 'name': 'top left', 'cost': 10,   'type': 'add',  'amount': 1,  'purchased': False},
    {'key': '2', 'name': 'sumsum',  'cost': 50,   'type': 'add',  'amount': 5,  'purchased': False},
    {'key': '3', 'name': 'dt',    'cost': 200,  'type': 'mult', 'amount': 2,  'purchased': False},
    {'key': '4', 'name': 'bottom right', 'cost': 500,  'type': 'add',  'amount': 10, 'purchased': False, 'meta_req': 'unlock_tier1'},
    {'key': '5', 'name': 'my ball', 'cost': 1200, 'type': 'mult', 'amount': 1.5,'purchased': False, 'meta_req': 'unlock_tier1'},
    {'key': '6', 'name': 'yo bro...','cost': 3000, 'type': 'add',  'amount': 50, 'purchased': False, 'meta_req': 'unlock_tier1'},
    {'key': '7', 'name': 'Whatever you do, at the crossroads, do NOT turn left.',    'cost': 7000, 'type': 'mult', 'amount': 2,  'purchased': False, 'meta_req': 'unlock_tier2'},
    {'key': '8', 'name': 'yo bro. js play the game alrdy',  'cost': 15000,'type': 'add',  'amount': 200, 'purchased': False, 'meta_req': 'unlock_tier2'},
    {'key': '9', 'name': 'bro',  'cost': 50000,'type': 'mult', 'amount': 3,  'purchased': False, 'meta_req': 'unlock_tier2'},
]

# Shop items (preserved)
shop_items = [
    {'key': '1', 'name': 'Sword', 'cost': 100, 'type': 'weapon', 'amount': 5, 'purchased': False},
    {'key': '2', 'name': 'Armour', 'cost': 80,  'type': 'armour', 'amount': 5, 'purchased': False},
    {'key': '3', 'name': 'Bag',    'cost': 50,  'type': 'bag',    'amount': 1, 'purchased': False},
    {'key': '4', 'name': 'Health Potion', 'cost': 30,  'type': 'consumable', 'subtype': 'heal', 'amount': 50, 'purchased': False},
    {'key': '5', 'name': 'Large Potion',  'cost': 120, 'type': 'consumable', 'subtype': 'heal', 'amount': 150, 'purchased': False},
    {'key': '6', 'name': 'Health Amulet', 'cost': 200, 'type': 'accessory',  'subtype': 'max_hp', 'amount': 20, 'purchased': False},
    {'key': '7', 'name': 'Greater Amulet','cost': 800, 'type': 'accessory',  'subtype': 'max_hp', 'amount': 50, 'purchased': False},
    {'key': '8', 'name': 'Ring of Strength','cost':300,'type':'accessory','subtype':'attack','amount':5,'purchased':False},
]

# Action upgrades (preserved)
action_upgrades = [
    {'key': '1', 'id': 'execute_power', 'name': 'Execute Power', 'desc': 'Increase Execute damage', 'cost': 200, 'level': 0, 'max_level': 5, 'amount': 2},
    {'key': '2', 'id': 'defend_power',  'name': 'Defend Power',  'desc': 'Increase Defend shield',  'cost': 180, 'level': 0, 'max_level': 5, 'amount': 8},
    {'key': '3', 'id': 'recover_power', 'name': 'Recover Power', 'desc': 'Recover restores more SP', 'cost': 150, 'level': 0, 'max_level': 5, 'amount': 1},
    {'key': '4', 'id': 'hack_power',    'name': 'Hack Power',    'desc': 'Increase Hack debuff amount', 'cost': 160, 'level': 0, 'max_level': 5, 'amount': 1},
    {'key': '5', 'id': 'debug_power',   'name': 'Debug Power',   'desc': 'Increase Debug buff amount',  'cost': 160, 'level': 0, 'max_level': 5, 'amount': 1},
]

# Player combat stats and inventory (preserved)
attack = 0
defense = 0
has_bag = False
inventory = []
inventory_capacity = 0
equipped_weapon = None
equipped_armour = None
equipped_accessory = None

# Teleport markers
TELEPORTS = {}
EXITS = {}

def create_enemy_instance(enemy_key, visits):
    """
    Generates a fully-statted enemy dictionary from a template, scaled by visits.
    This is robust to missing templates (returns a sensible fallback).
    """
    tpl = ENEMY_TEMPLATES.get(enemy_key)
    if not tpl:
        # fallback generic
        base_hp = 60 + visits * 12
        atk = 5 + visits
        return {'name': 'Mook', 'hp': base_hp, 'atk': atk, 'reward': 50 + visits * 15, 'ascii': '(?)'}

    # safe reads
    base_hp = int(tpl.get('base_hp', 50))
    base_atk = int(tpl.get('base_atk', 5))
    base_reward = int(tpl.get('base_reward', 100))
    # choose scaling parameters heuristically
    if enemy_key == 'human':
        hp_scale, atk_scale, reward_mult = 10, 1, 0.2
    elif enemy_key == 'dart_monkey':
        hp_scale, atk_scale, reward_mult = 18, 2, 0.2
    elif enemy_key == 'teto_boss':
        hp_scale, atk_scale, reward_mult = 40, 4, 0.5
    else:
        hp_scale, atk_scale, reward_mult = 8, 1, 0.15

    hp_base = base_hp + visits * hp_scale
    if visits > 0:
        # moderate exponential-ish growth but avoid insane numbers for small tests
        hp = int(hp_base * (1 + visits * 0.5))
    else:
        hp = int(hp_base)

    atk = int(base_atk + visits * atk_scale)
    reward = int(base_reward * (1 + reward_mult * visits))

    inst = {
        'name': tpl.get('name', 'Enemy'),
        'hp': hp,
        'atk': atk,
        'reward': reward,
        'ascii': tpl.get('ascii', '')
    }
    if 'special' in tpl:
        inst['special'] = dict(tpl['special'])
    return inst


def create_map():
    """Legacy single-map generator retained for fallback/compatibility."""
    game_map = [[FLOOR_CHAR for _ in range(ROOM_WIDTH)] for _ in range(ROOM_HEIGHT)]
    for x in range(ROOM_WIDTH):
        game_map[0][x] = H_WALL_CHAR
        game_map[ROOM_HEIGHT - 1][x] = H_WALL_CHAR
    for y in range(ROOM_HEIGHT):
        game_map[y][0] = WALL_CHAR
        game_map[y][ROOM_WIDTH - 1] = WALL_CHAR

    rooms_local = []
    max_rooms = 5
    attempts = 0
    while len(rooms_local) < max_rooms and attempts < 200:
        attempts += 1
        w = random.randint(5, min(10, ROOM_WIDTH - 4))
        h = random.randint(3, min(6, ROOM_HEIGHT - 4))
        x1 = random.randint(1, ROOM_WIDTH - w - 2)
        y1 = random.randint(1, ROOM_HEIGHT - h - 2)
        x2 = x1 + w - 1
        y2 = y1 + h - 1
        overlaps = False
        for (ax1, ay1, ax2, ay2) in rooms_local:
            # check overlap
            if not (x2 < ax1 or x1 > ax2 or y2 < ay1 or y1 > ay2):
                overlaps = True
                break
        if overlaps:
            continue
        rooms_local.append((x1, y1, x2, y2))

    # carve rooms
    for (x1, y1, x2, y2) in rooms_local:
        for ry in range(y1, y2 + 1):
            for rx in range(x1, x2 + 1):
                if ry == y1 or ry == y2:
                    game_map[ry][rx] = H_WALL_CHAR
                elif rx == x1 or rx == x2:
                    game_map[ry][rx] = WALL_CHAR
                else:
                    game_map[ry][rx] = FLOOR_CHAR

    # choose a shop position roughly centered in a random room
    if rooms_local:
        shop_room = random.choice(rooms_local)
        sx = (shop_room[0] + shop_room[2]) // 2
        sy = (shop_room[1] + shop_room[3]) // 2
        shop_pos = (sy, sx)
    else:
        avail = [(y, x) for y in range(1, ROOM_HEIGHT - 1) for x in range(1, ROOM_WIDTH - 1)]
        shop_pos = random.choice(avail)

    global TELEPORTS
    TELEPORTS = {shop_pos: 'shop'}

    # place a fountain in a different room if possible
    fountain_pos = None
    if rooms_local and len(rooms_local) > 1:
        pool = [r for r in rooms_local if r != shop_room]
        froom = random.choice(pool)
        fx = random.randint(froom[0] + 1, froom[2] - 1)
        fy = random.randint(froom[1] + 1, froom[3] - 1)
        fountain_pos = (fy, fx)
        game_map[fy][fx] = 'H'

    visits = map_visit_count
    num_exclaims = random.randint(1, max(1, min(3, 1 + visits)))
    num_enemies = random.randint(1 + visits, min(6, 2 + visits))

    free_cells = []
    for (x1, y1, x2, y2) in rooms_local:
        for ry in range(y1 + 1, y2):
            for rx in range(x1 + 1, x2):
                if (ry, rx) != shop_pos and (ry, rx) != fountain_pos:
                    free_cells.append((ry, rx))
    random.shuffle(free_cells)

    exclaim_positions = free_cells[:num_exclaims]
    remaining = free_cells[num_exclaims:]
    enemy_positions = remaining[:num_enemies]

    for (ey, ex) in exclaim_positions:
        game_map[ey][ex] = '!'

    # create enemies dict properly (fix earlier bug)
    global enemies
    enemies = {}
    HUMAN_CHANCE = 0.6
    HUMAN_KEY = 'human'
    DART_MONKEY_KEY = 'dart_monkey'
    for (ey, ex) in enemy_positions:
        if random.random() < HUMAN_CHANCE:
            enemy_key = HUMAN_KEY
        else:
            enemy_key = DART_MONKEY_KEY
        enemies[(ey, ex)] = create_enemy_instance(enemy_key, visits)

    # boss placement
    boss_room_candidates = [r for r in rooms_local if r[0] == 1 or r[1] == 1 or r[2] == ROOM_WIDTH - 2 or r[3] == ROOM_HEIGHT - 2]
    if not boss_room_candidates and rooms_local:
        boss_room_candidates = rooms_local
    boss_pos = None
    if boss_room_candidates:
        brow = random.choice(boss_room_candidates)
        bx = random.randint(brow[0] + 1, brow[2] - 1)
        by = random.randint(brow[1] + 1, brow[3] - 1)
        boss_pos = (by, bx)
        enemies[boss_pos] = {
            'name': 'Room Boss',
            'hp': 350 + visits * 50,
            'atk': 20 + visits * 3,
            'reward': int(1500 * (1 + 0.25 * visits)),
            'ascii': '(#B#)',
            'is_boss': True
        }
    return game_map

# create a default fallback current_map
try:
    current_map = create_room(0)['map']
except Exception:
    current_map = [[FLOOR_CHAR for _ in range(ROOM_WIDTH)] for _ in range(ROOM_HEIGHT)]

# temporary holders for transitions
prev_state = None
prev_player_pos = None

# Player HP
player_max_hp = 20
player_hp = player_max_hp

# ensure enemies exists
try:
    enemies
except NameError:
    enemies = {}

# battle state
current_battle_enemy = None
current_battle_pos = None

# meta progression (preserved)
meta_currency = 0
meta_upgrades = [
    {'key': '1', 'id': 'unlock_tier1', 'name': 'Unlock Tier I', 'cost': 5, 'desc': 'Unlock upgrades 4-6', 'purchased': False},
    {'key': '2', 'id': 'unlock_tier2', 'name': 'Unlock Tier II', 'cost': 20, 'desc': 'Unlock upgrades 7-9 (requires Tier I)', 'purchased': False},
    {'key': '3', 'id': 'start_per_click', 'name': 'Starter Hands', 'cost': 10, 'desc': 'Start each run with +1 per-click', 'purchased': False},
    {'key': '4', 'id': 'start_attack', 'name': 'Warrior Start', 'cost': 15, 'desc': 'Start each run with +5 attack', 'purchased': False},
]
meta_upgrades_state = {m['id']: m['purchased'] for m in meta_upgrades}
meta_start_per_click = 0
meta_start_attack = 0

import state
import actions
import persistence
import os

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

# ------------------------------
# MENU / VIEW SWITCHING
# ------------------------------

def switch_to_incremental():
    state.game_state = 'incremental'
    render_incremental()

def switch_to_map():
    state.game_state = 'explore'
    render_map()

def switch_to_menu():
    state.game_state = 'menu'
    display_menu()

# ------------------------------
# RENDER SCREENS
# ------------------------------

def display_start_menu():
    clear()
    print("====== CLICK ADVENTURE ======")
    print("Press [SPACE] to click.")
    print("Press [R] for clicker mode.")
    print("Press [M] for map explore mode.")
    print("Press [Q] for main menu.")
    print("Press [ESC] to quit.")
    print("=============================")

def display_menu():
    clear()
    print("==== MAIN MENU ====")
    print("R - Incremental")
    print("M - Map")
    print("I - Inventory")
    print("Q - Return here")
    print("====================")

def render_incremental():
    clear()
    print("=== CLICKER MODE ===")
    print(f"Clicks: {state.count}")
    print(f"Per click: {state.per_click}")
    print("Press SPACE to click.")
    print("=====================")

def render_map():
    clear()
    print("=== MAP ===")
    px, py = state.player_pos
    print(f"Player at: {px}, {py}")
    print("Use WASD to move.")
    print("====================")

def render_inventory():
    clear()
    print("=== INVENTORY ===")
    for item, value in state.inventory.items():
        print(f"{item}: {value}")
    print("==================")



# weapon/armour curves
def compute_weapon_attack(level: int, A0: float = 20.0, ra: float = 1.12) -> float:
    return A0 * (ra ** level)

def compute_armour_defense(level: int, D0: float = 15.0, rd: float = 1.1253333) -> float:
    return D0 * (rd ** level)


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def switch_to_incremental():
    state.game_state = 'incremental'
    render_incremental()

def switch_to_map():
    state.game_state = 'explore'
    render_map()

def switch_to_menu():
    state.game_state = 'menu'
    display_menu()

# ------------------------------
# RENDER SCREENS
# ------------------------------

def display_start_menu():
    clear()
    print("====== CLICK ADVENTURE ======")
    print("Press [SPACE] to click.")
    print("Press [R] for clicker mode.")
    print("Press [M] for map explore mode.")
    print("Press [Q] for main menu.")
    print("Press [ESC] to quit.")
    print("=============================")

def display_menu():
    clear()
    print("==== MAIN MENU ====")
    print("R - Incremental")
    print("M - Map")
    print("I - Inventory")
    print("Q - Return here")
    print("====================")

def render_incremental():
    clear()
    print("=== CLICKER MODE ===")
    print(f"Clicks: {state.count}")
    print(f"Per click: {state.per_click}")
    print("Press SPACE to click.")
    print("=====================")

def render_map():
    clear()
    print("=== MAP ===")
    px, py = state.player_pos
    print(f"Player at: {px}, {py}")
    print("Use WASD to move.")
    print("====================")

def render_inventory():
    clear()
    print("=== INVENTORY ===")
    for item, value in state.inventory.items():
        print(f"{item}: {value}")
    print("==================")
