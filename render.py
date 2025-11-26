import os
import shutil
import state
import persistence
import time


def clear_screen():
    print('\033[H\033[2J', end='', flush=True)


def center_text(text: str) -> str:
    try:
        columns, lines = shutil.get_terminal_size()
    except Exception:
        # Fallback for environments where get_terminal_size fails
        columns, lines = 80, 24 
        
    text_lines = text.split('\n')
    
    vertical_padding_top = max((lines - len(text_lines)) // 2, 0)
    vertical_padding_bottom = max(lines - len(text_lines) - vertical_padding_top, 0)

    centered_lines = [line.center(columns) for line in text_lines]
    
    full_output = ('\n' * vertical_padding_top + 
                   '\n'.join(centered_lines) + 
                   '\n' * vertical_padding_bottom)
    
    return full_output


def display_start_menu():
    """Display the initial start menu (New Game / Load Game)."""
    # Force clear screen with os.system just in case your terminal is stubborn here
    os.system('cls' if os.name == 'nt' else 'clear')

    if state.game_state != 'start_menu':
        # This should ideally never be reached when called from main() startup
        print("Error: Not in start menu state.")
        return
    
    lines = ['GAME MENU', '==========', '']
    lines.append('[1] New Game')
    if persistence.has_save_file():
        lines.append('[2] Load Game')
    lines.append('[ESC] Exit')
    menu_text = '\n'.join(lines) + '\n'
    
    # Use the center_text function and ensure immediate flush
    print(center_text(menu_text), end='', flush=True) 


def display_incremental():
    if state.game_state != 'incremental':
        return
    # Generate the full screen content as one large string
    title = 'IDK what resource this is'
    counter = f'Total Currency: {state.count}'
    prompt = f'(Press SPACE to earn +{state.per_click} | Press ESC to quit)'
    lines = [title, '', counter, '', prompt, '']
    lines.append('Upgrades:')
    for upg in state.upgrades:
        if upg.get('purchased'):
            status = '(PURCHASED)'
        else:
            meta_req = upg.get('meta_req')
            if meta_req and not state.meta_upgrades_state.get(meta_req, False):
                status = '(LOCKED)'
            else:
                status = f'Cost: {upg["cost"]}'
        effect = f'+{upg["amount"]}/click' if upg['type'] == 'add' else f'x{upg["amount"]}/click'
        lines.append(f'[{upg["key"]}] {upg["name"]} - {effect} {status}')
    full_output = center_text('\n'.join(lines))
    print(full_output, end='', flush=True)


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
    
    # Use colorama if available in state module
    fore = state.Fore if hasattr(state, 'Fore') else ''
    style = state.Style if hasattr(state, 'Style') else ''
    
    title = f"BATTLE: {enemy.get('name', 'Enemy')}"
    lines = [title, '', enemy.get('ascii', ''), '']
    lines.append(f"Enemy HP: {enemy.get('hp', 0)}")
    lines.append(f"Your HP: {state.player_hp}/{state.player_max_hp}")
    lines.append(f"Your Attack: {state.attack} | Your Defense: {state.defense}")
    lines.append('')
    lines.append('Choose an action:')

    # Display actions using keys 1-5
    for key, action in state.BATTLE_ACTIONS.items():
        # Map color names to colorama codes if available
        color_code = getattr(state, f"Fore.{action['color']}_EX", fore) if hasattr(state, 'Fore') else ''
        lines.append(f"[{key}] {color_code}{action['name']}{style.RESET_ALL}")
    
    lines.append('')
    lines.append('[L] Flee Battle')
    print(center_text('\n'.join(lines)))


def display_death_splash():
    """Show a death splash screen (rogue-lite reset)."""
    clear_screen()
    lines = ['YOU DIED', '']
    lines.append('')
    print(center_text('\n'.join(lines)))


def display_menu():
    """Display the main in-game menu."""
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
    menu_text = '\n'.join(lines) + '\n'
    print(center_text(menu_text), end='', flush=True)


def switch_to_incremental():
    """Only allow opening incremental view from the main menu."""
    if state.game_state != 'menu':
        return
    state.game_state = 'incremental'
    # Use the existing function to render the incremental view
    display_incremental()


def switch_to_map():
    # Only allow opening the map from the main menu
    if state.game_state != 'menu':
        # silently block when not in main menu
        return
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
