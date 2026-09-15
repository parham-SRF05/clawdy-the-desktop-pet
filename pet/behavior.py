"""What the pet does: walking, tricks, jumping, being dragged, sleeping and reacting to Claude Code.

No window code here: the app feeds in time, the Claude mood and mouse actions, and reads back
the position, animation and speech bubble.
"""
import math
import random

ACTIVITY_DWELL = 0.8      # seconds an activity animation stays before switching (no flicker)
LAND_TIME = 0.35
TRICK_CHANCE = 0.4        # after a walk, chance of doing a trick instead of just standing

REACTION_ANIM = {         # reaction -> (animation, seconds, bubble message key, jumps)
    'done': ('celebrate', 2.4, 'done', 2),
    'error': ('error', 3.0, 'error', 0),
    'oops': ('error', 1.2, None, 0),
    'hello': ('wave', 2.0, 'hello', 1),
    'bye': ('wave', 2.0, 'bye', 0),
    'compact': (None, 2.5, 'compact', 0),
    'poke': ('happy', 1.4, 'poke', 1),
    'hover': ('wave', 1.2, None, 0),
}
TRICKS = [('wave', 1.6, 0), ('dance', 2.4, 0), ('look', 2.0, 0), ('happy', 1.3, 1), ('sit', 3.0, 0),
          ('celebrate', 1.2, 1)]


def walk_zone(screen, percent=100, align='center'):
    """The part of the floor the pet walks on: `percent` of it, at the left, centre or right."""
    left, right, floor = screen
    width = (right - left) * min(max(percent, 10), 100) / 100.0
    if align == 'left':
        start = left
    elif align == 'right':
        start = right - width
    else:
        start = left + ((right - left) - width) / 2
    return start, start + width, floor


