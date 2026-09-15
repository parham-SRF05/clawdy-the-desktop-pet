"""Built-in pixel art: the square Claude Code character, drawn in code.

The shape follows the character on Claude Code's welcome screen, drawn there with block characters:

     ▐▛███▜▌        body 12 blocks wide with two tall eye slits,
    ▝▜█████▛▘       stubby arms on each side,
      ▘▘ ▝▝         and four little legs.

Here one block is 2x2 art pixels (terminal cells are twice as tall as wide, so rows are doubled),
which keeps the exact silhouette while leaving room for smooth, half-block animation.
Every frame is drawn on a 48x32 grid of palette keys: colours can be changed from the config, and
whole animations can be replaced by a skin's sprite sheet.
"""

W, H = 48, 32
GROUND = 31                      # bottom row: the legs stand here
BODY_L, BODY_R = 12, 35          # body: 24 px wide
BODY_TOP, BODY_BOTTOM = 12, 27   # 16 px tall
LEGS = (14, 18, 28, 32)          # each leg is 2 px wide, 4 px tall
EYES = (16, 30)                  # each eye is 2 px wide, 4 px tall

DEFAULT_COLORS = {
    'body': '#d77757',           # Claude Code orange
    'eye': '#231815',
    'shine': '#ffffff',
    'outline': '',               # e.g. "#3b2219" for a dark outline (off: like the original)
    'prop': '#454b57',
    'prop_light': '#9fd8ff',
    'yellow': '#ffe066',
    'red': '#ff5a5a',
    'snooze': '#bcd4ff',
    'bubble': '#ffffff',
}

KEYS = {'b': 'body', 'e': 'eye', 'w': 'shine', 'o': 'outline', 'k': 'prop', 'g': 'prop_light',
        'y': 'yellow', 'r': 'red', 'z': 'snooze', 'u': 'bubble'}
NO_OUTLINE = set('yzru')  # floating effects don't get an outline


class Grid:
    def __init__(self):
        self.px = [[None] * W for _ in range(H)]

    def put(self, x, y, key):
        if 0 <= x < W and 0 <= y < H:
            self.px[y][x] = key

    def rect(self, x0, y0, x1, y1, key):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.put(x, y, key)

    def pattern(self, x, y, rows, key):
        for dy, row in enumerate(rows):
            for dx, ch in enumerate(row):
                if ch != '.':
                    self.put(x + dx, y + dy, key if ch == '#' else ch)

    def outlined(self):
        out = [row[:] for row in self.px]
        for y in range(H):
            for x in range(W):
                if self.px[y][x] is None and any(
                        0 <= nx < W and 0 <= ny < H and self.px[ny][nx] not in (None,) and self.px[ny][nx] not in NO_OUTLINE
                        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))):
                    out[y][x] = 'o'
        self.px = out
        return self


# --- the character ----------------------------------------------------------------------------

