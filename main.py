import keyboard
import os
import shutil
import time
import json
import threading

count = 0
per_click = 1
game_state = 'menu'
movement_lock = threading.Lock()  
last_space_time = 0.0
SAVE_FILE = os.path.join(os.path.dirname(__file__), 'save.json')
prev_state = None
prev_player_pos = None

upgrades = [
    {'key': '1', 'name': 'Better Fingers', 'cost': 10,  'type': 'add',  'amount': 1, 'purchased': False},
    {'key': '2', 'name': 'Auto Clicker',  'cost': 50,  'type': 'add',  'amount': 5, 'purchased': False},
    {'key': '3', 'name': 'Double Tap',    'cost': 200, 'type': 'mult', 'amount': 2, 'purchased': False},
]

shop_items = [
    {'key': '1', 'name': 'Sword', 'cost': 100, 'type': 'weapon', 'amount': 5, 'purchased': False},
    {'key': '2', 'name': 'Armour', 'cost': 80,  'type': 'armour', 'amount': 5, 'purchased': False},
    {'key': '3', 'name': 'Bag',    'cost': 50,  'type': 'bag',    'amount': 1, 'purchased': False},
]
import keyboard
import render
import actions
import persistence
import loops
import state

keyboard.add_hotkey('space', actions.on_space)
for upg in state.upgrades:
    keyboard.add_hotkey(upg['key'], lambda k=upg['key']: actions.buy_upgrade_key(k))
for item in state.shop_items:
    keyboard.add_hotkey(item['key'], lambda k=item['key']: actions.buy_shop_item(k))

keyboard.add_hotkey('r', render.switch_to_incremental)
keyboard.add_hotkey('m', render.switch_to_map)
keyboard.add_hotkey('q', render.switch_to_menu)
keyboard.add_hotkey('b', actions.return_from_shop)
keyboard.add_hotkey('i', actions.toggle_inventory)


def main():
    # load saved state, start background loops, and show menu
    persistence.load_game()
    # start threads
    loops.movement_thread.start()
    loops.autosave_thread.start()
    # show initial menu
    import render as _render
    _render.display_menu()
    try:
        # block until ESC pressed
        keyboard.wait('esc')
    except KeyboardInterrupt:
        pass
    # on exit, save once
    persistence.save_game()


if __name__ == '__main__':
    main()