class Pet:
    def __init__(self, cfg, area, sprite_size, now=0.0, rng=None, screen=None):
        self.cfg = cfg
        self.rng = rng or random.Random()
        self.w, self.h = sprite_size
        unit = sprite_size[1] / 96.0                 # 1.0 at a 96 px tall sprite
        self.walk_speed = 54 * unit * cfg['walk_speed']   # px per second
        self.gravity = 2600 * unit
        self.jump_speed = math.sqrt(2 * self.gravity * 0.33 * self.h)
        self.set_area(area, screen)
        self.x = self.rng.uniform(self.left, self.right)
        self.lift = 0.0          # height above the floor, px
        self.vy = 0.0
        self.facing = 1
        self.mode = 'ground'     # ground | drag | fall
        self.target = None
        self.pause_until = now + 1.0
        self.resting_anim = 'idle'
        self.reaction = None     # (animation, until)
        self.jumps = []          # times to jump at
        self.bubble = None       # (text, until)
        self.asleep = False
        self.hovered = False
        self.last_event = now
        self.activity, self.activity_since = None, now
        self.anim, self.anim_time = 'idle', 0.0
        self.mood_state = 'idle'
        self.next_hop = now

    # --- world ---------------------------------------------------------------------------

    def set_area(self, area, screen=None):
        """area: where the pet walks; screen: where it can be dragged (defaults to the area)."""
        left, right, floor = area
        margin = self.w / 2
        self.left, self.right, self.floor = left + margin, max(left + margin, right - margin), floor
        s_left, s_right = (screen or area)[:2]
        self.screen_left, self.screen_right = s_left + margin, max(s_left + margin, s_right - margin)

    def window_origin(self, canvas_w, canvas_h):
        """Top-left of a canvas whose bottom centre is where the pet's feet are."""
        return round(self.x - canvas_w / 2), round(self.floor - self.lift - canvas_h)

    # --- input ---------------------------------------------------------------------------

    def say(self, now, key, seconds=2.5):
        text = self.cfg['messages'].get(key) if key else None
        if text and self.cfg['bubbles']:
            self.bubble = (text, now + seconds)

    def react(self, now, name):
        self._wake(now)
        if name == 'needs_you':
            self.jumps.append(now)
            return
        anim, seconds, message, jumps = REACTION_ANIM[name]
        if anim:
            self.reaction = (anim, now + seconds)
        self.say(now, message, seconds)
        self.jumps.extend(now + i * 0.9 for i in range(jumps))

    def poke(self, now):
        self.react(now, 'poke')

    def hover(self, now, on):
        if on and not self.hovered and self.mode == 'ground' and self.mood_state == 'idle' and not self.busy_reacting(now):
            self.react(now, 'hover')
        self.hovered = on
        if on:
            self._wake(now)
            self.target = None

    def grab(self, now, x, bottom):
        self._wake(now)
        self.mode = 'drag'
        self.target = None
        self.vy = 0.0
        self.drag_to(x, bottom)

    def drag_to(self, x, bottom):
        self.x = min(max(x, self.screen_left), self.screen_right)
        self.lift = max(0.0, self.floor - bottom)

    def release(self, now):
        self.mode = 'fall' if self.lift > 1 else 'ground'
        self.vy = 0.0
        self.pause_until = now + 1.0

    def toggle_sleep(self, now):
        if self.asleep:
            self._wake(now)
        else:
            self.asleep = True

    def busy_reacting(self, now):
        return bool(self.reaction and now < self.reaction[1])

    def _wake(self, now):
        self.asleep = False
        self.last_event = now

    # --- every frame -----------------------------------------------------------------------

    def update(self, now, dt, mood):
        dt = min(dt, 0.1)  # after a pause or a hidden period, don't teleport
        if self.cfg['react_to_claude'] and mood is not None:
            for name in mood.reactions:
                self.react(now, name)
            if mood.state != 'idle':
                self._wake(now)  # Claude is busy or needs you: no sleeping through that
            if mood.state == 'needs_you' and self.mood_state != 'needs_you':
                self.say(now, 'needs_you', 3.0)
            self.mood_state = mood.state
            activity = mood.activity if mood.state == 'working' else None
        else:
            self.mood_state, activity = 'idle', None

        if activity != self.activity and (self.activity is None or now - self.activity_since >= ACTIVITY_DWELL):
            self.activity, self.activity_since = activity, now

        sleep_after = self.cfg['sleep_after_seconds']
        if (sleep_after > 0 and self.mood_state == 'idle' and not self.asleep and not self.hovered
                and self.mode == 'ground' and now - self.last_event > sleep_after):
            self.asleep = True

        self._physics(now, dt)
        if self.mode == 'ground' and self.lift == 0:
            self._walk(now, dt)
        self._pick_animation(now, dt)
        if self.bubble and now > self.bubble[1]:
            self.bubble = None
        if self.mood_state == 'needs_you' and self.bubble is None and self.cfg['bubbles']:
            self.bubble = (self.cfg['messages']['needs_you'], now + 0.5)

    def _physics(self, now, dt):
        if self.mode == 'drag':
            return
        if self.mood_state == 'needs_you' and now >= self.next_hop and self.lift == 0:
            self.jumps.append(now)
            self.next_hop = now + 1.6
        if self.jumps and now >= self.jumps[0] and self.lift == 0 and self.mode == 'ground':
            self.jumps.pop(0)
            self.vy = self.jump_speed
        if self.lift > 0 or self.vy > 0:
            self.lift += self.vy * dt
            self.vy -= self.gravity * dt
            if self.lift <= 0:
                hard = self.mode == 'fall' or self.vy < -self.jump_speed * 1.2
                self.lift, self.vy = 0.0, 0.0
                self.mode = 'ground'
                if hard:
                    self.reaction = ('land', now + LAND_TIME)
        elif self.mode == 'fall':
            self.mode = 'ground'

    def _walk(self, now, dt):
        if self.hovered:
            self.target = None
            return
        outside = self.x < self.left - 0.5 or self.x > self.right + 0.5
        busy = (self.mood_state != 'idle' or self.asleep or self.busy_reacting(now)
                or not (self.cfg['wander'] or outside))
        if busy:
            self.target = None
            return
        if outside:
            self.target = min(max(self.x, self.left), self.right)  # dropped outside its area: walk back
        if self.target is None:
            if now < self.pause_until:
                return
            if self.cfg['tricks'] and self.rng.random() < TRICK_CHANCE:
                anim, seconds, jumps = self.rng.choice(TRICKS)
                self.reaction = (anim, now + seconds)
                self.jumps.extend(now + 0.2 + i * 0.6 for i in range(jumps))
                self.pause_until = now + seconds + self.rng.uniform(0.5, 2.0)
                return
            if self.right - self.left < 2:
                self.pause_until = now + 3.0
                return
            target = self.x
            for _ in range(10):
                target = self.rng.uniform(self.left, self.right)
                if abs(target - self.x) > min(self.w, (self.right - self.left) / 3):
                    break
            self.target = target
        step = self.walk_speed * dt
        distance = self.target - self.x
        if abs(distance) > 0.01:
            self.facing = 1 if distance > 0 else -1
        if abs(distance) <= step:
            self.x, self.target = self.target, None
            self.pause_until = now + self.rng.uniform(1.0, 4.0)
            self.resting_anim = 'look' if self.rng.random() < 0.3 else 'idle'
        else:
            self.x += step * self.facing

    def _pick_animation(self, now, dt):
        if self.mode == 'drag':
            anim = 'drag'
        elif self.mode == 'fall':
            anim = 'fall'
        elif self.busy_reacting(now):
            anim = self.reaction[0]
        elif self.mood_state == 'needs_you':
            anim = 'alert'
        elif self.activity:
            anim = self.activity
        elif self.asleep:
            anim = 'sleep'
        elif self.target is not None:
            anim = 'walk'
        else:
            anim = self.resting_anim
        if anim != self.anim:
            self.anim, self.anim_time = anim, 0.0
        else:
            self.anim_time += dt

    def frame(self, fps, count):
        index = int(self.anim_time * fps)
        return min(index, count - 1) if self.anim == 'land' else index % count
