import threading
import random
import os, subprocess, sys
import traceback # Added for debugging

try:
    import colorama
    from colorama import Fore, Style
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "colorama"])
    import colorama
    from colorama import Fore, Style
colorama.init(autoreset=True)

# --- Map Constants and Global Variables ---
ROOM_WIDTH = 50
ROOM_HEIGHT = 50
PLAYER_CHAR = f'{Fore.LIGHTRED_EX}~{Style.RESET_ALL}'
WALL_CHAR = '│'  # vertical wall
H_WALL_CHAR = '─'  # horizontal wall
FLOOR_CHAR = '.'
player_y, player_x = 4, 10
map_visit_count = 0

# Multi-room world tracking (Variables used by the primary 'create_rooms' logic)
rooms = [] # list of room dicts
current_room_index = 0
current_map = [] # active map layout
enemies = {} # active enemies in the current room
TELEPORTS = {}  # active teleports in the current room
EXITS = {}  # active exits in the current room


# --- Core Run State & Global Variables ---

count = 0
per_click = 1
run_max_count = 0
game_state = 'menu'
movement_lock = threading.Lock()
last_space_time = 0.0
MOVE_INTERVAL = 0.06
last_move_time = 0.0
space_pressed = False
SAVE_FILE = os.path.join(os.path.dirname(__file__), 'save.json')

# incremental upgrades (using the refined list from the last prompt)
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

# Player combat/stats and inventory
attack = 0
defense = 0
has_bag = False
inventory = []
inventory_capacity = 0
equipped_weapon = None  # dict or None
equipped_armour = None  # dict or None
prev_state = None # needed by actions.py for entering features
prev_player_pos = None # needed by actions.py for entering features

# Player HP and Battle State (Needed by actions.py and render.py)
player_max_hp = 100 # Increased from 20 to align with other battle logic
player_hp = player_max_hp
enemy_hp = 100
enemy_max_hp = 100
player_shield = 0
enemy_shield = 0
player_debuffs = 0
player_buffs = 0
enemy_debuffs = 0
enemy_buffs = 0
log_messages = []
turn_count = 1
player_actions_left = 3


# --- Meta / roguelite persistent progression ---
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


# --- Map Generation Functions ---

def create_room(visits: int = 0):
    # This is the function for the multi-room system, provided in a previous prompt
    # ... (Keep the full implementation of create_room from the previous response here) ...
    game_map = [[FLOOR_CHAR for _ in range(ROOM_WIDTH)] for _ in range(ROOM_HEIGHT)]
    for x in range(ROOM_WIDTH):
        game_map[0][x] = H_WALL_CHAR
        game_map[ROOM_HEIGHT - 1][x] = H_WALL_CHAR
    for y in range(ROOM_HEIGHT):
        game_map[y][0] = WALL_CHAR
        game_map[y][ROOM_WIDTH - 1] = WALL_CHAR
    exits = {}
    num_exclaims = random.randint(1, max(1, min(6, 1 + visits)))
    num_enemies = random.randint(2 + visits, min(12, 3 + visits * 2))
    num_rocks = random.randint(8, max(12, 15 + visits))
    avail = [(y, x) for y in range(1, ROOM_HEIGHT - 1) for x in range(1, ROOM_WIDTH - 1)]
    random.shuffle(avail)
    exclaim_positions = avail[:num_exclaims]
    enemy_positions = avail[num_exclaims:num_exclaims + num_enemies]
    rock_positions = avail[num_exclaims + num_enemies:num_exclaims + num_enemies + num_rocks]
    for (ey, ex) in exclaim_positions: game_map[ey][ex] = '!'
    for (ry, rx) in rock_positions:
        game_map[ry][rx] = '^'
        if random.random() < 0.4:
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ny, nx = ry + dy, rx + dx
                if 1 <= ny < ROOM_HEIGHT - 1 and 1 <= nx < ROOM_WIDTH - 1:
                    if game_map[ny][nx] == FLOOR_CHAR: game_map[ny][nx] = '^'
    enemies_local = {}
    for (ey, ex) in enemy_positions:
        if game_map[ey][ex] not in (FLOOR_CHAR, '!'): continue
        if random.random() < 0.6:
            enemies_local[(ey, ex)] = {'name': 'Human', 'hp': 80 + visits * 10, 'atk': 4 + visits, 'reward': int(200 * (1 + 0.2 * visits)), 'ascii': '  ,      ,\\n (\\_/)\\n (o.o)\\n  >^ ' }
        else:
            enemies_local[(ey, ex)] = {'name': 'Dart Monkey', 'hp': 130 + visits * 18, 'atk': 12 + visits * 2, 'reward': int(450 * (1 + 0.2 * visits)), 'ascii': "  ,--.\\n (____)\\n /||\\\\\\n  ||"}
    fountain_pos = None
    if len(avail) > num_exclaims + num_enemies + num_rocks:
        fpos = avail[num_exclaims + num_enemies + num_rocks]
        fy, fx = fpos
        game_map[fy][fx] = 'H'
        fountain_pos = (fy, fx)
    teleport = {}
    return {'map': game_map, 'enemies': enemies_local, 'teleport': teleport, 'fountain': fountain_pos, 'exits': exits}


