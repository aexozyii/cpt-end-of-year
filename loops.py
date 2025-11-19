import time
import threading
import state
import actions
import persistence


def movement_loop():
    while True:
        if state.game_state == 'explore':
            # combine WASD inputs into a single dx,dy to allow diagonal movement
            kb = __import__('keyboard')
            left = kb.is_pressed('a')
            right = kb.is_pressed('d')
            up = kb.is_pressed('w')
            down = kb.is_pressed('s')
            dx = 0
            dy = 0
            if right and not left:
                dx = 1
            elif left and not right:
                dx = -1
            if down and not up:
                dy = 1
            elif up and not down:
                dy = -1
            if dx != 0 or dy != 0:
                actions.move(dx, dy)
                import render
                render.render_map()
        time.sleep(0.05)


def autosave_loop():
    while True:
        time.sleep(30)
        persistence.save_game()


movement_thread = threading.Thread(target=movement_loop, daemon=True)
autosave_thread = threading.Thread(target=autosave_loop, daemon=True)
