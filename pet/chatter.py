"""Decides when Clawdy says something about what you're doing.

It watches which app is in front (and a browser's page title), whether you're away, the battery
and the time of day, and picks a line now and then: never the same line twice in a row, never
too often. Nothing it sees is saved.
"""
import collections
import random
import time

from . import lines as L

Snapshot = collections.namedtuple('Snapshot', 'exe title idle battery charging hour')
Say = collections.namedtuple('Say', 'text anim')

NEW_APP_AFTER = 20 * 60     # an app not used for this long counts as "just opened"
SITE_AGAIN_AFTER = 20 * 60
AWAY_AFTER = 5 * 60         # seconds without mouse or keyboard
NIGHT_AGAIN_AFTER = 90 * 60
QUICK_GAP = 8               # minimum gap even for important lines


def app_key(exe):
    return L.APPS.get((exe or '').lower())


def site_key(app, title):
    if app not in L.BROWSERS or not title:
        return None
    padded = ' %s ' % title.lower().replace('-', ' ').replace('|', ' ')
    for keyword, key in L.SITES:
        if keyword in padded:
            return key
    return None


class Chatter:
    def __init__(self, cfg, rng=None):
        self.cfg = cfg
        self.rng = rng or random.Random()
        self.lines = {k: list(v) for k, v in L.LINES.items()}
        for key, extra in (cfg.get('custom_lines') or {}).items():
            if isinstance(extra, list):
                self.lines.setdefault(key, []).extend(str(x) for x in extra)
        self.last_line = {}
        self.last_said = -1e9
        self.app = None
        self.seen = {}          # app / site key -> last time it was in front
        self.away = False
        self.warned_battery = False
        self.was_charging = None
        self.greeted = False
        self.last_night = -1e9

    def line(self, key):
        options = self.lines.get(key) or []
        if not options:
            return None
        if len(options) > 1:
            options = [o for o in options if o != self.last_line.get(key)]
        text = self.rng.choice(options)
        self.last_line[key] = text
        return text

    def say(self, key, now, important=False):
        """A line for `key` if it isn't too soon since the last one."""
        gap = QUICK_GAP if important else self.cfg.get('chatter_gap_seconds', 45)
        if now - self.last_said < gap:
            return None
        text = self.line(key)
        if not text:
            return None
        self.last_said = now
        return Say(text, L.ANIM.get(key))

    def observe(self, now, snap):
        """Things to say for this moment (usually nothing)."""
        if not self.cfg.get('chatter', True) or snap is None:
            return []
        out = []

        def add(item):
            if item:
                out.append(item)

        if not self.greeted:
            self.greeted = True
            if 5 <= snap.hour < 12:
                add(self.say('morning', now, important=True))
            else:
                add(self.say('hello_pet', now, important=True))

        # away and back
        if snap.idle >= AWAY_AFTER and not self.away:
            self.away = True
            add(self.say('idle', now, important=True))
        elif self.away and snap.idle < 2:
            self.away = False
            add(self.say('back', now, important=True))

        # battery
        if snap.battery is not None:
            if snap.charging and self.was_charging is False:
                add(self.say('charging', now, important=True))
                self.warned_battery = False
            elif not snap.charging and snap.battery <= 20 and not self.warned_battery:
                self.warned_battery = True
                add(self.say('battery_low', now, important=True))
            self.was_charging = snap.charging

        # late at night, while you're still busy
        if 0 <= snap.hour < 5 and snap.idle < 60 and now - self.last_night > NIGHT_AGAIN_AFTER:
            self.last_night = now
            add(self.say('night', now))

        # apps and websites
        app = app_key(snap.exe)
        if app and app != self.app:
            fresh = now - self.seen.get(app, -1e9) > NEW_APP_AFTER
            if fresh or self.rng.random() < 0.15:
                add(self.say(app, now, important=fresh))
        if app:
            self.seen[app] = now
        site = site_key(app, snap.title)
        if site:
            if now - self.seen.get('site:' + site, -1e9) > SITE_AGAIN_AFTER:
                add(self.say(site, now, important=True))
            self.seen['site:' + site] = now
        self.app = app
        return out[:1]  # one line at a time

    def busy_with(self, snap):
        """The animation matching what you're doing right now (if you're active in a known app)."""
        if snap is None or snap.idle > 5:
            return None
        app = app_key(snap.exe)
        return L.ANIM.get(site_key(app, snap.title) or app) if app else None


def snapshot(winapi):
    """What's happening on the PC right now, read from Windows."""
    exe, title = winapi.foreground_app()
    battery, charging = winapi.battery()
    return Snapshot(exe, title, winapi.idle_seconds(), battery, charging, time.localtime().tm_hour)