def create_rooms(n: int = 5, visits: int = 0):
    # This is the function for the multi-room system, provided in a previous prompt
    # ... (Keep the full implementation of create_rooms from the previous response here) ...
    n = max(1, min(int(n), 5))
    rs = [create_room(visits) for _ in range(n)]
    shop_idx = random.randrange(len(rs))
    rm = rs[shop_idx]
    sx = ROOM_WIDTH // 2; sy = ROOM_HEIGHT // 2
    rm['teleport'] = {(sy, sx): 'shop'}
    boss_idx = len(rs) - 1
    if shop_idx == boss_idx and len(rs) > 1:
        new_shop_idx = random.choice([i for i in range(len(rs)) if i != boss_idx])
        rs[shop_idx]['teleport'] = {}; shop_idx = new_shop_idx
        rm = rs[shop_idx]; sx = ROOM_WIDTH // 2; sy = ROOM_HEIGHT // 2
        rm['teleport'] = {(sy, sx): 'shop'}
    brow = rs[boss_idx]; bx = random.randint(2, ROOM_WIDTH - 3); by = random.randint(2, ROOM_HEIGHT - 3)
    brow['enemies'][(by, bx)] = {'name': 'Room Boss', 'hp': 350 + visits * 50, 'atk': 20 + visits * 3, 'reward': int(1500 * (1 + 0.25 * visits)), 'ascii': '(#B#)', 'is_boss': True}
    opening_size = 3; half = opening_size // 2; cy = ROOM_HEIGHT // 2
    for i in range(len(rs)): rs[i]['exits'] = {}
    for i in range(len(rs)):
        rm = rs[i]
        if i > 0:
            left_room = rs[i - 1]
            for dy in range(-half, half + 1):
                oy = cy + dy; ox = 0
                if 0 <= oy < ROOM_HEIGHT:
                    rm['map'][oy][ox] = FLOOR_CHAR; rm['exits'][(oy, ox)] = 'left'
                    left_room['map'][oy][ROOM_WIDTH - 1] = FLOOR_CHAR; left_room['exits'][(oy, ROOM_WIDTH - 1)] = 'right'
                    rm['enemies'].pop((oy, ox), None); left_room['enemies'].pop((oy, ROOM_WIDTH - 1), None)
        if i < len(rs) - 1:
            right_room = rs[i + 1]
            for dy in range(-half, half + 1):
                oy = cy + dy; ox = ROOM_WIDTH - 1
                if 0 <= oy < ROOM_HEIGHT:
                    rm['map'][oy][ox] = FLOOR_CHAR; rm['exits'][(oy, ox)] = 'right'
                    right_room['map'][oy][0] = FLOOR_CHAR # Fixed the syntax error from the prompt
                    right_room['exits'][(oy, 0)] = 'left'
                    rm['enemies'].pop((oy, ox), None); right_room['enemies'].pop((oy, 0), None)
    rooms[:] = rs


def load_room(idx: int):
    """Load room `idx` into the legacy globals (`current_map`, `enemies`, `TELEPORTS`, `EXITS`)."""
    global current_room_index, current_map, enemies, TELEPORTS, EXITS, player_y, player_x
    if not (0 <= idx < len(rooms)):
        return
    current_room_index = idx
    room = rooms[idx]
    current_map = room['map']
    enemies = dict(room['enemies'])
    TELEPORTS = dict(room.get('teleport', {}))
    EXITS = dict(room.get('exits', {}))


