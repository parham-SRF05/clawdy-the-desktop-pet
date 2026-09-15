"""Install Claude Pet into Claude Code.

    python install.py              add the pet's hooks (safe to run again: it updates them)
    python install.py --uninstall  remove the pet's hooks

Your other hooks are left exactly as they are, and settings.json is backed up first.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, 'hooks', 'pet_hook.py')
SETTINGS = os.path.join(os.path.expanduser('~'), '.claude', 'settings.json')
MARK = 'pet_hook.py'

# event -> matcher ("" = every tool / notification type; None = event has no matcher)
EVENTS = [('SessionStart', None), ('SessionEnd', None), ('UserPromptSubmit', None), ('PreToolUse', ''),
          ('PostToolUse', ''), ('PostToolUseFailure', ''), ('PermissionRequest', ''), ('Notification', ''),
          ('Stop', None), ('StopFailure', None), ('SubagentStart', None), ('SubagentStop', None),
          ('PreCompact', None), ('TaskCreated', None), ('TaskCompleted', None)]


def python_exe():
    exe = sys.executable
    folder, name = os.path.split(exe)
    if name.lower() == 'pythonw.exe':
        exe = os.path.join(folder, 'python.exe')
    return exe


def hook_entry(python, hook=HOOK):
    # exec form (args): no shell involved, and async so Claude Code never waits for the pet
    return {'type': 'command', 'command': python.replace('\\', '/'),
            'args': ['-S', '-E', hook.replace('\\', '/')], 'async': True, 'timeout': 10}


def is_pet_hook(hook):
    return MARK in ' '.join([str(hook.get('command', ''))] + [str(a) for a in hook.get('args') or []])


def remove_hooks(settings):
    hooks = settings.get('hooks')
    if not isinstance(hooks, dict):
        return settings
    for event in list(hooks):
        groups = hooks[event] if isinstance(hooks[event], list) else []
        kept = []
        for group in groups:
            entries = group.get('hooks', []) if isinstance(group, dict) else []
            remaining = [h for h in entries if not is_pet_hook(h)]
            if remaining or len(remaining) == len(entries):
                kept.append(dict(group, hooks=remaining) if isinstance(group, dict) else group)
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]
    if not hooks:
        del settings['hooks']
    return settings


def add_hooks(settings, python):
    remove_hooks(settings)  # updating: never add the pet twice
    hooks = settings.setdefault('hooks', {})
    for event, matcher in EVENTS:
        group = {'hooks': [hook_entry(python)]}
        if matcher is not None:
            group = {'matcher': matcher, 'hooks': group['hooks']}
        hooks.setdefault(event, []).append(group)
    return settings


def main():
    uninstall = '--uninstall' in sys.argv
    settings = {}
    if os.path.exists(SETTINGS):
        try:
            with open(SETTINGS, encoding='utf-8') as f:
                settings = json.load(f)
        except ValueError as e:
            print('Your Claude Code settings file has an error, so nothing was changed:\n  %s\n  %s' % (SETTINGS, e))
            return 1
        backup = '%s.bak-claude-pet-%s' % (SETTINGS, time.strftime('%Y%m%d-%H%M%S'))
        with open(SETTINGS, 'rb') as src, open(backup, 'wb') as dst:
            dst.write(src.read())
        print('Backed up your settings to', backup)
    settings = remove_hooks(settings) if uninstall else add_hooks(settings, python_exe())
    os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
    tmp = SETTINGS + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)
    os.replace(tmp, SETTINGS)
    if uninstall:
        print('Claude Pet hooks removed. Your other hooks were not touched.')
        return 0
    sys.path.insert(0, HERE)
    from pet import config
    config.load()  # creates the settings file with defaults
    print('Claude Pet is installed.')
    print('  Start the pet: double-click claude_pet.pyw (it also starts by itself with Claude Code).')
    print('  Settings:', config.CONFIG_FILE)
    return 0


if __name__ == '__main__':
    sys.exit(main())
