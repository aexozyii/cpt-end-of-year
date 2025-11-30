import os
import shutil
import state
import persistence
import time
import re
import traceback # Added for debugging placeholders


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def center_text(text: str) -> str:
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
    """Center a block of lines using a single left padding so each row aligns vertically."""
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
    if state.game_state != 'menu':
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
    # Move cursor home; we'll overwrite previous frame in-place to avoid flashing
    print('\033[H', end='', flush=True)
    
    try:
        # build a printable map (placeholder for player) to ensure fixed-width rows
        printable_map = [list(row) for row in state.current_map]
        # Rest of the map rendering logic requires many specific state variables.
        # If they aren't defined, this function would crash. We wrap in try-except
        # to just print a placeholder if map logic isn't fully implemented yet.
        # Example of commented out original logic that needs state variables:
        # for (ty, tx), feature in state.TELEPORTS.items():
        #     if 0 <= ty < state.ROOM_HEIGHT and 0 <= tx < state.ROOM_WIDTH:
        #         if not (ty == state.player_y and tx == state.player_x):
        #             printable_map[ty][tx] = 'S'
        # ...
        print('\n'.join(''.join(row) for row in printable_map))

    except Exception:
        # Fallback if the required state variables for the map aren't set up yet
        print(center_text("Map rendering placeholder. Move logic requires more state variables."))
        # print(traceback.format_exc()) # Uncomment this line to debug missing state variables


def display_menu():
    # Helper alias
    display_start_menu()

# --- Functions to handle state switching (needed for main.py bindings) ---

def switch_to_incremental():
    if state.game_state != 'battle':
        state.game_state = 'incremental'
        display_incremental()

def switch_to_map():
    if state.game_state != 'battle':
        state.game_state = 'explore'
        render_map()

def switch_to_menu():
    if state.game_state != 'battle':
        state.game_state = 'menu'
        display_menu()


# --- Display Battle Function (as modified previously) ---

def display_battle():
    """Renders the battle interface with improved formatting."""
    if state.game_state not in ['battle', 'meta', 'explore']:
        return

    # ANSI Color Codes
    RED = '\033[91m'
    BLUE = '\033[94m'
    WHITE = '\033[97m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    ENDC = '\033[0m'

    lines = []
    lines.append(f"{CYAN}--- TURN {state.turn_count} ---{ENDC}")
    lines.append("")

    # --- ENEMY STATS ---
    lines.append(f"{RED}ENEMY STATUS:{ENDC}")
    lines.append(f"  HP: {WHITE}[{RED}{state.enemy_hp}/{state.enemy_max_hp}{WHITE}]{ENDC}")
    lines.append(f"  Shield: {WHITE}[{BLUE}{state.enemy_shield}{WHITE}]{ENDC}")
    lines.append(f"  Status Effects: {YELLOW}Buffs: {state.enemy_buffs} | Debuffs: {state.enemy_debuffs}{ENDC}")
    lines.append("")

    lines.append("--------------------------------------------------")

    # --- PLAYER STATS ---
    lines.append(f"{GREEN}PLAYER STATUS:{ENDC}")
    lines.append(f"  HP: {WHITE}[{RED}{state.player_hp}/{state.player_max_hp}{WHITE}]{ENDC}")
    lines.append(f"  Shield: {WHITE}[{BLUE}{state.player_shield}{WHITE}]{ENDC}")
    lines.append(f"  Status Effects: {YELLOW}Buffs: {state.player_buffs} | Debuffs: {state.player_debuffs}{ENDC}")
    lines.append("")
    
    lines.append("--------------------------------------------------")

    # --- BATTLE LOG ---
    lines.append(f"{MAGENTA}LOG:{ENDC}")
    for msg in state.log_messages:
        lines.append(f"  {msg}")
    lines.append("")
    
    lines.append("--------------------------------------------------")

    # --- ACTIONS/MENU ---
    if state.game_state == 'battle':
        lines.append(f"{CYAN}ACTIONS LEFT: {state.player_actions_left}{ENDC}")
        lines.append("Choose an action (Press key):")
        lines.append(f"  [{RED}R{ENDC}] Execute Code (Deal Damage)")
        lines.append(f"  [{BLUE}B{ENDC}] Defend Code (Gain Shield)")
        lines.append(f"  [{WHITE}W{ENDC}] Recover (Heal HP)")
        lines.append(f"  [{YELLOW}K{ENDC}] Hack (Debuff Enemy)")
        lines.append(f"  [{GREEN}G{ENDC}] Debug (Buff Self)")
        lines.append(f"  [{CYAN}L{ENDC}] Leave Battle")

    elif state.game_state == 'explore':
         lines.append(f"{GREEN}Battle finished. Press [M] to return to map.{ENDC}")
    
    elif state.game_state == 'meta':
        lines.append(f"{RED}You were defeated. Press [B] to go to Meta Upgrades.{ENDC}")

    print(center_block(lines))
