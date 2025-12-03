import keyboard
import persistence
import loops
import render
import actions
import state

def safe_hotkey(key, func):
    def wrapped():
        if state.game_state == 'transition':
            return
        try:
            func()
        except Exception:
            pass
    keyboard.add_hotkey(key, wrapped)

def main():
    # start background loops
    loops.movement_thread.start()
    loops.autosave_thread.start()

    # load save on startup if present
    persistence.load_game()

    # register key bindings (some are global but handlers check state)
    keyboard.on_release_key('space', lambda e: actions.on_space_release())
    safe_hotkey('space', actions.on_space)

    # numeric keys
    for k in '123456789':
        safe_hotkey(k, lambda key=k: actions.handle_number_key(key))

    safe_hotkey('r', render.switch_to_incremental)
    safe_hotkey('m', render.switch_to_map)
    safe_hotkey('q', render.switch_to_menu)
    safe_hotkey('b', actions.return_from_shop if hasattr(actions, 'return_from_shop') else (lambda: None))
    safe_hotkey('i', actions.toggle_inventory if hasattr(actions, 'toggle_inventory') else (lambda: None))
    safe_hotkey('f', actions.battle_attack if hasattr(actions, 'battle_attack') else (lambda: None))
    safe_hotkey('l', actions.flee_battle if hasattr(actions, 'flee_battle') else (lambda: None))

    # show start/menu
    render.display_start_menu()

    try:
        keyboard.wait('esc')
    except KeyboardInterrupt:
        pass
    persistence.save_game()

if __name__ == '__main__':
    main()
