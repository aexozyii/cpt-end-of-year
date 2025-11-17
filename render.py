import os
import shutil
import state
import persistence


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def center_text(text: str) -> str:
    columns, lines = shutil.get_terminal_size()
    text_lines = text.split('\n')
    centered_lines = [line.center(columns) for line in text_lines]
    vertical_padding = max((lines - len(text_lines)) // 2, 0)
    return '\n' * vertical_padding + '\n'.join(centered_lines)


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
        status = '(PURCHASED)' if upg['purchased'] else f'Cost: {upg["cost"]}'
        effect = f'+{upg["amount"]}/click' if upg['type'] == 'add' else f'x{upg["amount"]}/click'
        lines.append(f'[{upg["key"]}] {upg["name"]} - {effect} {status}')
    print(center_text('\n'.join(lines)))


def display_shop():
    if state.game_state != 'shop':
        return
    print('\033[H', end='', flush=True)
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


def render_map():
    if state.game_state != 'explore':
        return
    print('\033[H', end='', flush=True)
    display_map = [row[:] for row in state.current_map]
    # draw teleport markers
    for (ty, tx), feature in state.TELEPORTS.items():
        if 0 <= ty < state.ROOM_HEIGHT and 0 <= tx < state.ROOM_WIDTH:
            if not (ty == state.player_y and tx == state.player_x):
                display_map[ty][tx] = 'S'
    # draw enemies (alive)
    for (ey, ex), enemy in list(state.enemies.items()):
        if 0 <= ey < state.ROOM_HEIGHT and 0 <= ex < state.ROOM_WIDTH:
            # don't overwrite player char if standing on it
            if not (ey == state.player_y and ex == state.player_x):
                display_map[ey][ex] = 'E'
    display_map[state.player_y][state.player_x] = state.PLAYER_CHAR
    map_str = '\n'.join([''.join(row) for row in display_map])
    print(center_text(map_str + '\n\nUse WASD to move. Press Q to return to menu. Press ESC to exit.'))


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
    state.game_state = 'incremental'
    clear_screen()
    display_incremental()


def switch_to_map():
    # When opening the map via the menu, place the player at the map center
    state.game_state = 'explore'
    # center inside the walls
    state.player_x = state.ROOM_WIDTH // 2
    state.player_y = state.ROOM_HEIGHT // 2
    clear_screen()
    render_map()


def switch_to_menu():
    state.game_state = 'menu'
    display_menu()
