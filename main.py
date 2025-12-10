import keyboard
import os
import shutil
import time
import json
import threading
import render
import actions
import persistence
import loops
import state

count = 0
per_click = 1
game_state = 'menu'
movement_lock = threading.Lock()
last_space_time = 0.0
SAVE_FILE = os.path.join(os.path.dirname(__file__), 'save.json')
prev_state = None
prev_player_pos = None

upgrades = [
    {
        'key': '1',
        'name': 'top left',
        'cost': 10,
        'type': 'add',
        'amount': 1,
        'purchased': False,
    },
    {
        'key': '2',
        'name': 'sumsum',
        'cost': 50,
        'type': 'add',
        'amount': 5,
        'purchased': False,
    },
    {
        'key': '3',
        'name': 'dt',
        'cost': 200,
        'type': 'mult',
        'amount': 2,
        'purchased': False,
    },
    {
        'key': '4',
        'name': 'bottom right',
        'cost': 500,
        'type': 'mult',
        'amount': 3,
        'purchased': False,
    },
    {
        'key': '5',
        'name': 'my ball',
        'cost': 1000,
        'type': 'add',
        'amount': 10,
        'purchased': False,
    },
    {
        'key': '6',
        'name': 'yo bro...',
        'cost': 5000,
        'type': 'mult',
        'amount': 5,
        'purchased': False,
    },
    {
        'key': '7',
        'name': 'Whatever you do, at the crossroads, do NOT turn left.',
        'cost': 10000,
        'type': 'add',
        'amount': 20,
        'purchased': False,
    },
    {
        'key': '8',
        'name': 'yo bro. js play the game alrdy',
        'cost': 50000,
        'type': 'mult',
        'amount': 10,
        'purchased': False,
    },
    {
        'key': '9',
        'name': 'bro',
        'cost': 100000,
        'type': 'add',
        'amount': 50,
        'purchased': False,
    },
]

shop_items = [
    {
        'key': '1',
        'name': 'Sword',
        'cost': 100,
        'type': 'weapon',
        'amount': 5,
        'purchased': False,
    },
    {
        'key': '2',
        'name': 'Armour',
        'cost': 80,
        'type': 'armour',
        'amount': 5,
        'purchased': False,
    },
    {
        'key': '3',
        'name': 'Bag',
        'cost': 50,
        'type': 'bag',
        'amount': 1,
        'purchased': False,
    },
]


_should_exit = False


def exit_game():
    global _should_exit
    _should_exit = True


keyboard.add_hotkey('space', actions.on_space)
# Register numeric keys 1-9 to a dispatcher that behaves based on current view
for k in list('123456789'):
    keyboard.add_hotkey(k, lambda key=k: actions.handle_number_key(key))


keyboard.add_hotkey('r', render.switch_to_incremental)
keyboard.add_hotkey('m', render.switch_to_map)
keyboard.add_hotkey('q', render.switch_to_menu)
keyboard.add_hotkey('b', actions.return_from_shop)
keyboard.add_hotkey('i', actions.toggle_inventory)
keyboard.add_hotkey('esc', exit_game)
keyboard.on_release_key('space', lambda e: actions.on_space_release())


def main():
    global _should_exit
    # start threads
    loops.movement_thread.start()
    loops.autosave_thread.start()
    # show initial game menu
    import render as _render
    _render.display_menu()
    try:
        # non-blocking loop that checks for exit flag
        while not _should_exit:
            time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    # on exit, save once
    persistence.save_game()


if __name__ == '__main__':
    main()
