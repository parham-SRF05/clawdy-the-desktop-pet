"""Settings, stored in %USERPROFILE%\\.claude-pet\\config.json (created with defaults on first run)."""
import copy
import json
import os

CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.claude-pet')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')

DEFAULTS = {
    'name': 'Clawdy',
    'scale': 2,                   # screen pixels per art pixel (the character is 32x20 art pixels)
    'walk_speed': 1.0,            # 1.0 = normal
    'wander': True,               # walk around when Claude is idle
    'walk_width_percent': 100,    # how much of the taskbar the pet walks on (10-100)
    'walk_align': 'center',       # where that part is: "left", "center" or "right"
    'bubbles': True,              # speech bubbles
    'react_to_claude': True,
    'start_with_claude_code': True,  # the pet starts by itself when a Claude Code session starts
    'hide_in_fullscreen': True,   # hide while a game or video fills the main screen
    'sleep_after_seconds': 0,     # fall asleep after this long with nothing happening (0 = never)
    'tricks': True,               # little cute moments (wave, dance, hop, look around) while wandering
    'store_task_titles': True,    # the hover panel shows the first line of what you asked Claude
    'skin': '',                   # folder name in .claude-pet\skins (empty = built-in pixel art)
    'colors': {},                 # override any built-in colour, e.g. {"body": "#6aa3ff"}
    'messages': {
        'done': 'Done!',
        'needs_you': 'Needs you!',
        'hello': 'Hi!',
        'bye': 'Bye!',
        'error': 'Uh oh...',
        'compact': 'Tidying up...',
        'poke': 'Hehe!',
    },
}

LIMITS = {'scale': (1, 8), 'walk_speed': (0.2, 3.0), 'sleep_after_seconds': (0, 86400),
          'walk_width_percent': (10, 100)}


def _merge(base, override):
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if key not in out:
            continue  # unknown setting: ignore
        if isinstance(out[key], dict) and isinstance(value, dict):
            out[key].update({k: v for k, v in value.items() if isinstance(v, str)})
        elif isinstance(out[key], bool):
            out[key] = bool(value)
        elif isinstance(out[key], (int, float)) and isinstance(value, (int, float)) and not isinstance(value, bool):
            low, high = LIMITS.get(key, (value, value))
            out[key] = type(out[key])(min(max(value, low), high))
        elif isinstance(out[key], str) and isinstance(value, str):
            out[key] = value
    return out


def load(path=CONFIG_FILE):
    """Settings from the file, with defaults for anything missing or invalid."""
    try:
        with open(path, encoding='utf-8') as f:
            user = json.load(f)
    except FileNotFoundError:
        user = None
    except (OSError, ValueError):
        user = {}  # broken file: run with defaults, don't overwrite the user's file
    cfg = _merge(DEFAULTS, user if isinstance(user, dict) else {})
    if user is None:
        save(cfg, path)
    return cfg


def save(cfg, path=CONFIG_FILE):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2)
        os.replace(tmp, path)
    except OSError:
        pass
