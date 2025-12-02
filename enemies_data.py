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

ENEMY_TEMPLATES = {
    'human': {
        'name': 'Human',
        'base_hp': 80,
        'base_atk': 4,
        'base_reward': 200,
        'ascii': "  ,      ,\\n (\\_/)\\n (o.o)\\n  >^ "
    },
    'dart_monkey': {
        'name': 'Dart Monkey',
        'base_hp': 130,
        'base_atk': 12,
        'base_reward': 450,
        'ascii': "  ,--.\\n (____)\\n /||\\\\\\n  ||"
    },
    'teto_boss': {
        'name': 'Teto (Boss)',
        'base_hp': 400,
        'base_atk': 25,
        'base_reward': 2000,
        'special': {
            'type': 'stun',
            'chance': 0.25,
            'duration': 1,
        },
        'ascii': """   .-=========-.
  .-===;  _   _  ;===-.
 /_   _| (o) (o) |_   _\\
((_\ (_ ,  .---.  , _) /_))
   `-.__\_/`---'\_/__.-'
       _/          \_
     /`   .-----.   `\\n+    /     |     |     \\
   /      |     |      \\
  |       '.___.'       |
   \                   /
    `-.___________.-'
"""
    },
}

ENEMY_SPAWN_POOL = {
    'common': ['human', 'goblin'],
    'uncommon': ['dart_monkey'],
    'boss_room': ['teto_boss']
    # You can expand this for different room types or difficulties
}

def apply_stun_debuff(target_state, duration_turns=1):
    """
    Applies a stun effect to the player state, preventing actions next turn.
    """
    target_state['is_stunned'] = True
    target_state['stun_duration'] = duration_turns
    print(f"DEBUG: Player has been stunned for {duration_turns} turn(s)!")

def check_player_stun_status(player_state):
    """
    Checks if the player can act this turn and updates the stun duration.
    This function would run at the start of the player's turn in a game loop.
    """
    if player_state.get('is_stunned', False):
        print("You are stunned and cannot act this turn!")
        player_state['stun_duration'] -= 1
        
        if player_state['stun_duration'] <= 0:
            player_state['is_stunned'] = False
            player_state['stun_duration'] = 0
            print("The stun wears off.")
        return True # Player is stunned, cannot take action
    return False # Player can take action