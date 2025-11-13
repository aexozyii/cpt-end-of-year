import keyboard
import sys
import os
import shutil
import time

count = 0
per_click = 1
game_state = 'menu'

upgrades = [
    {'key': '1', 'name': 'Better Fingers', 'cost': 10, 'type': 'add', 'amount': 1, 'purchased': False},
    {'key': '2', 'name': 'Auto Clicker',  'cost': 50, 'type': 'add', 'amount': 5, 'purchased': False},
    {'key': '3', 'name': 'Double Tap',    'cost': 200, 'type': 'mult', 'amount': 2, 'purchased': False},
]

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def center_text(text):
    columns, lines = shutil.get_terminal_size()
    text_lines = text.split('\n')
    centered_lines = [line.center(columns) for line in text_lines]
    vertical_padding = max((lines - len(text_lines)) // 2, 0)
    return '\n' * vertical_padding + '\n'.join(centered_lines)

def on_space():
    global count
    count += per_click
    display_incremental()

def buy_upgrade_key(key: str):
    """Attempt to buy the upgrade with matching key (e.g. '1', '2', '3')."""
    global count, per_click
    for upg in upgrades:
        if upg['key'] == key:
            if upg['purchased']:
                return
            if count < upg['cost']:
                return
            count -= upg['cost']
            if upg['type'] == 'add':
                per_click += upg['amount']
            elif upg['type'] == 'mult':
                per_click *= upg['amount']
            upg['purchased'] = True
            break
    display_incremental()
    
        keyboard.add_hotkey('r', switch_to_incremental)
        keyboard.add_hotkey('m', switch_to_map)

def display_incremental():
    if game_state != 'incremental':
        return
    clear_screen()
    title = "game placeholder"
    counter = f"Total Currency: {count}"
    prompt = f"(Press SPACE to earn +{per_click} | Press ESC to quit)"
    lines = [title, "", counter, "", prompt, ""]
    lines.append("")
    for upg in upgrades:
        status = "(PURCHASED)" if upg['purchased'] else f"Cost: {upg['cost']}"
        if upg['type'] == 'add':
            effect = f"+{upg['amount']} per click"
        else:
            effect = f"x{upg['amount']} per click"
        lines.append(f"[{upg['key']}] {upg['name']} - {effect} {status}")
    screen_text = "\n".join(lines)
    print(center_text(screen_text))

keyboard.add_hotkey('space', on_space)
for upg in upgrades:    keyboard.add_hotkey(upg['key'], lambda k=upg['key']: buy_upgrade_key(k))


ROOM_WIDTH = 20
ROOM_HEIGHT = 20
PLAYER_CHAR = '~'
WALL_CHAR = '|'
FLOOR_CHAR = '*'

player_y, player_x = 10, 10

def create_map():
    game_map = [[FLOOR_CHAR for _ in range(ROOM_WIDTH)] for _ in range(ROOM_HEIGHT)]
    for x in range(ROOM_WIDTH):
        game_map[0][x] = WALL_CHAR
        game_map[ROOM_HEIGHT - 1][x] = WALL_CHAR
    for y in range(ROOM_HEIGHT):
        game_map[y][0] = WALL_CHAR
        game_map[y][ROOM_WIDTH - 1] = WALL_CHAR
        
    return game_map

def render_map():
    if game_state != 'explore':
        return
    display_map = [row[:] for row in current_map] 
    display_map[player_y][player_x] = PLAYER_CHAR
    map_str = "\n".join(["".join(row) for row in display_map])
    print(center_text(map_str + "\n\nUse WASD to move. Press ESC to exit."))

current_map = create_map()

def move(dx, dy):
    global player_x, player_y
    new_x = player_x + dx
    new_y = player_y + dy
    if current_map[new_y][new_x] != WALL_CHAR:
        player_x = new_x
        player_y = new_y
        render_map()

keyboard.add_hotkey('w', move, args=(0, -1))
keyboard.add_hotkey('s', move, args=(0, 1))
keyboard.add_hotkey('a', move, args=(-1, 0))
keyboard.add_hotkey('d', move, args=(1, 0))

def display_menu():
    if game_state != 'menu':
        return
    clear_screen()
    menu_text = (
        "MAIN MENU\n"
        "===========\n\n"
        "[1] Resources\n"
        "[2] Map\n"
        "[ESC] Quit Game\n"
    )
    print(center_text(menu_text))

def switch_to_incremental():
    global game_state
    game_state = 'incremental'
    display_incremental()

def switch_to_map():
    global game_state
    game_state = 'explore'
    render_map()

def switch_to_menu():
    global game_state
    game_state = 'menu'
    display_menu()

if __name__ == '__main__':
    current_map = create_map()
    display_menu()
    render_map()
    keyboard.wait('esc')
    clear_screen()
    print(center_text("Goodbye!"))
    time.sleep(1)
    clear_screen()
