"""Talking and copying what you do: app and website lines, away/back, battery, night, pokes, mouse watching."""
import os
import random
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
from pet import behavior, bridge, chatter as C, config, lines as L, winapi

fails = 0


def check(name, ok, detail=''):
    global fails
    fails += not ok
    print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(detail)) if detail else ''))


def snap(exe=None, title='', idle=0.0, battery=None, charging=None, hour=14):
    return C.Snapshot(exe, title, idle, battery, charging, hour)


cfg = config._merge(config.DEFAULTS, {})

# --- chatter ----------------------------------------------------------------------------------
ch = C.Chatter(cfg, random.Random(1))
t = 1000.0
out = ch.observe(t, snap())
check('says hello when it starts', len(out) == 1 and out[0].text in L.LINES['hello_pet'], out)
out = ch.observe(t + 10, snap('chrome.exe', 'New Tab - Google Chrome'))
check('opening Chrome: a Chrome joke while browsing along', len(out) == 1 and out[0].text in L.LINES['chrome']
      and out[0].anim == 'web', out)
check('same app a moment later: quiet', ch.observe(t + 11, snap('chrome.exe', 'New Tab - Google Chrome')) == [])
out = ch.observe(t + 20, snap('code.exe', 'app.py - claude-pet - Visual Studio Code'))
check('opening VS Code: grabs its laptop', len(out) == 1 and out[0].text in L.LINES['vscode'] and out[0].anim == 'type', out)
out = ch.observe(t + 30, snap('chrome.exe', 'Funny cats - YouTube - Google Chrome'))
check('a website it knows gets its own line', len(out) == 1 and out[0].text in L.LINES['youtube'], out)
check('switching back and forth is not spammy', sum(len(ch.observe(t + 40 + i, snap(['chrome.exe', 'code.exe'][i % 2])))
                                                    for i in range(20)) <= 4)
out = ch.observe(t + 200, snap('chrome.exe', idle=400))
check('away for 5 minutes: "anyone there?"', len(out) == 1 and out[0].text in L.LINES['idle'], out)
out = ch.observe(t + 210, snap('chrome.exe', idle=0.5))
check('back: welcome back', len(out) == 1 and out[0].text in L.LINES['back'], out)
out = ch.observe(t + 300, snap(battery=15, charging=False))
check('low battery warning', len(out) == 1 and out[0].text in L.LINES['battery_low'], out)
check('warned only once', ch.observe(t + 400, snap(battery=14, charging=False)) == [])
out = ch.observe(t + 500, snap(battery=14, charging=True))
check('plugged in: happy about it', len(out) == 1 and out[0].text in L.LINES['charging'], out)
out = ch.observe(t + 600, snap(hour=3))
check('3am: tells you to go to bed', len(out) == 1 and out[0].text in L.LINES['night'], out)
check('but not every minute', ch.observe(t + 700, snap(hour=3)) == [])

seq = [ch.line('poke') for _ in range(30)]
check('never the same line twice in a row', all(a != b for a, b in zip(seq, seq[1:])))
custom = C.Chatter(dict(cfg, custom_lines={'chrome': ['My own Chrome joke']}), random.Random(2))
check('your own lines are used', 'My own Chrome joke' in custom.lines['chrome'])
check('talking can be turned off', C.Chatter(dict(cfg, chatter=False)).observe(t, snap('chrome.exe')) == [])
check('copying what you do', [ch.busy_with(s) for s in (snap('code.exe', idle=1), snap('chrome.exe', 'x - YouTube', idle=1),
                                                         snap('code.exe', idle=30), snap('mystery.exe', idle=0))]
      == ['type', 'sit', None, None])
check('website lines only in browsers', C.site_key(C.app_key('notepad.exe'), 'YouTube notes') is None)
check('every line points at a real animation', set(L.ANIM.values()) <= set(__import__('pet.sprites', fromlist=['x']).ANIMATIONS))

# --- behaviour ------------------------------------------------------------------------------
IDLE = bridge.Mood('idle', None, '', [])
AREA, SIZE = (0, 1920, 1140), (96, 64)


