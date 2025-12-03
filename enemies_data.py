# enemies_data.py
import random

# Enemy templates: name, base_hp, base_atk, base_reward, optional special (dict), ascii
ENEMY_TEMPLATES = {
    'human': {
        'name': 'Human',
        'base_hp': 80,
        'base_atk': 4,
        'base_reward': 200,
        'ascii': "  ,      ,\n (\\_/)\n (o.o)\n  >^ "
    },
    'dart_monkey': {
        'name': 'Dart Monkey',
        'base_hp': 130,
        'base_atk': 12,
        'base_reward': 450,
        'ascii': "  ,--.\n (____)\n /||\\\\\n  ||"
    },
    'teto_boss': {
        'name': 'Teto (Boss)',
        'base_hp': 400,
        'base_atk': 25,
        'base_reward': 2000,
        'special': {'type': 'stun', 'chance': 0.25, 'duration': 1},
        'ascii': (
            "   .-=========-.\n"
            "  .-===;  _   _  ;===-.\n"
            " /_   _| (o) (o) |_   _\\\n"
            "((_\\ (_ ,  .---.  , _) /_))\n"
            "   `-.__\\_/`---'\\_/__.-'\n"
            "       _/          \\_\n"
            "     /`   .-----.   `\\\n"
            "    /     |     |     \\\n"
            "   /      |     |      \\\n"
            "  |       '.___.'       |\n"
            "   \\                   /\n"
            "    `-.___________.-'\n"
        )
    }
}

# Spawn pools by tier (safe: no missing keys)
ENEMY_SPAWN_POOL = {
    'common': ['human'],
    'uncommon': ['dart_monkey'],
    'boss_room': ['teto_boss']
}

def create_enemy_instance(key: str, visits: int = 0) -> dict:
    tpl = ENEMY_TEMPLATES.get(key)
    if not tpl:
        # fallback generic enemy
        return {'name': 'Mook', 'hp': 50 + visits * 10, 'atk': 5 + visits, 'reward': 50 + visits * 10, 'ascii': '(?)'}

    # scale hp/atk/reward reasonably
    base_hp = int(tpl['base_hp'] + visits * (tpl.get('hp_scale', 10)))
    # make moderate scaling (linear then mild exponential)
    hp = base_hp + visits * base_hp // 3
    atk = int(tpl['base_atk'] + visits * (tpl.get('atk_scale', 1)))
    reward = int(tpl['base_reward'] * (1 + 0.2 * visits))
    inst = {
        'name': tpl['name'],
        'hp': hp,
        'atk': atk,
        'reward': reward,
        'ascii': tpl.get('ascii', '')
    }
    if 'special' in tpl:
        inst['special'] = dict(tpl['special'])
    return inst