def draw_legs(g, phase=None, tucked=False):
    """Walking lifts legs 1+3, then 2+4, one pixel: a little crab-like shuffle."""
    for i, x in enumerate(LEGS):
        lift = 0
        if phase is not None and phase % 2 == 0:
            lift = 1 if (i % 2 == (phase // 2) % 2) else 0
        g.rect(x, GROUND - 3 - lift, x + 1, GROUND - lift, 'b')


def draw_body(g, bob=0, squash=0):
    top = BODY_TOP + bob + 2 * squash
    g.rect(BODY_L - squash, top, BODY_R + squash, BODY_BOTTOM + bob, 'b')
    return top


def draw_eyes(g, top, kind='open', look=0):
    y = top + 4
    for x in (EYES[0] + look, EYES[1] + look):
        if kind == 'open':
            g.rect(x, y, x + 1, y + 3, 'e')
        elif kind == 'closed':
            g.rect(x - 1, y + 3, x + 2, y + 3, 'e')
        elif kind == 'up':
            g.rect(x, y - 1, x + 1, y + 1, 'e')
        elif kind == 'focus':
            g.rect(x, y + 2, x + 1, y + 3, 'e')
        elif kind == 'happy':
            g.pattern(x - 1, y + 1, ['.##.', '#..#'], 'e')
        elif kind == 'wide':
            g.rect(x, y - 1, x + 1, y + 3, 'e')
            g.put(x, y - 1, 'w')
        elif kind == 'sad':
            g.pattern(x - 1, y + 2, ['#...', '.###'] if x < 24 else ['...#', '###.'], 'e')
        elif kind == 'dizzy':
            g.pattern(x - 1, y, ['#..#', '.##.', '.##.', '#..#'], 'e')


def draw_arms(g, top, pose='down', phase=0, squash=0):
    y = top + 8
    lx, rx = 8 - squash, 36 + squash

    def side(x, dy):
        g.rect(x, y + dy, x + 3, y + 3 + dy, 'b')

    def raised(x, outer):
        g.rect(x, top + 2, x + 3, top + 5, 'b')      # shoulder
        g.rect(outer, top - 2, outer + 1, top + 1, 'b')  # arm pointing up

    p = phase % 2
    if pose == 'up':
        raised(lx, lx)
        raised(rx, rx + 2)
    elif pose == 'cheer':
        (raised(lx, lx), side(rx, 0)) if p else (side(lx, 0), raised(rx, rx + 2))
    elif pose == 'wave':
        side(lx, 0)
        raised(rx, rx + 2) if p else side(rx, -3)
    elif pose == 'swing':
        side(lx, p)
        side(rx, 1 - p)
    elif pose == 'type':
        side(lx, 2 * p)
        side(rx, 2 - 2 * p)
    elif pose == 'hold':
        side(lx, 0)
        side(rx, -3)
    elif pose == 'tap':
        side(lx, 0)
        side(rx, -3 + p)
    elif pose == 'low':
        side(lx, 2)
        side(rx, 2)
    else:
        side(lx, 0)
        side(rx, 0)


# --- props and effects ------------------------------------------------------------------------

def prop_laptop(g, phase):
    g.rect(15, 21, 32, 28, 'k')                              # lid, seen from behind
    g.rect(23, 23, 24, 24, 'g' if phase % 2 else 'k')        # glowing logo
    g.rect(11, 29, 36, 29, 'k')                              # base


def prop_terminal(g, phase):
    g.rect(40, 13, 47, 22, 'k')
    g.rect(41, 14, 46, 20, 'e')
    g.pattern(41, 15, ['#..', '.#.', '#..'], 'g')           # >
    if phase % 2 == 0:
        g.rect(44, 19, 45, 19, 'g')                          # blinking cursor
    g.rect(43, 23, 44, 25, 'k')


def prop_magnifier(g, phase):
    x = 40 + (0, 1, 2, 1)[phase % 4]
    g.pattern(x, 9, ['.###.', '#ggg#', '#gwg#', '#ggg#', '.###.'], 'k')
    g.rect(x, 14, x + 1, 15, 'k')


def prop_globe(g, phase):
    g.pattern(41, 11, ['.####.', '#gggg#', '#gggg#', '#gggg#', '#gggg#', '.####.'], 'k')
    m = 42 + phase % 4
    g.rect(m, 12, m, 15, 'k')
    g.rect(42, 13, 45, 13, 'k')
    g.rect(43, 17, 44, 19, 'k')


def fx_thought(g, phase):
    for i, (x, y, size) in enumerate(((35, 9, 1), (38, 6, 2), (41, 2, 3))):
        if i <= phase % 4:
            g.rect(x, y, x + size - 1, y + size - 1, 'u')


def fx_zzz(g, phase):
    for i, (x, y) in enumerate(((33, 7), (37, 3), (41, 0))):
        if i <= phase % 3:
            g.pattern(x, y, ['###', '.#.', '###'], 'z')


def fx_alert(g, phase):
    y = 1 + phase % 2
    g.rect(23, y, 24, y + 5, 'r')
    g.rect(23, y + 7, 24, y + 8, 'r')


def fx_sparkles(g, phase):
    for x, y in (((5, 6), (42, 3)), ((3, 13), (44, 10)), ((8, 2), (39, 7)))[phase % 3]:
        g.pattern(x - 1, y - 1, ['.#.', '###', '.#.'], 'y')


def fx_heart(g, phase):
    g.pattern(34, 3 - phase % 2, ['##.##', '#####', '.###.', '..#..'], 'r')


def fx_sweat(g, phase):
    g.pattern(37, 8 + phase % 2, ['.#.', '###', '.#.'], 'z')


PROPS = {'laptop': prop_laptop, 'terminal': prop_terminal, 'magnifier': prop_magnifier, 'globe': prop_globe}
FX = {'thought': fx_thought, 'zzz': fx_zzz, 'alert': fx_alert, 'sparkles': fx_sparkles,
      'heart': fx_heart, 'sweat': fx_sweat}


def draw(bob=0, squash=0, eyes='open', look=0, arms='down', arm_phase=0, legs=None,
         prop=None, fx=None, phase=0, outline=False):
    g = Grid()
    draw_legs(g, legs)
    top = draw_body(g, bob, squash)
    draw_arms(g, top, arms, arm_phase, squash)
    draw_eyes(g, top, eyes, look)
    if prop:
        PROPS[prop](g, phase)
    if outline:
        g.outlined()
    if fx:
        FX[fx](g, phase)
    return g.px


# --- animations: name -> (frames per second, [frame parameters]) -----------------------------

ANIMATIONS = {
    'idle': (4, [dict(), dict(bob=1), dict(), dict(bob=1, eyes='closed')]),
    'walk': (10, [dict(legs=i, bob=i % 2, arms='swing', arm_phase=i // 2, look=1) for i in range(4)]),
    'sit': (2, [dict(bob=3, eyes='happy'), dict(bob=2, eyes='happy')]),
    'think': (4, [dict(eyes='up', fx='thought', phase=i, bob=i % 2) for i in range(4)]),
    'type': (8, [dict(bob=2, eyes='focus', arms='type', arm_phase=i, prop='laptop', phase=i // 2) for i in range(4)]),
    'read': (5, [dict(eyes='focus', look=1, arms='hold', prop='magnifier', phase=i) for i in range(4)]),
    'command': (6, [dict(eyes='focus', look=1, arms='tap', arm_phase=i, prop='terminal', phase=i,
                         bob=i % 2) for i in range(4)]),
    'web': (6, [dict(look=1, arms='hold', prop='globe', phase=i) for i in range(4)]),
    'alert': (6, [dict(eyes='wide', arms='up', fx='alert', phase=i, squash=i % 2) for i in range(4)]),
    'celebrate': (10, [dict(eyes='happy', arms='cheer', arm_phase=i, fx='sparkles', phase=i,
                            bob=i % 2) for i in range(6)]),
    'wave': (6, [dict(eyes='happy', arms='wave', arm_phase=i) for i in range(4)]),
    'look': (3, [dict(look=-2), dict(look=-2), dict(), dict(look=2), dict(look=2), dict(eyes='closed')]),
    'watch': (3, [dict(look=2), dict(look=2), dict(look=2, bob=1), dict(look=2, eyes='closed')]),
    'dizzy': (6, [dict(eyes='dizzy', arms='low', fx='sweat', phase=i, bob=i % 2) for i in range(4)]),
    'dance': (8, [dict(eyes='happy', arms='cheer', arm_phase=i, legs=2 * i, bob=i % 2) for i in range(4)]),
    'happy': (6, [dict(eyes='happy', fx='heart', phase=i, bob=i % 2) for i in range(4)]),
    'error': (4, [dict(eyes='sad', arms='low', fx='sweat', phase=i) for i in range(4)]),
    'sleep': (2, [dict(bob=3, eyes='closed', fx='zzz', phase=i) for i in range(3)]),
    'drag': (6, [dict(eyes='wide', arms='up', legs=0), dict(eyes='wide', arms='up', legs=2)]),
    'fall': (1, [dict(eyes='wide', arms='up')]),
    'land': (8, [dict(squash=1, eyes='closed'), dict(squash=1, eyes='happy'), dict()]),
}


def build_frames(colors=None):
    """{animation: [rows of '#rrggbb' / None]}, using the default colours plus any overrides."""
    palette = dict(DEFAULT_COLORS)
    palette.update({k: v for k, v in (colors or {}).items() if k in DEFAULT_COLORS})
    outline = bool(palette.get('outline'))
    frames = {}
    for name, (_, specs) in ANIMATIONS.items():
        frames[name] = [[[palette[KEYS[k]] if k else None for k in row]
                         for row in draw(outline=outline, **spec)] for spec in specs]
    return frames


def fps(name):
    return ANIMATIONS[name][0]
