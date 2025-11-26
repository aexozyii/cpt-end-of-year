import threading
import random
import os, subprocess, sys
try:
    import colorama
    from colorama import Fore, Style
except ImportError:
    subprocess.check_call(sys.executable["-m", "pip", "install", "colorama"])
    import colorama
    from colorama import Fore, Style
colorama.init(autoreset=True)


count = 0
per_click = 1
# track the highest currency reached during the current run (used for meta reward)
run_max_count = 0
game_state = 'start_menu'

movement_lock = threading.Lock()
last_space_time = 0.0
MOVE_INTERVAL = 0.15
last_move_time = 0.0
space_pressed = False

SAVE_FILE = os.path.join(os.path.dirname(__file__), 'save.json')

# incremental upgrades
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

# Shop items
shop_items = [
    {'key': '1', 'name': 'Sword', 'cost': 100, 'type': 'weapon', 'amount': 5, 'purchased': False},
    {'key': '2', 'name': 'Armour', 'cost': 80,  'type': 'armour', 'amount': 5, 'purchased': False},
    {'key': '3', 'name': 'Bag',    'cost': 50,  'type': 'bag',    'amount': 1, 'purchased': False},
]


BATTLE_ACTIONS = {
    '1': {'name': 'Execute Code', 'type': 'Attack', 'color': 'RED'},
    '2': {'name': 'Defend Code',  'type': 'Defend', 'color': 'BLUE'},
    '3': {'name': 'Recover',      'type': 'Heal',   'color': 'WHITE'},
    '4': {'name': 'Hack',         'type': 'Debuff', 'color': 'Black'},
    '5': {'name': 'Debug',        'type': 'Buff',    'color': 'GREEN'},
}


# Player combat/stats and inventory
attack = 0
defense = 0
has_bag = False
inventory = []
inventory_capacity = 0
player_defense_modifier = 0
enemy_attack_modifier = 0

# equipped items
equipped_weapon = None  # dict or None
equipped_armour = None  # dict or None

# Map constants
ROOM_WIDTH = 20
ROOM_HEIGHT = 10
PLAYER_CHAR = f'{Fore.LIGHTRED_EX}~{Style.RESET_ALL}'
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
    avail = [(y, x)
            for y in range(1, ROOM_HEIGHT - 1)
            for x in range(1, ROOM_WIDTH - 1)
            if not (y == player_y and x == player_x)]
    shop_pos = random.choice(avail)
    ty, tx = shop_pos
    global TELEPORTS
    TELEPORTS = {shop_pos: 'shop'}
    occupied = {shop_pos}
    num_exclaims = random.randint(1, 2)
    num_enemies = random.randint(1, 2)
    remaining = [p for p in avail if p not in occupied]
    random.shuffle(remaining)
    take = num_exclaims + num_enemies
    chosen = remaining[:take]
    exclaim_positions = chosen[:num_exclaims]
    enemy_positions = chosen[num_exclaims: num_exclaims + num_enemies]
    for (ey, ex) in exclaim_positions:
        game_map[ey][ex] = '!'
    # create enemy entries (do not write to map here; render will show them)
    global enemies
    enemies = {}
    for (ey, ex) in enemy_positions:
        # randomly choose enemy type/stats
        if random.random() < 0.6:
            enemies[(ey, ex)] = {
                'name': 'Human',
                'hp': 80,
                'atk': 4,
                'reward': 200,
                'ascii': '  ,      ,\n (\_/)\n (o.o)\n  >^ '
            }
        else:
            enemies[(ey, ex)] = {
                'name': 'Dart Monkey',
                'hp': 130,
                'atk': 12,
                'reward': 450,
                'ascii': "  ,--.\n (____)\n /||\\\\\n  ||"
            }

    return game_map

current_map = create_map()


# temporary holders for feature transitions
prev_state = None
prev_player_pos = None

# Player HP
player_max_hp = 20               
player_hp = player_max_hp

# enemies will be created by create_map(); ensure variable exists
try:
    enemies
except NameError:
    enemies = {}

# Current battle state
current_battle_enemy = None
current_battle_pos = None

# --- Meta / roguelite persistent progression ---
# Meta currency gained on death and spent on persistent upgrades
meta_currency = 0
# Meta upgrades definition
meta_upgrades = [
    {'key': '1', 'id': 'unlock_tier1', 'name': 'Unlock Tier I', 'cost': 5, 'desc': 'Unlock upgrades 4-6', 'purchased': False},
    {'key': '2', 'id': 'unlock_tier2', 'name': 'Unlock Tier II', 'cost': 20, 'desc': 'Unlock upgrades 7-9 (requires Tier I)', 'purchased': False},
    {'key': '3', 'id': 'start_per_click', 'name': 'Starter Hands', 'cost': 10, 'desc': 'Start each run with +1 per-click', 'purchased': False},
    {'key': '4', 'id': 'start_attack', 'name': 'Warrior Start', 'cost': 15, 'desc': 'Start each run with +5 attack', 'purchased': False},
]
# quick lookup mapping id->purchased (kept in sync by persistence)
meta_upgrades_state = {m['id']: m['purchased'] for m in meta_upgrades}

# persistent meta bonuses
meta_start_per_click = 0
meta_start_attack = 0


def compute_weapon_attack(level: int, A0: float = 20.0, ra: float = 1.12) -> float:
    """Compute weapon attack for given level using A = A0 * ra ** level."""
    return A0 * (ra ** level)


def compute_armour_defense(level: int, D0: float = 15.0, rd: float = 1.1253333) -> float:
    """Compute armor defense for given level using D = D0 * rd ** level."""
    return D0 * (rd ** level)
