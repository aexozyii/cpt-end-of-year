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

ROOM_WIDTH = 50
ROOM_HEIGHT = 50
PLAYER_CHAR = f'{Fore.LIGHTRED_EX}~{Style.RESET_ALL}'
WALL_CHAR = '|'
FLOOR_CHAR = '.'
player_y, player_x = 4, 10
# how many times the player has opened/visited the map
map_visit_count = 0

# Multi-room world: generate several separate room-maps (each ROOM_WIDTH x ROOM_HEIGHT)
# `rooms` is a list where each entry is a dict: {'map': [...], 'enemies': {...}, 'teleport': {...}, 'fountain': (y,x) or None}
rooms = []
current_room_index = 0

def create_room(visits: int = 0):
    """Create a single room map (ROOM_WIDTH x ROOM_HEIGHT) with walls, events, enemies and optionally a fountain.
    Returns a dict with keys: 'map', 'enemies', 'teleport', 'fountain'.
    """
    game_map = [[FLOOR_CHAR for _ in range(ROOM_WIDTH)] for _ in range(ROOM_HEIGHT)]
    # outer walls
    for x in range(ROOM_WIDTH):
        game_map[0][x] = WALL_CHAR
        game_map[ROOM_HEIGHT - 1][x] = WALL_CHAR
    for y in range(ROOM_HEIGHT):
        game_map[y][0] = WALL_CHAR
        game_map[y][ROOM_WIDTH - 1] = WALL_CHAR

    # carve small openings at each edge so players can move between rooms
    # openings are centered and 3 cells wide (vertical on left/right, horizontal on top/bottom)
    opening_size = 3
    cy = ROOM_HEIGHT // 2
    cx = ROOM_WIDTH // 2
    exits = {}
    half = opening_size // 2
    # left edge openings
    for dy in range(-half, half + 1):
        oy = cy + dy
        ox = 0
        if 0 <= oy < ROOM_HEIGHT:
            game_map[oy][ox] = FLOOR_CHAR
            exits[(oy, ox)] = 'left'
    # right edge openings
    for dy in range(-half, half + 1):
        oy = cy + dy
        ox = ROOM_WIDTH - 1
        if 0 <= oy < ROOM_HEIGHT:
            game_map[oy][ox] = FLOOR_CHAR
            exits[(oy, ox)] = 'right'
    # top edge openings
    for dx in range(-half, half + 1):
        oy = 0
        ox = cx + dx
        if 0 <= ox < ROOM_WIDTH:
            game_map[oy][ox] = FLOOR_CHAR
            exits[(oy, ox)] = 'up'
    # bottom edge openings
    for dx in range(-half, half + 1):
        oy = ROOM_HEIGHT - 1
        ox = cx + dx
        if 0 <= ox < ROOM_WIDTH:
            game_map[oy][ox] = FLOOR_CHAR
            exits[(oy, ox)] = 'down'

    # place some interior features: number of exclaims/enemies scale with visits
    num_exclaims = random.randint(1, max(1, min(6, 1 + visits)))
    num_enemies = random.randint(1 + visits, min(10, 2 + visits * 2))

    # pick free interior cells (not walls)
    avail = [(y, x) for y in range(1, ROOM_HEIGHT - 1) for x in range(1, ROOM_WIDTH - 1)]
    random.shuffle(avail)
    exclaim_positions = avail[:num_exclaims]
    enemy_positions = avail[num_exclaims:num_exclaims + num_enemies]

    for (ey, ex) in exclaim_positions:
        game_map[ey][ex] = '!'

    # create enemies dict for this room
    enemies_local = {}
    for (ey, ex) in enemy_positions:
        if random.random() < 0.6:
            enemies_local[(ey, ex)] = {
                'name': 'Human',
                'hp': 80 + visits * 10,
                'atk': 4 + visits,
                'reward': int(200 * (1 + 0.2 * visits)),
                'ascii': '  ,      ,\\n (\\_/)\\n (o.o)\\n  >^ '
            }
        else:
            enemies_local[(ey, ex)] = {
                'name': 'Dart Monkey',
                'hp': 130 + visits * 18,
                'atk': 12 + visits * 2,
                'reward': int(450 * (1 + 0.2 * visits)),
                'ascii': "  ,--.\\n (____)\\n /||\\\\\\n  ||"
            }

    # optional fountain
    fountain_pos = None
    if len(avail) > num_exclaims + num_enemies:
        fpos = avail[num_exclaims + num_enemies]
        fy, fx = fpos
        game_map[fy][fx] = 'H'
        fountain_pos = (fy, fx)

    # no shop teleport by default; assigned when rooms generated in bulk
    teleport = {}

    return {'map': game_map, 'enemies': enemies_local, 'teleport': teleport, 'fountain': fountain_pos, 'exits': exits}