def create_map():
    """Generates a single, self-contained map using the older, room-based method (from the latest prompt)."""
    # base map with floor and outer walls
    game_map = [[FLOOR_CHAR for _ in range(ROOM_WIDTH)] for _ in range(ROOM_HEIGHT)]
    for x in range(ROOM_WIDTH):
        game_map[0][x] = H_WALL_CHAR
        game_map[ROOM_HEIGHT - 1][x] = H_WALL_CHAR
    for y in range(ROOM_HEIGHT):
        game_map[y][0] = WALL_CHAR
        game_map[y][ROOM_WIDTH - 1] = WALL_CHAR

    rooms_data = [] # Use rooms_data to not conflict with global 'rooms' list
    max_rooms = 5
    attempts = 0
    while len(rooms_data) < max_rooms and attempts < 200:
        attempts += 1
        w = random.randint(5, min(10, ROOM_WIDTH - 4))
        h = random.randint(3, min(6, ROOM_HEIGHT - 4))
        x1 = random.randint(1, ROOM_WIDTH - w - 2)
        y1 = random.randint(1, ROOM_HEIGHT - h - 2)
        x2 = x1 + w - 1
        y2 = y1 + h - 1
        overlaps = False
        for (ax1, ay1, ax2, ay2) in rooms_data:
            if not (x2 < ax1 or x1 > ax2 or y2 < ay1 or y1 > ay2):
                overlaps = True
                break
        if overlaps:
            continue
        rooms_data.append((x1, y1, x2, y2))

    for (x1, y1, x2, y2) in rooms_data:
        for ry in range(y1, y2 + 1):
            for rx in range(x1, x2 + 1):
                if ry == y1 or ry == y2:
                    game_map[ry][rx] = H_WALL_CHAR
                elif rx == x1 or rx == x2:
                    game_map[ry][rx] = WALL_CHAR
                else:
                    game_map[ry][rx] = FLOOR_CHAR

    # Find a shop position
    shop_pos = None
    if rooms_data:
        shop_room = random.choice(rooms_data)
        sx = (shop_room[0] + shop_room[2]) // 2
        sy = (shop_room[1] + shop_room[3]) // 2
        shop_pos = (sy, sx)
    else:
        avail = [(y, x) for y in range(1, ROOM_HEIGHT - 1) for x in range(1, ROOM_WIDTH - 1)]
        shop_pos = random.choice(avail)

    global TELEPORTS
    TELEPORTS = {shop_pos: 'shop'}

    # Find a fountain position (logic from the latest prompt)
    fountain_pos = None
    if rooms_data and len(rooms_data) > 1:
        pool = [r for r in rooms_data if r != shop_room]
        froom = random.choice(pool)
        fx = random.randint(froom[0] + 1, froom[2] - 1)
        fy = random.randint(froom[1] + 1, froom[3] - 1)
        fountain_pos = (fy, fx)
        game_map[fy][fx] = 'H'

    # Decide how many exclaims and enemies, scaled by map visits
    visits = map_visit_count
    num_exclaims = random.randint(1, max(1, min(3, 1 + visits)))
    num_enemies = random.randint(1 + visits, min(6, 2 + visits))

    # Pick positions for exclaims and enemies within rooms (logic from the latest prompt)
    free_cells = []
    for (x1, y1, x2, y2) in rooms_data:
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

    # Create enemy entries (logic from the latest prompt)
    global enemies
    enemies = {}
    for (ey, ex) in enemy_positions:
        if random.random() < 0.6:
            enemies[(ey, ex)] = {
                'name': 'Human', 'hp': 80 + visits * 10, 'atk': 4 + visits,
                'reward': int(200 * (1 + 0.2 * visits)),
                'ascii': '  ,      ,\\n (\\_/)\\n (o.o)\\n  >^ '
            }
        else:
            enemies[(ey, ex)] = {
                'name': 'Dart Monkey', 'hp': 130 + visits * 18, 'atk': 12 + visits * 2,
                'reward': int(450 * (1 + 0.2 * visits)),
                'ascii': "  ,--.\\n (____)\\n /||\\\\\\n  ||"
            }

    # Choose an end room for a boss (logic from the latest prompt)
    boss_room_candidates = [r for r in rooms_data if r[0] == 1 or r[1] == 1 or r[2] == ROOM_WIDTH - 2 or r[3] == ROOM_HEIGHT - 2]
    if not boss_room_candidates and rooms_data:
        boss_room_candidates = rooms_data
    boss_pos = None
    if boss_room_candidates:
        brow = random.choice(boss_room_candidates)
        bx = random.randint(brow[0] + 1, brow[2] - 1)
        by = random.randint(brow[1] + 1, brow[3] - 1)
        boss_pos = (by, bx)
        enemies[boss_pos] = {
            'name': 'Room Boss', 'hp': 350 + visits * 50,
            'atk': 20 + visits * 3,
            'reward': int(1500 * (1 + 0.25 * visits)),
            'ascii': '(#B#)',
            'is_boss': True
        }
    
    # Return the generated map (current_map is set globally)
    global current_map
    current_map = game_map
    return game_map


# Initialize the current map on load (using the single map version as default now)
try:
    # Use create_map() (single map) or create_rooms(N_ROOMS) (multi-room) here
    # current_map = create_rooms(3)['map'] # Example for multi-room start
    create_map() # This function sets the global current_map, enemies, TELEPORTS

except Exception:
    # Fallback if map generation fails for any reason
    print(f"Error during initial map generation: {traceback.format_exc()}")
    current_map = [[FLOOR_CHAR for _ in range(ROOM_WIDTH)] for _ in range(ROOM_HEIGHT)]


# --- Helper functions required by actions.py for inventory/combat ---

def compute_weapon_attack(level: int, A0: float = 20.0, ra: float = 1.12) -> float:
    """Compute weapon attack for given level using A = A0 * ra ** level."""
    return A0 * (ra ** level)

def compute_armour_defense(level: int, D0: float = 15.0, rd: float = 1.1253333) -> float:
    """Compute armor defense for given level using D = D0 * rd ** level."""
    return D0 * (rd ** level)
