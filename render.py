import os
import shutil
import state
import persistence
import time
import re
try:
    from colorama import Fore, Style
except ImportError:
    class Fore:
        BLACK = ''
    class Style:
        DIM = ''
        RESET_ALL = ''


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
    columns, term_lines = shutil.get_terminal_size()
    ansi_re = re.compile(r"\x1b\[[0-9;]*m")
    printable_lens = [len(ansi_re.sub('', l)) for l in lines]
    max_printable = max(printable_lens) if printable_lens else 0
    left_pad = max((columns - max_printable) // 2, 0)
    padded = [(' ' * left_pad) + l for l in lines]
    vertical_padding = max((term_lines - len(lines)) // 2, 0)
    return '\n' * vertical_padding + '\n'.join(padded)


# module-level ANSI regex and previous render height track to avoid flashing
_ansi_re = re.compile(r"\x1b\[[0-9;]*m")
_last_render_height = 0


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


def get_stats_bar() -> str:
    """Build a horizontal stats bar showing player HP, SP, attack, defense, and floor.
    Returns a formatted string suitable for display at the top of the map."""
    attack_stat = getattr(state, 'attack', 0)
    defense_stat = getattr(state, 'defense', 0)
    hp_stat = getattr(state, 'player_hp', 100)
    max_hp_stat = getattr(state, 'player_max_hp', 100)
    floor_num = getattr(state, 'map_visit_count', 0)
    
    # Build bar: HP | ATK | DEF | Floor
    hp_bar = f"{Fore.LIGHTGREEN_EX}HP:{hp_stat}/{max_hp_stat}{Style.RESET_ALL}"
    atk_bar = f"{Fore.RED}ATK:{attack_stat}{Style.RESET_ALL}"
    def_bar = f"{Fore.BLUE}DEF:{defense_stat}{Style.RESET_ALL}"
    flr_bar = f"Floor: {floor_num}"
    
    stats_bar = f"  {hp_bar}  |  {atk_bar}  |  {def_bar}  |  {flr_bar}"
    return stats_bar


def display_inventory():
    if not state.has_bag:
        return
    clear_screen()
    title = 'INVENTORY'
    lines = [title, '', f'Slots: {len(state.inventory)}/{state.inventory_capacity}', '']
    # show equipped slots
    wep = state.equipped_weapon.get('name') if getattr(state, 'equipped_weapon', None) else 'None'
    arm = state.equipped_armour.get('name') if getattr(state, 'equipped_armour', None) else 'None'
    acc = state.equipped_accessory.get('name') if getattr(state, 'equipped_accessory', None) else 'None'
    lines.append(f'Equipped -> Weapon: {wep}   Armour: {arm}   Accessory: {acc}')
    lines.append('')
    
    # Display player stats
    lines.append('--- STATS ---')
    attack_stat = getattr(state, 'attack', 0)
    defense_stat = getattr(state, 'defense', 0)
    hp_stat = getattr(state, 'player_hp', 100)
    max_hp_stat = getattr(state, 'player_max_hp', 100)
    lines.append(f'Attack: {attack_stat}  |  Defense: {defense_stat}')
    lines.append(f'HP: {hp_stat}/{max_hp_stat}')
    
    # Display action upgrade levels
    lines.append('')
    lines.append('--- ACTION UPGRADES ---')
    for upg in state.action_upgrades:
        upg_name = upg.get('name', 'Unknown')
        upg_level = upg.get('level', 0)
        upg_max = upg.get('max_level', 1)
        bonus = int(upg_level * upg.get('amount', 0))
        lines.append(f'{upg_name}: Lv {upg_level}/{upg_max} (+{bonus})')
    
    lines.append('')
    if not state.inventory:
        lines.append('(empty)')
    else:
        # build two-column grid of items
        items = []
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
                if state.equipped_accessory and state.equipped_accessory.get('name') == name:
                    equipped = True
                desc = f'{i}. {name} (lvl {lvl}) [{itype}]' + (' [EQUIPPED]' if equipped else '')
            else:
                desc = f'{i}. {it}'
            items.append(desc)
        # render in two columns
        col_width = 42
        for left, right in zip(items[0::2], items[1::2] + [''] * (len(items[0::2]) - len(items[1::2]))):
            lines.append(f'{left:<{col_width}}{right}')
        # if odd item count, append the last one
        if len(items) % 2 == 1:
            lines.append(items[-1])
    lines.append('')
    lines.append('Press I to close inventory')
    lines.append('Press the number key to equip/use an item.')
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
    # Move cursor home; we'll overwrite previous frame in-place to avoid flashing
    print('\033[H', end='', flush=True)
    # build a printable map (placeholder for player) to ensure fixed-width rows
    printable_map = [list(row) for row in state.current_map]
    # track colored cells for later: (y, x) -> color_code (without wrapping char)
    cell_colors = {}
    
    # draw teleport markers with color
    for (ty, tx), feature in state.TELEPORTS.items():
        if 0 <= ty < state.ROOM_HEIGHT and 0 <= tx < state.ROOM_WIDTH:
            if not (ty == state.player_y and tx == state.player_x):
                # different teleport features show different letters and colors
                if feature == 'shop':
                    printable_map[ty][tx] = 'S'
                    cell_colors[(ty, tx)] = Fore.YELLOW
                elif feature == 'action_upgrades':
                    printable_map[ty][tx] = 'U'
                    cell_colors[(ty, tx)] = Fore.CYAN
                else:
                    printable_map[ty][tx] = 'S'
                    cell_colors[(ty, tx)] = Fore.YELLOW
    # draw enemies (alive) as single chars (B for boss)
    for (ey, ex), enemy in list(state.enemies.items()):
        if 0 <= ey < state.ROOM_HEIGHT and 0 <= ex < state.ROOM_WIDTH:
            if not (ey == state.player_y and ex == state.player_x):
                if enemy.get('is_boss'):
                    printable_map[ey][ex] = 'B'
                    cell_colors[(ey, ex)] = Fore.LIGHTRED_EX
                else:
                    printable_map[ey][ex] = 'E'
                    cell_colors[(ey, ex)] = Fore.RED

    # draw exit indicators for adjacent-room openings (only on floor cells)
    try:
        for (ey, ex), d in getattr(state, 'EXITS', {}).items():
            if 0 <= ey < state.ROOM_HEIGHT and 0 <= ex < state.ROOM_WIDTH:
                if printable_map[ey][ex] == state.FLOOR_CHAR:
                    arrow = {'left': '<', 'right': '>', 'up': '^', 'down': 'v'}.get(d, '+')
                    printable_map[ey][ex] = arrow
                    cell_colors[(ey, ex)] = Fore.GREEN
    except Exception:
        pass

    # place a simple placeholder for the player so printable widths stay consistent
    placeholder = '~'
    printable_map[state.player_y][state.player_x] = placeholder

    # build plain rows (fixed width)
    rows_plain = [''.join(r) for r in printable_map]

    # Double each character horizontally and apply colors
    rows_doubled = []
    for y, row in enumerate(rows_plain):
        colored_row = ''
        for x, ch in enumerate(row):
            if (y, x) in cell_colors:
                # Wrap the doubled char with the color code
                color = cell_colors[(y, x)]
                colored_row += f'{color}{ch * 2}{Style.RESET_ALL}'
            else:
                colored_row += ch * 2
        rows_doubled.append(colored_row)

    # now create colored rows by substituting the doubled placeholder with two colored player chars
    rows_colored = []
    ph = placeholder * 2
    pcol = state.PLAYER_CHAR * 2
    for r in rows_doubled:
        if ph in r:
            rows_colored.append(r.replace(ph, pcol, 1))
        else:
            rows_colored.append(r)

    # build legend lines to display to the right of the map (deduplicated, decorative items hidden)
    raw_legend = [
        'Legend:',
        f'{state.PLAYER_CHAR} You',
        f'{Fore.RED}E{Style.RESET_ALL}  Enemy',
        f'{Fore.LIGHTRED_EX}B{Style.RESET_ALL}  Boss',
        f'{Fore.YELLOW}S{Style.RESET_ALL}  Shop',
        f'{Fore.CYAN}U{Style.RESET_ALL}  Upgrade',
        '!  Event',
        'H  Fountain (heals)',
        '≈  Water (blocked)',
        '.  Floor',
        f'{state.WALL_CHAR}  Vertical Wall',
        f'{state.H_WALL_CHAR}  Horizontal Wall',
        '^  Rock (obstacle)',
    ]
    # preserve order but remove duplicates (some entries could be identical in rare cases)
    legend = []
    seen = set()
    for line in raw_legend:
        key = line
        if key not in seen:
            legend.append(line)
            seen.add(key)

    # combine colored rows with legend lines ensuring we use printable widths
    combined_lines = []
    max_lines = max(len(rows_colored), len(legend))
    for i in range(max_lines):
        left_colored = rows_colored[i] if i < len(rows_colored) else ' ' * (state.ROOM_WIDTH * 2)
        right = legend[i] if i < len(legend) else ''
        combined_lines.append(left_colored + '   ' + right)

    # small minimap showing all generated rooms (one row), highlight current room in red
    try:
        rooms = getattr(state, 'rooms', [])
        mini_items = []
        for i in range(len(rooms)):
            if i == getattr(state, 'current_room_index', 0):
                mini_items.append(state.Fore.LIGHTRED_EX + '■' + state.Style.RESET_ALL)
            else:
                mini_items.append('□')
        minimap_line = 'Rooms: ' + ' '.join(mini_items)
    except Exception:
        minimap_line = ''

    # Add stats bar at the top
    stats_bar = get_stats_bar()
    map_lines = [stats_bar, ''] + combined_lines + [''] + [ minimap_line, 'Use WASD to move (hold two keys for diagonals). Press Q to return to menu. Press ESC to exit.' ]

    # Render the centered block but avoid flicker by overwriting previous frame.
    out = center_block(map_lines)
    out_lines = out.split('\n')
    # calculate printable widths per line (strip ANSI)
    printable_lens = [_ansi_re.sub('', l) for l in out_lines]
    max_width = max((len(s) for s in printable_lens), default=0)

    global _last_render_height
    # print each line and pad with spaces to fully overwrite previous content
    for line in out_lines:
        plain = _ansi_re.sub('', line)
        pad = max_width - len(plain)
        try:
            print(line + (' ' * pad))
        except UnicodeEncodeError:
            # fallback: replace non-encodable chars so the renderer doesn't crash
            safe = line.encode('ascii', 'replace').decode('ascii')
            print(safe + (' ' * pad))
    # if previous frame had more lines, clear the remainder
    if _last_render_height > len(out_lines):
        blank = ' ' * max_width
        for _ in range(_last_render_height - len(out_lines)):
            print(blank)
    _last_render_height = len(out_lines)


def display_battle():
    if state.game_state != 'battle' or not state.current_battle_enemy:
        return
    clear_screen()
    enemy = state.current_battle_enemy
    title = f"{Fore.LIGHTRED_EX}BATTLE: {enemy.get('name', 'Enemy')}{Style.RESET_ALL}"
    lines = [title, '', enemy.get('ascii', ''), '']
    lines.append(f"{Fore.LIGHTRED_EX}Enemy HP:{Style.RESET_ALL} {enemy.get('hp', 0)}")
    lines.append(f"{Fore.LIGHTGREEN_EX}Your HP:{Style.RESET_ALL} {state.player_hp}/{state.player_max_hp}")
    # show transient battle status (shield, buff, debuff, skill points)
    s_status = getattr(state, 'current_battle_status', {})
    shield = s_status.get('player_shield', 0)
    buff = s_status.get('player_buff', 0)
    dcharge = s_status.get('enemy_debuff', 0)
    sp = s_status.get('skill_points', 0)
    sp_max = s_status.get('skill_points_max', sp)
    lines.append(f"{Fore.CYAN}Shield:{Style.RESET_ALL} {shield}   {Fore.GREEN}Buff:{Style.RESET_ALL} +{buff}   {Fore.YELLOW}EnemyDebuff:{Style.RESET_ALL} -{dcharge}   {Fore.LIGHTBLUE_EX}SP:{Style.RESET_ALL} {sp}/{sp_max}")
    lines.append('')
    # format actions into two columns with color coding
    left_actions = [
        f"{Fore.RED}[1] Execute (Red) - 1SP{Style.RESET_ALL}",
        f"{Fore.BLUE}[2] Defend (Blue) - 2SP{Style.RESET_ALL}",
        f"{Fore.WHITE}[3] Recover (White) -> +3SP{Style.RESET_ALL}"
    ]
    right_actions = [
        f"{Fore.BLACK}[4] Hack (Black) - 2SP{Style.RESET_ALL}",
        f"{Fore.GREEN}[5] Debug (Green) - 2SP{Style.RESET_ALL}",
        ""
    ]
    # pad each left action to width and join with right column to avoid wrapping
    max_rows = max(len(left_actions), len(right_actions))
    for i in range(max_rows):
        la = left_actions[i] if i < len(left_actions) else ''
        ra = right_actions[i] if i < len(right_actions) else ''
        lines.append(f"{la:<36}{ra}")
    lines.append('\n(Press 1-5 to use an action, I for action descriptions)')
    print(center_text('\n'.join(lines)))


def display_battle_action_descriptions():
    """Show detailed descriptions of each battle action."""
    if state.game_state != 'battle':
        return
    clear_screen()
    title = 'BATTLE ACTIONS'
    descriptions = [
        title,
        '=' * 40,
        '',
        '[1] Execute (Red) - 1 SP',
        'Direct attack. Deals damage equal to your',
        'attack stat plus any buffs.',
        'Resourceless and reliable.',
        '',
        '[2] Defend (Blue) - 2 SP',
        'Grant yourself a shield that blocks',
        'incoming damage this turn.',
        'Shield strength scales with defense.',
        '',
        '[3] Recover (White) - 0 SP',
        'Restore 3+ SP (modified by upgrades).',
        'Only action usable while stunned.',
        'Essential for maintaining action economy.',
        '',
        '[4] Hack (Black) - 2 SP',
        'Debuff the enemy, reducing their attack',
        'power for the rest of the battle.',
        'Cumulative debuff capped at 10.',
        '',
        '[5] Debug (Green) - 2 SP',
        'Buff yourself, increasing your attack',
        'for the rest of the battle.',
        'Scales with your current attack stat.',
        '',
        'Press I to return to battle...',
    ]
    print(center_text('\n'.join(descriptions)))


def display_action_upgrades():
    if state.game_state != 'action_upgrade':
        return
    clear_screen()
    title = 'ACTION UPGRADE ALTAR'
    lines = [title, '', 'Spend currency to upgrade your combat actions:', '']
    for upg in state.action_upgrades:
        lvl = upg.get('level', 0)
        ml = upg.get('max_level', 1)
        cost = upg.get('cost', 0)
        # grey out (dim) if player can't afford or already at max level
        key = upg.get('key')
        name = upg.get('name')
        desc = upg.get('desc')
        if lvl >= ml:
            # already maxed out
            line = f'[{key}] {name} Lv:{lvl}/{ml} - {desc} (MAXED)'
            line = f'{Fore.BLACK}{Style.DIM}{line}{Style.RESET_ALL}'
        elif state.count < cost:
            # can't afford
            line = f'[{key}] {name} Lv:{lvl}/{ml} - {desc} (Cost: {cost})'
            line = f'{Fore.BLACK}{Style.DIM}{line}{Style.RESET_ALL}'
        else:
            # can afford
            line = f'[{key}] {name} Lv:{lvl}/{ml} - {desc} (Cost: {cost})'
        lines.append(line)
    lines.append('')
    lines.append('[B] Return to Map')
    lines.append('(Press number key to buy upgrade)')
    print(center_text('\n'.join(lines)))


def display_victory_splash(reward: int):
    """Show a small victory splash screen with earned resources."""
    clear_screen()
    lines = ["YOU WON!", f"Resources gained: {reward}", ""]
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
    # don't allow switching to menu while in battle
    if state.game_state == 'battle':
        return
    state.game_state = 'menu'
    display_menu()
