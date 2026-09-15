"""Tests for everything that doesn't need a window: hook, bridge, progress, behaviour, settings, pixel art."""
import json
import os
import random
import re
import sys
import tempfile
import time

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'hooks'))
import pet_hook
from pet import behavior, bridge, config, sprites

fails = 0


def check(name, ok, detail=''):
    global fails
    fails += not ok
    print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(detail)) if detail else ''))


# --- hook -----------------------------------------------------------------------------------
now = time.time()
rec = pet_hook.record_for({'hook_event_name': 'PreToolUse', 'tool_name': 'Edit', 'cwd': 'C:\\code\\ac-dash',
                           'tool_input': {'file_path': 'C:\\code\\ac-dash\\timing.py', 'new_string': 'SECRET'}}, now)
check('hook describes the action, never the content', rec['detail'] == 'Editing timing.py'
      and rec['project'] == 'ac-dash' and 'SECRET' not in json.dumps(rec), rec)
check('commands use their description', pet_hook.describe('Bash', {'command': 'rm -rf x', 'description': 'Run tests'})
      == 'Run tests')
check('other tools described', [pet_hook.describe(t, a) for t, a in (
    ('Grep', {'pattern': 'def main'}), ('WebFetch', {'url': 'https://docs.python.org/3/x'}),
    ('mcp__github__create_issue', {}), ('Agent', {'description': 'Find the bug'}))]
      == ['Searching for "def main"', 'Reading docs.python.org', 'Using create issue', 'Agent: Find the bug'])
check('hook ignores unrelated notifications',
      pet_hook.record_for({'hook_event_name': 'Notification', 'notification_type': 'auth_success'}, now) is None)
rec = pet_hook.record_for({'hook_event_name': 'UserPromptSubmit', 'prompt': '\n  Make the pet show progress\nmore details'}, now)
check('request title: first line only', rec['title'] == 'Make the pet show progress', rec)
check('request title can be turned off', 'title' not in pet_hook.record_for(
    {'hook_event_name': 'UserPromptSubmit', 'prompt': 'secret'}, now, titles=False))
rec = pet_hook.record_for({'hook_event_name': 'PreToolUse', 'tool_name': 'TodoWrite', 'tool_input': {'todos': [
    {'content': 'Write tests', 'status': 'completed', 'activeForm': 'Writing tests'},
    {'content': 'Ship it', 'status': 'in_progress'}]}}, now)
check('to-do lists recorded', rec['todos'] == [['Write tests', 'completed'], ['Ship it', 'in_progress']], rec)
rec = pet_hook.record_for({'hook_event_name': 'TaskCreated', 'task_id': '3', 'task_subject': 'Fix the bug'}, now)
check('task created recorded', rec['task'] == {'id': '3', 'subject': 'Fix the bug', 'status': 'pending'}, rec)
d = tempfile.mkdtemp()
pet_hook.write(d, '../../evil name', {'e': 'Stop', 't': now})
pet_hook.write(d, '../../evil name', {'e': 'Stop', 't': now + 1})
check('one safe log file per session, one line per event', os.listdir(d) == ['evilname.jsonl']
      and len(open(os.path.join(d, 'evilname.jsonl')).read().splitlines()) == 2)

# --- bridge ---------------------------------------------------------------------------------
d = tempfile.mkdtemp()
B = bridge.Bridge(d)


def send(session, event, age=0.0, **extra):
    pet_hook.write(d, session, dict({'e': event, 't': time.time() - age, 'project': session}, **extra))


check('no sessions: idle', B.poll().state == 'idle')
send('a', 'PreToolUse', tool='Read', detail='Reading app.py')
m = B.poll()
check('reading a file: working/read', (m.state, m.activity) == ('working', 'read'), m)
send('b', 'PermissionRequest')
m = B.poll()
check('one session waiting beats another working', m.state == 'needs_you' and m.project == 'b', m)
check('waiting triggers one reaction', m.reactions == ['needs_you'], m.reactions)
check('the same event does not react twice', B.poll().reactions == [])
send('b', 'Stop')
m = B.poll()
check('finished: celebrate once, back to the working session', m.reactions == ['done'] and m.state == 'working', m)
send('c', 'Stop', age=60)
check('old events are not replayed', 'done' not in B.poll().reactions)
with open(os.path.join(d, 'a.jsonl'), 'a') as f:
    f.write('{"e": "PreToolUse", "t": %f, "tool": "Ed' % time.time())  # a line still being written
check('a half-written line is not misread', B.poll().state == 'working')
with open(os.path.join(d, 'a.jsonl'), 'a') as f:
    f.write('it", "detail": "Editing x.py"}\n')
B.poll()
check('and is read once complete', B.sessions['a.jsonl'].detail == 'Editing x.py')
check('tool mapping', [bridge.activity_for(t) for t in ('Edit', 'Grep', 'Bash', 'WebSearch', 'mcp__x__y', 'Agent')]
      == ['type', 'read', 'command', 'web', 'web', 'think'])

