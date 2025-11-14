import time
import threading
import state
import actions
import persistence


def movement_loop():
    while True:
        if state.game_state == 'explore':
            moved = False
            if __import__('keyboard').is_pressed('w'):
                actions.move(0, -1)
                moved = True
            if __import__('keyboard').is_pressed('s'):
                actions.move(0, 1)
                moved = True
            if __import__('keyboard').is_pressed('a'):
                actions.move(-1, 0)
                moved = True
            if __import__('keyboard').is_pressed('d'):
                actions.move(1, 0)
                moved = True
            if moved:
                # render map once after moves
                import render
                render.render_map()
        time.sleep(0.05)


def autosave_loop():
    while True:
        time.sleep(30)
        persistence.save_game()


movement_thread = threading.Thread(target=movement_loop, daemon=True)
autosave_thread = threading.Thread(target=autosave_loop, daemon=True)