def create_rooms(n: int = 5, visits: int = 0):
    """Generate `n` independent rooms for the current run. One room will be assigned the shop, and one a boss."""
    rs = [create_room(visits) for _ in range(n)]
    # pick a shop room and assign a teleport position roughly near center
    shop_idx = random.randrange(len(rs))
    rm = rs[shop_idx]
    sx = ROOM_WIDTH // 2
    sy = ROOM_HEIGHT // 2
    rm['teleport'] = {(sy, sx): 'shop'}
    # ensure shop tile and adjacent cells are free from enemies/events
    try:
        to_remove = []
        for (ey, ex) in list(rm.get('enemies', {}).keys()):
            if abs(ey - sy) <= 1 and abs(ex - sx) <= 1:
                to_remove.append((ey, ex))
        for k in to_remove:
            try:
                del rm['enemies'][k]
            except Exception:
                pass
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                cy, cx = sy + dy, sx + dx
                if 0 <= cy < ROOM_HEIGHT and 0 <= cx < ROOM_WIDTH:
                    if rm['map'][cy][cx] in ('!', 'H'):
                        rm['map'][cy][cx] = FLOOR_CHAR
        rm['map'][sy][sx] = FLOOR_CHAR
    except Exception:
        pass
    # pick a boss room (prefer an index different from shop)
    boss_idx = shop_idx
    if len(rs) > 1:
        while boss_idx == shop_idx:
            boss_idx = random.randrange(len(rs))
    # put boss near an edge
    brow = rs[boss_idx]
    bx = random.randint(2, ROOM_WIDTH - 3)
    by = random.randint(2, ROOM_HEIGHT - 3)
    brow['enemies'][(by, bx)] = {
        'name': 'Room Boss',
        'hp': 350 + visits * 50,
        'atk': 20 + visits * 3,
        'reward': int(1500 * (1 + 0.25 * visits)),
        'ascii': '(#B#)',
        'is_boss': True
    }
    return rs


def load_room(idx: int):
    """Load room `idx` into the legacy globals (`current_map`, `enemies`, `TELEPORTS`)."""
    global current_room_index, rooms
    current_room_index = idx
    room = rooms[idx]
    # set module-level globals used elsewhere
    global current_map, enemies, TELEPORTS
    current_map = room['map']
    enemies = dict(room['enemies'])
    TELEPORTS = dict(room.get('teleport', {}))
    # expose exit positions for rendering indicators
    global EXITS
    EXITS = dict(room.get('exits', {}))
    # ensure fountain is represented in current_map (already set in creation)
    return

# core run state
count = 0
per_click = 1
# track the highest currency reached during the current run (used for meta rewards)
run_max_count = 0
game_state = 'start_menu'

movement_lock = threading.Lock()
last_space_time = 0.0
MOVE_INTERVAL = 0.06
last_move_time = 0.0
space_pressed = False

SAVE_FILE = os.path.join(os.path.dirname(__file__), 'save.json')

# incremental upgrades (some gated by meta requirements)
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
# equipped items
equipped_weapon = None  # dict or None
equipped_armour = None  # dict or None

# teleport markers mapping (set by create_map)
TELEPORTS = {}
EXITS = {}


