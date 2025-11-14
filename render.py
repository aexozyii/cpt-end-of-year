import os
import shutil
import state


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def center_text(text: str) -> str:
    columns, lines = shutil.get_terminal_size()
    text_lines = text.split('\n')
    centered_lines = [line.center(columns) for line in text_lines]
    vertical_padding = max((lines - len(text_lines)) // 2, 0)
    return '\n' * vertical_padding + '\n'.join(centered_lines)


def display_incremental():
    if state.game_state != 'incremental':
        return
    clear_screen()
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
    lines = [title, '', 'Welcome to the shop!', '', 'Buy items with the number keys:', '']
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
            lines.append(f'{i}. {it}')
    lines.append('')
    lines.append('Press I to close inventory')
    print(center_text('\n'.join(lines)))


def render_map():
    if state.game_state != 'explore':
        return
    print('\033[H', end='', flush=True)
    display_map = [row[:] for row in state.current_map]
    for (ty, tx), feature in state.TELEPORTS.items():
        if 0 <= ty < state.ROOM_HEIGHT and 0 <= tx < state.ROOM_WIDTH:
            if not (ty == state.player_y and tx == state.player_x):
                display_map[ty][tx] = 'S'
    display_map[state.player_y][state.player_x] = state.PLAYER_CHAR
    map_str = '\n'.join([''.join(row) for row in display_map])
    print(center_text(map_str + '\n\nUse WASD to move. Press Q to return to menu. Press ESC to exit.'))


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
