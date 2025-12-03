# loops.py
import time
import threading
import keyboard
import actions 
import render
import state
import persistence

MOVEMENT_DELAY = 0.05
AUTOSAVE_DELAY = 30.0

def movement_loop():
    while True:
        if state.game_state == 'explore':
            dx = (1 if keyboard.is_pressed('d') else 0) - (1 if keyboard.is_pressed('a') else 0)
            dy = (1 if keyboard.is_pressed('s') else 0) - (1 if keyboard.is_pressed('w') else 0)
            if dx != 0 or dy != 0:
                actions.move(dx, dy) if hasattr(actions, 'move') else None
                render.render_map()
        time.sleep(MOVEMENT_DELAY)

def autosave_loop():
    while True:
        time.sleep(AUTOSAVE_DELAY)
        # skip saving during battle or transition states
        if state.game_state not in ('battle', 'transition'):
            try:
                persistence.save_game()
            except Exception:
                pass

movement_thread = threading.Thread(target=movement_loop, daemon=True)
autosave_thread = threading.Thread(target=autosave_loop, daemon=True)