def create_map():
    # base map with floor and outer walls
    game_map = [[FLOOR_CHAR for _ in range(ROOM_WIDTH)] for _ in range(ROOM_HEIGHT)]
    for x in range(ROOM_WIDTH):
        game_map[0][x] = WALL_CHAR
        game_map[ROOM_HEIGHT - 1][x] = WALL_CHAR
    for y in range(ROOM_HEIGHT):
        game_map[y][0] = WALL_CHAR
        game_map[y][ROOM_WIDTH - 1] = WALL_CHAR

    # create multiple rectangular rooms (rooms are logical areas where enemies/events spawn)
    rooms = []
    max_rooms = 5
    attempts = 0
    while len(rooms) < max_rooms and attempts < 200:
        attempts += 1
        w = random.randint(5, min(10, ROOM_WIDTH - 4))
        h = random.randint(3, min(6, ROOM_HEIGHT - 4))
        x1 = random.randint(1, ROOM_WIDTH - w - 2)
        y1 = random.randint(1, ROOM_HEIGHT - h - 2)
        x2 = x1 + w - 1
        y2 = y1 + h - 1
        # check overlap
        overlaps = False
        for (ax1, ay1, ax2, ay2) in rooms:
            if not (x2 < ax1 or x1 > ax2 or y2 < ay1 or y1 > ay2):
                overlaps = True
                break
        if overlaps:
            continue
        rooms.append((x1, y1, x2, y2))

    # carve rooms into the map (floor already '.', but mark boundaries with wall char)
    for (x1, y1, x2, y2) in rooms:
        for ry in range(y1, y2 + 1):
            for rx in range(x1, x2 + 1):
                # leave interior as floor, draw walls at room edges
                if ry == y1 or ry == y2 or rx == x1 or rx == x2:
                    game_map[ry][rx] = WALL_CHAR
                else:
                    game_map[ry][rx] = FLOOR_CHAR

    # pick a shop room and place teleport marker inside it
    if rooms:
        shop_room = random.choice(rooms)
        sx = (shop_room[0] + shop_room[2]) // 2
        sy = (shop_room[1] + shop_room[3]) // 2
        shop_pos = (sy, sx)
    else:
        avail = [(y, x) for y in range(1, ROOM_HEIGHT - 1) for x in range(1, ROOM_WIDTH - 1)]
        shop_pos = random.choice(avail)

    global TELEPORTS
    TELEPORTS = {shop_pos: 'shop'}

    # place a healing fountain in a different random room
    fountain_pos = None
    if rooms and len(rooms) > 1:
        pool = [r for r in rooms if r != shop_room]
        froom = random.choice(pool)
        fx = random.randint(froom[0] + 1, froom[2] - 1)
        fy = random.randint(froom[1] + 1, froom[3] - 1)
        fountain_pos = (fy, fx)
        game_map[fy][fx] = 'H'

    # decide how many exclaims and enemies, scaled by map visits
    visits = map_visit_count
    num_exclaims = random.randint(1, max(1, min(3, 1 + visits)))
    num_enemies = random.randint(1 + visits, min(6, 2 + visits))

    # pick positions for exclaims and enemies within rooms
    free_cells = []
    for (x1, y1, x2, y2) in rooms:
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

    # create enemy entries
    global enemies
    enemies = {}
    for (ey, ex) in enemy_positions:
        if random.random() < 0.6:
            enemies[(ey, ex)] = {
                'name': 'Human',
                'hp': 80 + visits * 10,
                'atk': 4 + visits,
                'reward': int(200 * (1 + 0.2 * visits)),
                'ascii': '  ,      ,\\n (\\_/)\\n (o.o)\\n  >^ '
            }
        else:
            enemies[(ey, ex)] = {
                'name': 'Dart Monkey',
                'hp': 130 + visits * 18,
                'atk': 12 + visits * 2,
                'reward': int(450 * (1 + 0.2 * visits)),
                'ascii': "  ,--.\\n (____)\\n /||\\\\\\n  ||"
            }

    # choose an end room for a boss (prefer rooms touching a boundary)
    boss_room_candidates = [r for r in rooms if r[0] == 1 or r[1] == 1 or r[2] == ROOM_WIDTH - 2 or r[3] == ROOM_HEIGHT - 2]
    if not boss_room_candidates and rooms:
        boss_room_candidates = rooms
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

try:
    current_map = create_room(0)['map']
except Exception:
    current_map = [[FLOOR_CHAR for _ in range(ROOM_WIDTH)] for _ in range(ROOM_HEIGHT)]


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