def run(pet, seconds, t0=0.0, mood=IDLE):
    t = t0
    for _ in range(int(seconds * 60)):
        pet.update(t, 1 / 60, mood)
        t += 1 / 60
    return t


P = behavior.Pet(cfg, AREA, SIZE, 0.0, random.Random(1))
run(P, 1)
check('chat: bubble and matching animation', P.chat(1.0, 'Chrome! Say goodbye to your RAM.', 'web')
      and P.bubble[0].startswith('Chrome') and run(P, 0.5, 1.0) and P.anim == 'web', P.anim)
P2 = behavior.Pet(cfg, AREA, SIZE, 0.0, random.Random(1))
run(P2, 0.5, mood=bridge.Mood('needs_you', None, '', []))
check('never talks over Claude needing you', not P2.chat(0.6, 'hi', 'web') and P2.bubble[0] == 'Needs you!')
P3 = behavior.Pet(cfg, AREA, SIZE, 0.0, random.Random(1))
run(P3, 0.5, mood=bridge.Mood('working', 'type', '', []))
P3.chat(0.6, 'VS Code!', 'dance')
run(P3, 0.3, 0.6, bridge.Mood('working', 'type', '', []))
check('while Claude works: talks, but keeps working', P3.anim == 'type' and P3.bubble[0] == 'VS Code!', P3.anim)

P = behavior.Pet(cfg, AREA, SIZE, 0.0, random.Random(1))
P.lines = ch.line
for i in range(3):
    P.poke(1.0 + i * 0.3)
run(P, 0.2, 1.7)
check('3 quick pokes: dizzy', P.anim == 'dizzy' and P.bubble[0] in L.LINES['dizzy'], (P.anim, P.bubble))
P.react(5.0, 'done')
check('"done" says a random celebration line', P.bubble[0] in L.LINES['done'])
P.cfg = dict(cfg, messages=dict(cfg['messages'], done='Yay!'))
P.react(9.0, 'done')
check('a message you customised always wins', P.bubble[0] == 'Yay!')

P = behavior.Pet(dict(cfg, wander=False, tricks=False), AREA, SIZE, 0.0, random.Random(1))
P.cursor = (P.x - 150, 1100)
run(P, 0.5)
check('watches the mouse pointer when it comes close', P.anim == 'watch' and P.facing == -1, (P.anim, P.facing))
P.cursor = (P.x + 900, 400)
run(P, 0.5, 0.5)
check('stops watching when it goes away', P.anim == 'idle')

P = behavior.Pet(cfg, AREA, SIZE, 0.0, random.Random(3))
P.hint = 'type'
seen = []
t = 0.0
for _ in range(60 * 240):
    P.update(t, 1 / 60, IDLE)
    seen.append(P.anim)
    t += 1 / 60
tricks = {a for a in seen}
check('copies what you do: codes along far more often', seen.count('type') > 3 * seen.count('dance'),
      (seen.count('type'), seen.count('dance')))
P = behavior.Pet(cfg, AREA, SIZE, 0.0, random.Random(9))
seen = set()
t = 0.0
for _ in range(60 * 400):
    P.update(t, 1 / 60, IDLE)
    seen.add(P.anim)
    t += 1 / 60
check('with Claude closed it still shows its work animations', {'type', 'read', 'command', 'web', 'think'} <= seen, seen)

# --- settings and Windows -------------------------------------------------------------------
c = config._merge(config.DEFAULTS, {'custom_lines': {'chrome': ['a', 'b'], 'bad': [1, 2]}, 'chatter_gap_seconds': 1})
check('custom lines accepted, invalid ones ignored', c['custom_lines'] == {'chrome': ['a', 'b']}
      and c['chatter_gap_seconds'] == 5, c['custom_lines'])
exe, title = winapi.foreground_app()
idle, (battery, charging), pos = winapi.idle_seconds(), winapi.battery(), winapi.cursor_pos()
check('Windows: reads the app in front, idle time, battery and mouse', (exe is None or exe.endswith('.exe'))
      and idle >= 0 and (battery is None or 0 <= battery <= 100) and pos is not None, (exe, round(idle, 1), battery, pos))

print('\nALL PASS' if not fails else f'\n{fails} FAILED')
sys.exit(1 if fails else 0)
