"""Installer: adds the pet's hooks without touching other hooks, never twice, and removes them cleanly."""
import copy
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
import install

fails = 0


def check(name, ok, detail=''):
    global fails
    fails += not ok
    print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(detail)) if detail else ''))


OTHER = {'type': 'command', 'command': '"C:\\Program Files\\Git\\bin\\bash.exe" "C:/Users/x/.claude/hooks/telegram-notify.sh"'}
original = {
    'model': 'opus',
    'hooks': {
        'Notification': [{'matcher': '', 'hooks': [dict(OTHER)]}],
        'Stop': [{'hooks': [dict(OTHER)]}],
        'UserPromptSubmit': [{'hooks': [dict(OTHER)]}],
    },
}
py = r'C:\Python\python.exe'

s = install.add_hooks(copy.deepcopy(original), py)
pet_count = {e: sum(install.is_pet_hook(h) for g in s['hooks'][e] for h in g['hooks']) for e, _ in install.EVENTS}
check('the pet hook is added once for every event', set(pet_count.values()) == {1}, pet_count)
check('other hooks are kept', all(any(h == OTHER for g in s['hooks'][e] for h in g['hooks'])
                                   for e in ('Notification', 'Stop', 'UserPromptSubmit')))
check('other settings are kept', s['model'] == 'opus')
entry = s['hooks']['PreToolUse'][0]
check('tool events match every tool', entry['matcher'] == '')
h = entry['hooks'][0]
check('runs in the background, without a shell', h['async'] is True and h['args'][:2] == ['-S', '-E']
      and h['command'] == 'C:/Python/python.exe' and h['args'][2].endswith('hooks/pet_hook.py'), h)

s2 = install.add_hooks(copy.deepcopy(s), py)
check('installing again does not add it twice', s2 == s)

removed = install.remove_hooks(copy.deepcopy(s))
check('uninstall restores the original settings exactly', removed == original, json.dumps(removed)[:200])
check('uninstall when nothing was installed changes nothing', install.remove_hooks(copy.deepcopy(original)) == original)
check('works on empty settings', install.remove_hooks(install.add_hooks({}, py)) == {})

print('\nALL PASS' if not fails else f'\n{fails} FAILED')
sys.exit(1 if fails else 0)
