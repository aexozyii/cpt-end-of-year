import threading
import random
import os, subprocess, sys
from enemies_data import ENEMY_TEMPLATES
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
# vertical wall (left/right) and horizontal wall (top/bottom)
# use box-drawing characters for a nicer look (most terminals support these)
WALL_CHAR = '│'  # vertical wall
H_WALL_CHAR = '─'  # horizontal wall
# flag to track if action descriptions are currently displayed
showing_battle_descriptions = False
FLOOR_CHAR = '.'
player_y, player_x = 4, 10
# how many times the player has opened/visited the map
map_visit_count = 0

# Multi-room world: generate several separate room-maps (each ROOM_WIDTH x ROOM_HEIGHT)
# `rooms` is a list where each entry is a dict: {'map': [...], 'enemies': {...}, 'teleport': {...}, 'fountain': (y,x) or None}
rooms = []
current_room_index = 0


resources = {
    'GordonGeo': 0,
    'Lollipop': 0,
    'CameronChildren': 0,
    'Cards': 0,
    'PMoons' 0
}


def create_room(visits: int = 0):
    """Create a single room map (ROOM_WIDTH x ROOM_HEIGHT) with walls, events, enemies and optionally a fountain.
    Returns a dict with keys: 'map', 'enemies', 'teleport', 'fountain'.
    """
    game_map = [[FLOOR_CHAR for _ in range(ROOM_WIDTH)] for _ in range(ROOM_HEIGHT)]
    # outer walls: top/bottom use horizontal wall, left/right use vertical wall
    for x in range(ROOM_WIDTH):
        game_map[0][x] = H_WALL_CHAR
        game_map[ROOM_HEIGHT - 1][x] = H_WALL_CHAR
    for y in range(ROOM_HEIGHT):
        game_map[y][0] = WALL_CHAR
        game_map[y][ROOM_WIDTH - 1] = WALL_CHAR

    # by default no carved exits; `create_rooms` will link rooms and carve openings as needed
    exits = {}

    # place some interior features: number of exclaims/enemies scale with visits
    num_exclaims = random.randint(1, max(1, min(6, 1 + visits)))
    num_enemies = random.randint(2 + visits, min(12, 3 + visits * 2))  # increased spawn rate
    num_rocks = random.randint(8, max(12, 15 + visits))  # increased rock density
    num_trees = random.randint(6, max(10, 12 + visits))  # large trees (passable decoration)
    num_water = random.randint(3, max(6, 7 + visits // 2))  # water patches (impassable)

    # pick free interior cells (not walls)
    avail = [(y, x) for y in range(1, ROOM_HEIGHT - 1) for x in range(1, ROOM_WIDTH - 1)]
    random.shuffle(avail)
    exclaim_positions = avail[:num_exclaims]
    enemy_positions = avail[num_exclaims:num_exclaims + num_enemies]
    rock_positions = avail[num_exclaims + num_enemies:num_exclaims + num_enemies + num_rocks]
    tree_positions = avail[num_exclaims + num_enemies + num_rocks:num_exclaims + num_enemies + num_rocks + num_trees]
    water_positions = avail[num_exclaims + num_enemies + num_rocks + num_trees:num_exclaims + num_enemies + num_rocks + num_trees + num_water]

    for (ey, ex) in exclaim_positions:
        game_map[ey][ex] = '!'

    # place large trees - decorative, passable obstacles
    for (ty, tx) in tree_positions:
        game_map[ty][tx] = 'T'
        # expand trees to make them larger and more visually significant
        if random.random() < 0.5:
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ny, nx = ty + dy, tx + dx
                if 1 <= ny < ROOM_HEIGHT - 1 and 1 <= nx < ROOM_WIDTH - 1:
                    if game_map[ny][nx] == FLOOR_CHAR:
                        game_map[ny][nx] = 'T'

    # place water tiles - impassable obstacles for navigation challenge
    for (wy, wx) in water_positions:
        game_map[wy][wx] = '≈'
        # randomly expand water patches to make them more visually significant
        if random.random() < 0.3:
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ny, nx = wy + dy, wx + dx
                if 1 <= ny < ROOM_HEIGHT - 1 and 1 <= nx < ROOM_WIDTH - 1:
                    if game_map[ny][nx] == FLOOR_CHAR:
                        game_map[ny][nx] = '≈'

    # place rocks (obstacles) on the map with cluster expansion for larger rocks
    for (ry, rx) in rock_positions:
        game_map[ry][rx] = '^'
        # randomly expand rock clusters to make rocks bigger
        if random.random() < 0.4:
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ny, nx = ry + dy, rx + dx
                if 1 <= ny < ROOM_HEIGHT - 1 and 1 <= nx < ROOM_WIDTH - 1:
                    if game_map[ny][nx] == FLOOR_CHAR:
                        game_map[ny][nx] = '^'

    # place torches on walls for ambiance
    for i in range(min(6, 4 + visits)):
        torch_y = random.choice([1, ROOM_HEIGHT - 2])
        torch_x = random.randint(2, ROOM_WIDTH - 3)
        if 0 <= torch_y < ROOM_HEIGHT and 0 <= torch_x < ROOM_WIDTH:
            if game_map[torch_y][torch_x] == FLOOR_CHAR or game_map[torch_y][torch_x] == H_WALL_CHAR:
                game_map[torch_y][torch_x] = '*'

    # create enemies dict for this room (skip cells with decorative elements)
    enemies_local = {}
    for (ey, ex) in enemy_positions:
        # skip if enemy position overlaps with interactive elements (vegetation, water, treasure, torches)
        if game_map[ey][ex] not in (FLOOR_CHAR, '!'):
            continue
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
    if len(avail) > num_exclaims + num_enemies + num_rocks + num_trees + num_water:
        fpos = avail[num_exclaims + num_enemies + num_rocks + num_trees + num_water]
        fy, fx = fpos
        game_map[fy][fx] = 'H'
        fountain_pos = (fy, fx)

    # no shop teleport by default; assigned when rooms generated in bulk
    teleport = {}

    return {'map': game_map, 'enemies': enemies_local, 'teleport': teleport, 'fountain': fountain_pos, 'exits': exits}


def create_rooms(n: int = 5, visits: int = 0):
    """Generate `n` independent rooms for the current run. One room will be assigned the shop, and one a boss."""
    # cap the number of rooms to a sane maximum (5)
    n = max(1, min(int(n), 5))
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

    # pick an action-upgrade room (different from shop); place an upgrade altar teleport
    try:
        candidates = [i for i in range(len(rs)) if i != shop_idx]
        if candidates:
            upgrade_idx = random.choice(candidates)
            urm = rs[upgrade_idx]
            ux = ROOM_WIDTH // 2
            uy = ROOM_HEIGHT // 2 - 3
            # reserve tile for upgrade terminal
            urm['teleport'] = urm.get('teleport', {})
            urm['teleport'][(uy, ux)] = 'action_upgrades'
            # mark visible tile as 'U' in the map
            try:
                urm['map'][uy][ux] = 'U'
            except Exception:
                pass
    except Exception:
        pass
    # place the boss in the last room (index len(rs)-1)
    boss_idx = len(rs) - 1
    # if the shop was randomly chosen to be the last room, move shop elsewhere
    if shop_idx == boss_idx and len(rs) > 1:
        # pick a different shop index
        new_shop_idx = random.choice([i for i in range(len(rs)) if i != boss_idx])
        # move teleport data
        # clear old shop
        try:
            rs[shop_idx]['teleport'] = {}
        except Exception:
            pass
        shop_idx = new_shop_idx
        rm = rs[shop_idx]
        sx = ROOM_WIDTH // 2
        sy = ROOM_HEIGHT // 2
        rm['teleport'] = {(sy, sx): 'shop'}
    # put boss near an edge in the final room — use Teto miniboss template
    brow = rs[boss_idx]
    bx = random.randint(2, ROOM_WIDTH - 3)
    by = random.randint(2, ROOM_HEIGHT - 3)
    try:
        # always use teto_boss regardless of floor (scaling handled by visits multiplier)
        boss_key = 'teto_boss'
        # create a scaled instance from ENEMY_TEMPLATES if available
        boss_instance = create_enemy_instance(boss_key, visits)
        boss_instance['is_boss'] = True
        # give boss a larger hp/atk boost
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
    # Link rooms linearly (left-right). Carve 3-cell openings between neighbors and set 'exits'.
    opening_size = 3
    half = opening_size // 2
    cy = ROOM_HEIGHT // 2
    for i in range(len(rs)):
        rs[i]['exits'] = {}
    for i in range(len(rs)):
        rm = rs[i]
        # connect to previous room on the left
        if i > 0:
            left_room = rs[i - 1]
            for dy in range(-half, half + 1):
                oy = cy + dy
                ox = 0
                if 0 <= oy < ROOM_HEIGHT:
                    # carve opening
                    rm['map'][oy][ox] = FLOOR_CHAR
                    rm['exits'][(oy, ox)] = 'left'
                    # also carve reciprocal opening on right edge of left_room
                    left_room['map'][oy][ROOM_WIDTH - 1] = FLOOR_CHAR
                    left_room['exits'][(oy, ROOM_WIDTH - 1)] = 'right'
                    # remove any enemy/event on those cells
                    rm['enemies'].pop((oy, ox), None)
                    left_room['enemies'].pop((oy, ROOM_WIDTH - 1), None)
                    if rm['map'][oy][ox] in ('!', 'H'):
                        rm['map'][oy][ox] = FLOOR_CHAR
                    if left_room['map'][oy][ROOM_WIDTH - 1] in ('!', 'H'):
                        left_room['map'][oy][ROOM_WIDTH - 1] = FLOOR_CHAR
        # connect to next room on the right
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
    {'key': '4', 'name': 'Health Potion', 'cost': 30,  'type': 'consumable', 'subtype': 'heal', 'amount': 50, 'purchased': False},
    {'key': '5', 'name': 'Large Potion',  'cost': 120, 'type': 'consumable', 'subtype': 'heal', 'amount': 150, 'purchased': False},
    {'key': '6', 'name': 'Health Amulet', 'cost': 200, 'type': 'accessory',  'subtype': 'max_hp', 'amount': 20, 'purchased': False},
    {'key': '7', 'name': 'Greater Amulet','cost': 800, 'type': 'accessory',  'subtype': 'max_hp', 'amount': 50, 'purchased': False},
    {'key': '8', 'name': 'Ring of Strength','cost':300,'type':'accessory','subtype':'attack','amount':5,'purchased':False},
]

# Action upgrades (can be purchased at the Action Upgrade altar)
action_upgrades = [
    {'key': '1', 'id': 'execute_power', 'name': 'Execute Power', 'desc': 'Increase Execute damage', 'cost': 200, 'level': 0, 'max_level': 5, 'amount': 2},
    {'key': '2', 'id': 'defend_power',  'name': 'Defend Power',  'desc': 'Increase Defend shield',  'cost': 180, 'level': 0, 'max_level': 5, 'amount': 8},
    {'key': '3', 'id': 'recover_power', 'name': 'Recover Power', 'desc': 'Recover restores more SP', 'cost': 150, 'level': 0, 'max_level': 5, 'amount': 1},
    {'key': '4', 'id': 'hack_power',    'name': 'Hack Power',    'desc': 'Increase Hack debuff amount', 'cost': 160, 'level': 0, 'max_level': 5, 'amount': 1},
    {'key': '5', 'id': 'debug_power',   'name': 'Debug Power',   'desc': 'Increase Debug buff amount',  'cost': 160, 'level': 0, 'max_level': 5, 'amount': 1},
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
equipped_accessory = None  # dict or None (accessory like amulet/ring)

# teleport markers mapping (set by create_map)
TELEPORTS = {}
EXITS = {}

def create_enemy_instance(enemy_key, visits):
    """
    Generates a fully-statted enemy dictionary from a template, scaled by visits.
    HP scales exponentially (squared), ATK scales linearly.
    """
    template = ENEMY_TEMPLATES[enemy_key]
    if enemy_key == 'human':
        hp_scale, atk_scale, reward_mult = 10, 1, 0.2
    elif enemy_key == 'dart_monkey':
        hp_scale, atk_scale, reward_mult = 18, 2, 0.2
    else: # Default/Fallback scaling
        hp_scale, atk_scale, reward_mult = 5, 1, 0.1

    # HP scales exponentially: (base + visits * scale)^2 for floor 2+, otherwise just linear
    hp_base = template['base_hp'] + visits * hp_scale
    if visits > 0:
        hp = hp_base * hp_base  # exponential scaling
    else:
        hp = hp_base
    
    atk = template['base_atk'] + visits * atk_scale
    reward = int(template['base_reward'] * (1 + reward_mult * visits))

    return {
        'name': template['name'],
        'hp': hp,
        'atk': atk,
        'reward': reward,
        'ascii': template['ascii']
    }



def create_map():
    # base map with floor and outer walls
    game_map = [[FLOOR_CHAR for _ in range(ROOM_WIDTH)] for _ in range(ROOM_HEIGHT)]
    for x in range(ROOM_WIDTH):
        game_map[0][x] = H_WALL_CHAR
        game_map[ROOM_HEIGHT - 1][x] = H_WALL_CHAR
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
                if ry == y1 or ry == y2:
                    game_map[ry][rx] = H_WALL_CHAR
                elif rx == x1 or rx == x2:
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
    HUMAN_CHANCE = 0.6
    HUMAN_KEY = 'human'
    DART_MONKEY_KEY = 'dart_monkey'
    for (ey, ex) in enemy_positions:
        if random.random() < HUMAN_CHANCE:
            enemy_key = HUMAN_KEY
        else:
            enemy_key = DART_MONKEY_KEY
    enemies[(ey, ex)] = create_enemy_instance(enemy_key, visits)
    
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