# progress
d = tempfile.mkdtemp()
B = bridge.Bridge(d)
send('p', 'UserPromptSubmit', age=120, title='Add a progress panel')
for i, detail in enumerate(['Reading app.py', 'Editing app.py', 'Editing app.py', 'Run tests']):
    send('p', 'PreToolUse', age=100 - i, tool='Edit', detail=detail)
send('p', 'TaskCreated', age=90, task={'id': '1', 'subject': 'Write the panel', 'status': 'pending'})
send('p', 'TaskCreated', age=89, task={'id': '2', 'subject': 'Test it', 'status': 'pending'})
send('p', 'PreToolUse', age=80, tool='TaskUpdate', detail='Updating the task list',
     task={'id': '1', 'status': 'in_progress', 'subject': ''})
send('p', 'TaskCompleted', age=70, task={'id': '1', 'subject': 'Write the panel', 'status': 'completed'})
B.poll()
p = B.progress()[0]
check('progress: title, current action, steps, time', p['title'] == 'Add a progress panel'
      and p['detail'] == 'Updating the task list' and p['steps'] == 5 and 115 < time.time() - p['started'] < 125, p)
check('progress: tasks with live status', p['tasks'] == [('Write the panel', 'completed'), ('Test it', 'pending')], p)
check('progress: recent actions, newest first, no repeats', p['recent'][:3] == ['Updating the task list', 'Run tests',
                                                                                'Editing app.py'], p['recent'])
send('p', 'Stop')
B.poll()
p = B.progress()[0]
check('progress: finished request shows as done with its duration', p['state'] == 'done' and p['finished'], p['state'])
send('q', 'PermissionRequest')
B.poll()
check('progress: the session that needs you is listed first', [s['project'] for s in B.progress()][:2] == ['q', 'p'])
send('q', 'SessionEnd')
B.poll()
check('progress: ended sessions leave the panel', 'q' not in [s['project'] for s in B.progress()])

# --- behaviour ------------------------------------------------------------------------------
cfg = config._merge(config.DEFAULTS, {})
IDLE = bridge.Mood('idle', None, '', [])
AREA = (0, 1920, 1140)
SIZE = (96, 64)


def run(pet, seconds, mood=IDLE, t0=0.0, first=()):
    t = t0
    for i in range(int(seconds * 60)):
        pet.update(t, 1 / 60, mood._replace(reactions=list(first)) if i == 0 and first else mood)
        t += 1 / 60
    return t


P = behavior.Pet(cfg, AREA, SIZE, 0.0, random.Random(4))
xs, anims = [], set()
t = 0.0
for _ in range(60 * 120):
    P.update(t, 1 / 60, IDLE)
    xs.append(P.x)
    anims.add(P.anim)
    t += 1 / 60
check('never falls asleep by default: still lively after 2 minutes', 'sleep' not in anims and not P.asleep)
check('walks along the taskbar', max(xs) - min(xs) > 400, (round(min(xs)), round(max(xs))))
check('does cute tricks while wandering', len({'wave', 'dance', 'look', 'happy', 'sit', 'celebrate'} & anims) >= 3, anims)
check('smooth: no jumps between frames', max(abs(a - b) for a, b in zip(xs, xs[1:])) < 2)

zone = behavior.walk_zone(AREA, 40, 'center')
check('walking area: 40% in the middle', zone == (576.0, 1344.0, 1140), zone)
check('walking area: left and right', behavior.walk_zone(AREA, 25, 'left')[:2] == (0, 480.0)
      and behavior.walk_zone(AREA, 25, 'right')[:2] == (1440.0, 1920))
P = behavior.Pet(cfg, zone, SIZE, 0.0, random.Random(8), screen=AREA)
xs = []
t = 0.0
for _ in range(60 * 90):
    P.update(t, 1 / 60, IDLE)
    xs.append(P.x)
    t += 1 / 60
check('stays inside its walking area', min(xs) >= 576 + 48 - 0.01 and max(xs) <= 1344 - 48 + 0.01, (min(xs), max(xs)))
P.grab(t, 100, 1140)
P.release(t)
check('can be dragged outside its area', P.x == 100, P.x)
run(P, 30, t0=t)
check('then walks back into its area by itself', 624 <= P.x <= 1296, round(P.x))

P = behavior.Pet(dict(cfg, sleep_after_seconds=20), AREA, SIZE, 0.0, random.Random(1))
run(P, 25)
check('optional sleep still works when turned on', P.asleep)
run(P, 1, bridge.Mood('working', 'type', 'x', []), t0=25)
check('wakes up and types when Claude edits code', not P.asleep and P.anim == 'type', P.anim)

P = behavior.Pet(cfg, AREA, SIZE, 0.0, random.Random(3))
run(P, 3)
P.hover(3.0, True)
x0 = P.x
t = run(P, 2, t0=3.0)
check('hover: stops, waves hello, stays put', P.x == x0 and P.target is None, P.anim)
P.hover(t, False)
run(P, 20, t0=t)
check('after hover: walks again', P.x != x0)

