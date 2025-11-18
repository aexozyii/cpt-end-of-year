import os
import shutil
import state
import persistence
import time


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def center_text(text: str) -> str:
    import re
    # compute terminal size
    columns, lines = shutil.get_terminal_size()
    text_lines = text.split('\n')
    # ANSI escape sequence regex
    ansi_re = re.compile(r"\x1b\[[0-9;]*m")
    centered_lines = []
    for line in text_lines:
        # compute printable length by stripping ANSI sequences
        printable = ansi_re.sub('', line)
        printable_len = len(printable)
        if printable_len >= columns:
            # no centering if line is too long
            centered_lines.append(line)
        else:
            left_pad = max((columns - printable_len) // 2, 0)
            centered_lines.append(' ' * left_pad + line)
    vertical_padding = max((lines - len(text_lines)) // 2, 0)
    return '\n' * vertical_padding + '\n'.join(centered_lines)


def center_block(lines: list) -> str:
    """Center a block of lines using a single left padding so each row aligns vertically.

    This computes the printable width of each line (stripping ANSI sequences), finds
    the maximum printable width, computes one left padding to center the block, and
    prefixes every line with that padding. Returns the block as a single string
    with vertical centering applied.
    """
    import re
    columns, term_lines = shutil.get_terminal_size()
    ansi_re = re.compile(r"\x1b\[[0-9;]*m")
    printable_lens = [len(ansi_re.sub('', l)) for l in lines]
    max_printable = max(printable_lens) if printable_lens else 0
    left_pad = max((columns - max_printable) // 2, 0)
    padded = [(' ' * left_pad) + l for l in lines]
    vertical_padding = max((term_lines - len(lines)) // 2, 0)
    return '\n' * vertical_padding + '\n'.join(padded)


def display_start_menu():
    """Display the initial start menu (New Game / Load Game)."""
    if state.game_state != 'start_menu':
        return
    clear_screen()
    lines = ['GAME MENU', '==========', '']
    lines.append('[1] New Game')
    if persistence.has_save_file():
        lines.append('[2] Load Game')
    lines.append('[ESC] Exit')
    menu_text = '\n'.join(lines) + '\n'
    print(center_text(menu_text))


def display_incremental():
    if state.game_state != 'incremental':
        return
    print('\033[H', end='', flush=True)
    title = 'game placeholder'
    counter = f'Total Currency: {state.count}'
    prompt = f'(Press SPACE to earn +{state.per_click} | Press ESC to quit)'
    lines = [title, '', counter, '', prompt, '']
    lines.append('Upgrades:')
    for upg in state.upgrades:
        if upg.get('purchased'):
            status = '(PURCHASED)'
        else:
            # show locked status when upgrade requires a meta unlock
            meta_req = upg.get('meta_req')
            if meta_req and not state.meta_upgrades_state.get(meta_req, False):
                status = '(LOCKED)'
            else:
                status = f'Cost: {upg["cost"]}'
        effect = f'+{upg["amount"]}/click' if upg['type'] == 'add' else f'x{upg["amount"]}/click'
        lines.append(f'[{upg["key"]}] {upg["name"]} - {effect} {status}')
    print(center_text('\n'.join(lines)))


def display_meta_upgrades(meta_gain: int = 0):
    """Show meta-upgrade screen where player spends meta-currency after death.
    `meta_gain` is how much was just awarded this death (for messaging).
    """
    if state.game_state != 'meta':
        return
    clear_screen()
    title = 'META UPGRADES'
    lines = [title, '', f'You earned +{meta_gain} meta-currency this run!', f'Meta Currency: {state.meta_currency}', '']
    lines.append('Buy persistent upgrades with number keys:')
    lines.append('')
    for m in state.meta_upgrades:
        status = '(PURCHASED)' if m.get('purchased') else f'Cost: {m.get("cost")}'
        lines.append(f'[{m.get("key")}] {m.get("name")} - {m.get("desc")} {status}')
    lines.append('')
    lines.append('[B] Finish and start a new run')
    lines.append('(Press the number key to buy, B to finish)')
    print(center_text('\n'.join(lines)))


def display_shop():
    if state.game_state != 'shop':
        return
    clear_screen()
    title = 'SHOP'
    lines = [
        title,
        '',
        'Welcome to the shop!',
        '',
        '[B] Return to Map',
        '',
        'Buy items with the number keys:',
        '',
    ]
    for item in state.shop_items:
        if item['purchased']:
            status = '(PURCHASED)'
        else:
            status = f'Cost: {item["cost"]}'
        if item['type'] == 'weapon':
            effect = f'+{item["amount"]} attack'
        elif item['type'] == 'armour':
            effect = f'+{item["amount"]} defense'
        elif item['type'] == 'bag':
            effect = f'Inventory +{item["amount"]*10}'
        else:
            effect = ''
        lines.append(f'[{item["key"]}] {item["name"]} - {effect} {status}')
    lines.append('')
    lines.append('Press B to return to the map')
    print(center_text('\n'.join(lines)))


def display_inventory():
    if not state.has_bag:
        return
    clear_screen()
    title = 'INVENTORY'
    lines = [title, '', f'Slots: {len(state.inventory)}/{state.inventory_capacity}', '']
    if not state.inventory:
        lines.append('(empty)')
    else:
        for i, it in enumerate(state.inventory, 1):
            if isinstance(it, dict):
                name = it.get('name', 'item')
                lvl = it.get('level', 1)
                itype = it.get('type', '')
                equipped = False
                if state.equipped_weapon and state.equipped_weapon.get('name') == name:
                    equipped = True
                if state.equipped_armour and state.equipped_armour.get('name') == name:
                    equipped = True
                lines.append(f'{i}. {name} (level {lvl}) [{itype}]' + (' [EQUIPPED]' if equipped else ''))
                # add ascii art below the item
                ascii_art = it.get('ascii', '')
                if ascii_art:
                    for art_line in ascii_art.split('\n'):
                        if art_line.strip() == '':
                            continue
                        lines.append('    ' + art_line)
            else:
                lines.append(f'{i}. {it}')
    lines.append('')
    lines.append('Press I to close inventory')
    lines.append('Press the number key to equip a sword/armour.')
    print(center_text('\n'.join(lines)))


def flash_message(msg: str, delay: float = 0.8):
    """Show a brief centered message then re-render current view."""
    clear_screen()
    print(center_text(msg))
    time.sleep(delay)
    # re-render according to current state
    if state.game_state == 'menu':
        display_menu()
    elif state.game_state == 'incremental':
        display_incremental()
    elif state.game_state == 'explore':
        render_map()
    elif state.game_state == 'shop':
        display_shop()
    elif state.game_state == 'inventory':
        display_inventory()
    elif state.game_state == 'battle':
        display_battle()
    elif state.game_state == 'meta':
        display_meta_upgrades(0)


def render_map():
    if state.game_state != 'explore':
        return
    # clear screen to avoid previous frames stacking
    clear_screen()
    # build a printable map (placeholder for player) to ensure fixed-width rows
    printable_map = [list(row) for row in state.current_map]
    # draw teleport markers
    for (ty, tx), feature in state.TELEPORTS.items():
        if 0 <= ty < state.ROOM_HEIGHT and 0 <= tx < state.ROOM_WIDTH:
            if not (ty == state.player_y and tx == state.player_x):
                printable_map[ty][tx] = 'S'
    # draw enemies (alive) as single chars (B for boss)
    for (ey, ex), enemy in list(state.enemies.items()):
        if 0 <= ey < state.ROOM_HEIGHT and 0 <= ex < state.ROOM_WIDTH:
            if not (ey == state.player_y and ex == state.player_x):
                printable_map[ey][ex] = 'B' if enemy.get('is_boss') else 'E'

    # draw exit indicators for adjacent-room openings (only on floor cells)
    try:
        for (ey, ex), d in getattr(state, 'EXITS', {}).items():
            if 0 <= ey < state.ROOM_HEIGHT and 0 <= ex < state.ROOM_WIDTH:
                if printable_map[ey][ex] == state.FLOOR_CHAR:
                    arrow = {'left': '<', 'right': '>', 'up': '^', 'down': 'v'}.get(d, '+')
                    printable_map[ey][ex] = arrow
    except Exception:
        pass

    # place a simple placeholder for the player so printable widths stay consistent
    placeholder = '~'
    printable_map[state.player_y][state.player_x] = placeholder

    # build plain rows (fixed width)
    rows_plain = [''.join(r) for r in printable_map]

    # now create colored rows by substituting the placeholder with the colored player char
    rows_colored = []
    for r in rows_plain:
        if placeholder in r:
            rows_colored.append(r.replace(placeholder, state.PLAYER_CHAR, 1))
        else:
            rows_colored.append(r)

    # build legend lines to display to the right of the map
    legend = [
        'Legend:',
        f'{state.PLAYER_CHAR} You',
        'E  Enemy',
        'B  Boss',
        'S  Shop',
        '!  Event',
        'H  Fountain (heals)',
        '.  Floor',
        '|  Wall',
    ]

    # combine colored rows with legend lines ensuring we use printable widths
    combined_lines = []
    max_lines = max(len(rows_colored), len(legend))
    for i in range(max_lines):
        left_colored = rows_colored[i] if i < len(rows_colored) else ' ' * state.ROOM_WIDTH
        right = legend[i] if i < len(legend) else ''
        combined_lines.append(left_colored + '   ' + right)

    map_lines = combined_lines + [''] + [ 'Use WASD to move. Press Q to return to menu. Press ESC to exit.' ]
    print(center_block(map_lines))


def display_battle():
    if state.game_state != 'battle' or not state.current_battle_enemy:
        return
    clear_screen()
    enemy = state.current_battle_enemy
    title = f"BATTLE: {enemy.get('name', 'Enemy')}"
    lines = [title, '', enemy.get('ascii', ''), '']
    lines.append(f"Enemy HP: {enemy.get('hp', 0)}")
    lines.append(f"Your HP: {state.player_hp}/{state.player_max_hp}")
    lines.append('')
    lines.append('[F] Attack    [L] Flee')
    lines.append('\n(Press F to attack, L to flee)')
    print(center_text('\n'.join(lines)))


def display_death_splash():
    """Show a death splash screen (rogue-lite reset)."""
    clear_screen()
    lines = ['YOU DIED', '']
    lines.append('')
    print(center_text('\n'.join(lines)))


def display_menu():
    if state.game_state != 'menu':
        return
    clear_screen()
    # Build menu lines and include inventory hint if player has a bag
    lines = [
        'MAIN MENU',
        '===========',
        '',
        '[R] Resources (incremental)',
        '[M] Map',
    ]
    if state.has_bag:
        lines.append('[I] Inventory')
    lines.extend([
        '[Q] Menu',
        '[ESC] Quit Game',
    ])
    menu_text = '\n'.join(lines) + '\n'
    print(center_text(menu_text))


def switch_to_incremental():
    # Only allow opening incremental view from the main menu
    if state.game_state != 'menu':
        # silently block when not in main menu
        return
    state.game_state = 'incremental'
    clear_screen()
    display_incremental()


def switch_to_map():
    # Only allow opening the map from the main menu
    if state.game_state != 'menu':
        # silently block when not in main menu
        return
    # When opening the map via the menu, place the player at the map center
    # increment visit counter to increase difficulty/spawns
    state.map_visit_count = getattr(state, 'map_visit_count', 0) + 1
    # regenerate rooms for this visit count and load the first room
    try:
        state.rooms = state.create_rooms(5, visits=state.map_visit_count)
        # restore or clamp current room if present, otherwise start at 0
        idx = getattr(state, 'current_room_index', 0)
        try:
            idx = max(0, min(idx, len(state.rooms) - 1))
        except Exception:
            idx = 0
        state.current_room_index = idx
        state.load_room(idx)
    except Exception:
        state.current_map = state.create_map()
    state.game_state = 'explore'
    # center inside the walls
    state.player_x = state.ROOM_WIDTH // 2
    state.player_y = state.ROOM_HEIGHT // 2
    clear_screen()
    render_map()


def switch_to_menu():
    state.game_state = 'menu'
    display_menu()