P = behavior.Pet(cfg, AREA, SIZE, 0.0, random.Random(2))
run(P, 0.5, first=['done'])
check('Claude finished: celebrates with a bubble', P.anim == 'celebrate' and P.bubble and P.bubble[0] == 'Done!')
run(P, 3, t0=0.5)
t = run(P, 20, t0=3.5)
check('after celebrating it keeps walking around', P.target is not None or P.busy_reacting(t) or P.anim in (
    'walk', 'idle', 'look', 'wave', 'dance', 'happy', 'sit', 'celebrate'), P.anim)

P = behavior.Pet(cfg, AREA, SIZE, 0.0, random.Random(3))
wait = bridge.Mood('needs_you', None, 'x', [])
lifts = []
t = 0.0
for i in range(60 * 4):
    P.update(t, 1 / 60, wait._replace(reactions=['needs_you'] if i == 0 else []))
    lifts.append(P.lift)
    t += 1 / 60
check('needs you: alert pose, bubble and repeated hops', P.anim == 'alert' and P.bubble[0] == 'Needs you!'
      and sum(1 for a, b in zip(lifts, lifts[1:]) if a == 0 and b > 0) >= 2)

P = behavior.Pet(cfg, AREA, SIZE, 0.0, random.Random(5))
P.grab(0.0, 500, 800)
P.update(0.02, 0.02, IDLE)
check('dragged: dangling pose in the air', P.anim == 'drag' and P.lift == 340)
P.release(0.1)
run(P, 2, t0=0.1)
check('dropped: falls back onto the taskbar', P.lift == 0 and P.mode == 'ground')

P = behavior.Pet(cfg, AREA, SIZE, 0.0, random.Random(6))
t, shown = 0.0, []
for i in range(60 * 3):
    P.update(t, 1 / 60, bridge.Mood('working', ['read', 'type'][(i // 6) % 2], '', []))
    shown.append(P.anim)
    t += 1 / 60
check('rapid tool switching does not flicker', sum(1 for a, b in zip(shown, shown[1:]) if a != b) <= 4)

P = behavior.Pet(dict(cfg, react_to_claude=False, wander=False, tricks=False), AREA, SIZE, 0.0, random.Random(7))
x0 = P.x
run(P, 10, bridge.Mood('needs_you', None, '', ['done']))
check('settings: no reactions, walking or tricks when turned off', P.anim == 'idle' and P.x == x0, P.anim)

# --- settings -------------------------------------------------------------------------------
c = config._merge(config.DEFAULTS, {'scale': 99, 'walk_speed': 'fast', 'bubbles': 0, 'nonsense': 1,
                                    'walk_width_percent': 3, 'messages': {'done': 'Yay!'}})
check('settings are validated', c['scale'] == 8 and c['walk_speed'] == 1.0 and c['bubbles'] is False
      and 'nonsense' not in c and c['walk_width_percent'] == 10 and c['messages']['done'] == 'Yay!'
      and c['messages']['hello'] == 'Hi!')
check('defaults: lively, full taskbar', config.DEFAULTS['sleep_after_seconds'] == 0 and config.DEFAULTS['tricks']
      and config.DEFAULTS['walk_width_percent'] == 100)
p = os.path.join(tempfile.mkdtemp(), 'config.json')
with open(p, 'w') as f:
    f.write('{broken')
check('a broken settings file is not overwritten',
      config.load(p)['scale'] == config.DEFAULTS['scale'] and open(p).read() == '{broken')

# --- pixel art ------------------------------------------------------------------------------
frames = sprites.build_frames({'body': '#6aa3ff'})
sizes = {(len(f), len(f[0])) for anim in frames.values() for f in anim}
check('every frame is 48x32', sizes == {(32, 48)}, sizes)
idle = sprites.build_frames()['idle'][0]
body = sprites.DEFAULT_COLORS['body']
cols = [x for x in range(sprites.W) if any(idle[y][x] == body for y in range(sprites.H))]
rows = [y for y in range(sprites.H) if any(c == body for c in idle[y])]
check('the square character: 32 px wide with arms, 20 px tall, standing on the ground',
      (cols[0], cols[-1], rows[0], rows[-1]) == (8, 39, 12, 31))
check('two tall eyes', all(idle[y][x] == sprites.DEFAULT_COLORS['eye'] for x in (16, 17, 30, 31) for y in range(16, 20)))
check('four legs', [x for x in range(sprites.W) if idle[31][x] == body] == [14, 15, 18, 19, 28, 29, 32, 33])
colours = {c for anim in frames.values() for f in anim for row in f for c in row if c}
check('all colours valid, none equal to the see-through colour',
      all(re.fullmatch(r'#[0-9a-f]{6}', c) for c in colours) and '#ff00fe' not in colours)
check('colour overrides are applied', '#6aa3ff' in colours and body not in colours)
needed = {'idle', 'walk', 'sit', 'think', 'type', 'read', 'command', 'web', 'alert', 'celebrate', 'wave', 'happy',
          'error', 'sleep', 'drag', 'fall', 'land', 'look', 'dance'}
needed |= {a for a, _, _ in behavior.TRICKS} | {v[0] for v in behavior.REACTION_ANIM.values() if v[0]}
check('every animation the behaviour can pick exists', needed <= set(frames), needed - set(frames))

print('\nALL PASS' if not fails else f'\n{fails} FAILED')
sys.exit(1 if fails else 0)
