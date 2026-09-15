"""The pet's window: draws the pixel art, moves it smoothly, handles the mouse and the progress panel."""
import os
import subprocess
import sys
import time
import tkinter as tk
import traceback

from . import config, skins, sprites, winapi
from .behavior import Pet, walk_zone
from .bridge import Bridge, Mood

KEY = '#ff00fe'            # see-through colour: clicks on it pass to the window below
FRAME_TIME = 1 / 60
POLL_EVERY, AREA_EVERY, FULLSCREEN_EVERY, TOPMOST_EVERY, PANEL_EVERY = 0.15, 2.0, 0.5, 1.0, 0.5
BUBBLE_ROOM = 48           # px above the pet for speech bubbles
LOG_FILE = os.path.join(config.CONFIG_DIR, 'pet.log')

BG, BORDER, TEXT, MUTED = '#1f1e1d', '#d77757', '#f4f1ea', '#9b978f'
GREEN, ORANGE, RED, TRACK = '#8fce8a', '#e8906f', '#ff7a7a', '#3a3836'
STATE_LOOK = {'needs_you': ('Needs you', RED), 'working': ('Working', ORANGE),
              'done': ('Done', GREEN), 'idle': ('Idle', MUTED)}


def log(message):
    try:
        os.makedirs(config.CONFIG_DIR, exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(time.strftime('%Y-%m-%d %H:%M:%S  ') + message + '\n')
    except OSError:
        pass


def photo(master, rows):
    """A 1x PhotoImage from rows of colours (None = see-through)."""
    img = tk.PhotoImage(master=master, width=len(rows[0]), height=len(rows))
    img.put(' '.join('{' + ' '.join(c or KEY for c in row) + '}' for row in rows))
    return img


def scaled(master, img, scale, flip=False):
    out = tk.PhotoImage(master=master, width=img.width() * scale, height=img.height() * scale)
    out.tk.call(out, 'copy', img, '-zoom', scale, scale)
    if flip:
        mirrored = tk.PhotoImage(master=master, width=out.width(), height=out.height())
        mirrored.tk.call(mirrored, 'copy', out, '-subsample', -1, 1)
        return mirrored
    return out


def duration(seconds):
    seconds = max(0, int(seconds))
    if seconds < 60:
        return '%ds' % seconds
    if seconds < 3600:
        return '%dm %02ds' % (seconds // 60, seconds % 60)
    return '%dh %02dm' % (seconds // 3600, seconds % 3600 // 60)


class ProgressPanel:
    """The card that appears while you hover over the pet: what Claude is doing and how far along it is."""

    WIDTH = 300

    def __init__(self, root, name):
        self.name = name
        self.win = tk.Toplevel(root, bg=BORDER)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.wm_attributes('-topmost', True)
        self.body = tk.Frame(self.win, bg=BG, padx=12, pady=10)
        self.body.pack(padx=2, pady=2)
        self.win.update_idletasks()
        self.hwnd = winapi.top_level_handle(self.win)
        winapi.style_pet_window(self.hwnd)
        self.visible = False

    def label(self, parent, text, color=TEXT, bold=False, size=9, **pack):
        lbl = tk.Label(parent, text=text, fg=color, bg=BG, anchor='w', justify='left',
                       font=('Segoe UI Semibold' if bold else 'Segoe UI', size), wraplength=self.WIDTH)
        lbl.pack(fill='x', **pack)
        return lbl

    def render(self, sessions, now):
        for child in self.body.winfo_children():
            child.destroy()
        head = tk.Frame(self.body, bg=BG)
        head.pack(fill='x')
        tk.Label(head, text=self.name, fg=ORANGE, bg=BG, font=('Segoe UI Semibold', 11)).pack(side='left')
        if not sessions:
            self.label(self.body, 'No Claude Code activity yet.', MUTED, pady=(6, 0))
            self.label(self.body, 'Give Claude a task, then hover over me again.', MUTED)
            return
        for i, s in enumerate(sessions):
            if i:
                tk.Frame(self.body, bg=TRACK, height=1).pack(fill='x', pady=8)
            self._session(s, now, first=(i == 0), head=head)

    def _session(self, s, now, first, head):
        text, color = STATE_LOOK.get(s['state'], STATE_LOOK['idle'])
        if first:
            tk.Label(head, text='  ' + text, fg=color, bg=BG, font=('Segoe UI Semibold', 9)).pack(side='right')
        else:
            self.label(self.body, text, color, bold=True)
        if s['project']:
            self.label(self.body, s['project'], MUTED, size=8, pady=(4 if first else 0, 0))
        if s['title']:
            self.label(self.body, s['title'], TEXT, bold=True)
        if s['state'] == 'needs_you':
            self.label(self.body, 'Waiting for your approval', RED, pady=(2, 0))
        elif s['state'] == 'working' and s['detail']:
            self.label(self.body, '▶  ' + s['detail'], ORANGE, pady=(2, 0))
        if s['started']:
            end = s['finished'] or now
            verb = 'took' if s['finished'] else 'so far'
            self.label(self.body, '%d steps  ·  %s %s' % (s['steps'], duration(end - s['started']), verb),
                       MUTED, size=8, pady=(2, 0))
        tasks = s['tasks']
        if tasks:
            done = sum(1 for _, status in tasks if status == 'completed')
            self.label(self.body, 'Tasks  %d/%d' % (done, len(tasks)), TEXT, bold=True, pady=(8, 2))
            bar = tk.Canvas(self.body, width=self.WIDTH, height=6, bg=TRACK, highlightthickness=0, bd=0)
            bar.pack(anchor='w', pady=(0, 4))
            bar.create_rectangle(0, 0, int(self.WIDTH * done / len(tasks)), 6, fill=GREEN, width=0)
            for title, status in tasks[:8]:
                mark, col = {'completed': ('✓', GREEN), 'in_progress': ('▶', ORANGE)}.get(status, ('○', MUTED))
                self.label(self.body, '%s  %s' % (mark, title), col if status != 'completed' else MUTED)
            if len(tasks) > 8:
                self.label(self.body, '+ %d more' % (len(tasks) - 8), MUTED, size=8)
        if s['recent']:
            self.label(self.body, 'Recent: ' + '  ·  '.join(s['recent']), MUTED, size=8, pady=(6, 0))

    def place_above(self, center_x, top_y, screen_left, screen_right):
        self.win.update_idletasks()
        w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        x = int(min(max(center_x - w / 2, screen_left + 4), screen_right - w - 4))
        winapi.place(self.hwnd, x, int(top_y - h - 4))
        if not self.visible:
            winapi.show(self.hwnd, True)
            self.visible = True

    def hide(self):
        if self.visible:
            winapi.show(self.hwnd, False)
            self.visible = False


class App:
    def __init__(self, cfg):
        self.cfg = cfg
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.configure(bg=KEY)
        self.root.wm_attributes('-transparentcolor', KEY)
        self.root.wm_attributes('-topmost', True)

        self.frames, size = self._load_art()
        self.sprite_w, self.sprite_h = size
        self.canvas_w = self.sprite_w + 180
        self.canvas_h = self.sprite_h + BUBBLE_ROOM
        self.canvas = tk.Canvas(self.root, width=self.canvas_w, height=self.canvas_h, bg=KEY,
                                highlightthickness=0, bd=0)
        self.canvas.pack()
        self.sprite = self.canvas.create_image(self.canvas_w // 2, self.canvas_h, anchor='s')
        self.bubble_box = self.canvas.create_rectangle(0, 0, 0, 0, fill='#ffffff', outline='#3b2219',
                                                       width=2, state='hidden')
        self.bubble_text = self.canvas.create_text(0, 0, text='', fill='#3b2219', state='hidden',
                                                   font=('Segoe UI', 9, 'bold'))
        self.shown_image = self.shown_bubble = self.shown_pos = None

        now = time.perf_counter()
        self.screen = winapi.walk_area()
        self.pet = Pet(cfg, self._zone(), size, now, screen=self.screen)
        self.bridge = Bridge()
        self.bridge.cleanup()
        self.mood = Mood('idle', None, '', [])
        self.next_poll = self.next_area = self.next_fullscreen = self.next_topmost = self.next_panel = now
        self.hidden = False
        self.press = None
        self.dragging = False
        self.hover_off_at = None
        self.last = now

        self.root.geometry('%dx%d+%d+%d' % ((self.canvas_w, self.canvas_h) + self.pet.window_origin(
            self.canvas_w, self.canvas_h)))
        self.root.deiconify()
        self.root.update_idletasks()
        self.hwnd = winapi.top_level_handle(self.root)
        winapi.style_pet_window(self.hwnd)
        self.panel = ProgressPanel(self.root, cfg['name'])

        self.canvas.bind('<ButtonPress-1>', self._press)
        self.canvas.bind('<B1-Motion>', self._motion)
        self.canvas.bind('<ButtonRelease-1>', self._release)
        self.canvas.bind('<Button-3>', self._menu)
        self.canvas.bind('<Enter>', self._enter)
        self.canvas.bind('<Leave>', self._leave)
        self.root.after(1, self._tick)

    # --- art -------------------------------------------------------------------------------

    def _load_art(self):
        scale = self.cfg['scale']
        colors = {k: v for k, v in self.cfg['colors'].items() if k in sprites.DEFAULT_COLORS}
        built_in = sprites.build_frames(colors)
        skin, skin_size = {}, None
        try:
            skin, skin_size = skins.load(self.root, self.cfg['skin'])
        except (OSError, ValueError, tk.TclError) as e:
            log('Skin "%s" could not be loaded, using the built-in pet: %r' % (self.cfg['skin'], e))
        use_built_in = skin_size in (None, (sprites.W, sprites.H))
        frames = {}
        for name in set(built_in if use_built_in else ()) | set(skin):
            if name in skin:
                fps, images = skin[name]
            else:
                fps, images = sprites.fps(name), [photo(self.root, rows) for rows in built_in[name]]
            frames[name] = (fps, [scaled(self.root, i, scale) for i in images],
                            [scaled(self.root, i, scale, flip=True) for i in images])
        w, h = skin_size or (sprites.W, sprites.H)
        return frames, (w * scale, h * scale)

    def _zone(self):
        return walk_zone(self.screen, self.cfg['walk_width_percent'], self.cfg['walk_align'])

    # --- every frame -----------------------------------------------------------------------

    def _tick(self):
        start = time.perf_counter()
        try:
            self._step(start)
        except Exception:
            log('Error:\n' + traceback.format_exc())
        delay = FRAME_TIME - (time.perf_counter() - start)
        self.root.after(max(1, int(delay * 1000)), self._tick)

    def _step(self, now):
        dt, self.last = now - self.last, now
        mood = Mood(self.mood.state, self.mood.activity, self.mood.project, [])
        if now >= self.next_poll:
            self.next_poll = now + POLL_EVERY
            mood = self.mood = self.bridge.poll()
        if now >= self.next_area:
            self.next_area = now + AREA_EVERY
            self.screen = winapi.walk_area()
            self.pet.set_area(self._zone(), self.screen)
        if now >= self.next_fullscreen:
            self.next_fullscreen = now + FULLSCREEN_EVERY
            hide = self.cfg['hide_in_fullscreen'] and winapi.fullscreen_app_on_main_screen()
            if hide != self.hidden:
                self.hidden = hide
                winapi.show(self.hwnd, not hide)
                if hide:
                    self._hover_end()
        if self.hover_off_at is not None and now >= self.hover_off_at:
            self._hover_end()
        self.pet.update(now, dt, mood)
        if not self.hidden:
            self._draw(now)
            if self.panel.visible and now >= self.next_panel:
                self._show_panel(now)

    def _draw(self, now):
        pet = self.pet
        fps, right, left = self.frames.get(pet.anim) or self.frames['idle']
        images = right if pet.facing > 0 else left
        image = images[pet.frame(fps, len(images))]
        if image is not self.shown_image:
            self.canvas.itemconfigure(self.sprite, image=image)
            self.shown_image = image

        text = pet.bubble[0] if pet.bubble else None
        if self.panel.visible:
            text = None  # the panel says it all
        if text != self.shown_bubble:
            state = 'normal' if text else 'hidden'
            self.canvas.itemconfigure(self.bubble_box, state=state)
            self.canvas.itemconfigure(self.bubble_text, state=state)
            if text:  # (a hidden item has no size, so show it before measuring)
                cx, bottom = self.canvas_w // 2, BUBBLE_ROOM + self.sprite_h // 3
                self.canvas.itemconfigure(self.bubble_text, text=text)
                self.canvas.coords(self.bubble_text, cx, bottom - 14)
                box = self.canvas.bbox(self.bubble_text)
                if box:
                    x0, y0, x1, y1 = box
                    self.canvas.coords(self.bubble_box, x0 - 8, y0 - 4, x1 + 8, y1 + 4)
            self.shown_bubble = text

        pos = pet.window_origin(self.canvas_w, self.canvas_h)
        if pos != self.shown_pos or now >= self.next_topmost:
            self.next_topmost = now + TOPMOST_EVERY
            self.shown_pos = pos
            winapi.place(self.hwnd, *pos)

    # --- hover: progress panel -------------------------------------------------------------

    def _enter(self, event):
        self.hover_off_at = None
        if self.dragging:
            return
        now = time.perf_counter()
        self.pet.hover(now, True)
        self._show_panel(now)

    def _leave(self, event):
        self.hover_off_at = time.perf_counter() + 0.35  # small grace period: no flicker at the edges

    def _hover_end(self):
        self.hover_off_at = None
        self.pet.hover(time.perf_counter(), False)
        self.panel.hide()

    def _show_panel(self, now):
        self.next_panel = now + PANEL_EVERY
        self.panel.render(self.bridge.progress(), time.time())
        top = self.pet.floor - self.pet.lift - self.sprite_h * 0.7
        self.panel.place_above(self.pet.x, top, self.screen[0], self.screen[1])

    # --- mouse -----------------------------------------------------------------------------

    def _press(self, event):
        self.press = (event.x_root, event.y_root)
        self.dragging = False
        self.grab_offset = (self.pet.x - event.x_root, (self.pet.floor - self.pet.lift) - event.y_root)

    def _motion(self, event):
        if not self.press:
            return
        now = time.perf_counter()
        if not self.dragging and max(abs(event.x_root - self.press[0]), abs(event.y_root - self.press[1])) > 4:
            self.dragging = True
            self._hover_end()
            self.pet.grab(now, event.x_root + self.grab_offset[0], event.y_root + self.grab_offset[1])
        if self.dragging:
            self.pet.drag_to(event.x_root + self.grab_offset[0], event.y_root + self.grab_offset[1])

    def _release(self, event):
        now = time.perf_counter()
        if self.press and self.dragging:
            self.pet.release(now)
        elif self.press:
            self.pet.poke(now)
        self.press = None
        self.dragging = False

    def _menu(self, event):
        self._hover_end()
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label='Wake up' if self.pet.asleep else 'Go to sleep',
                         command=lambda: self.pet.toggle_sleep(time.perf_counter()))
        wander = tk.BooleanVar(self.root, self.cfg['wander'])
        tricks = tk.BooleanVar(self.root, self.cfg['tricks'])
        bubbles = tk.BooleanVar(self.root, self.cfg['bubbles'])
        menu.add_checkbutton(label='Walk around', variable=wander, command=lambda: self._set('wander', wander.get()))
        menu.add_checkbutton(label='Do tricks', variable=tricks, command=lambda: self._set('tricks', tricks.get()))
        menu.add_checkbutton(label='Speech bubbles', variable=bubbles,
                             command=lambda: self._set('bubbles', bubbles.get()))

        area = tk.Menu(menu, tearoff=0)
        width = tk.IntVar(self.root, self.cfg['walk_width_percent'])
        align = tk.StringVar(self.root, self.cfg['walk_align'])
        for percent in (25, 40, 60, 80, 100):
            area.add_radiobutton(label='%d%% of the taskbar' % percent, value=percent, variable=width,
                                 command=lambda p=percent: self._set_area('walk_width_percent', p))
        area.add_separator()
        for side in ('left', 'center', 'right'):
            area.add_radiobutton(label=side.capitalize(), value=side, variable=align,
                                 command=lambda s=side: self._set_area('walk_align', s))
        menu.add_cascade(label='Walking area', menu=area)

        sizes = tk.Menu(menu, tearoff=0)
        size = tk.IntVar(self.root, self.cfg['scale'])
        for scale in (1, 2, 3, 4):
            sizes.add_radiobutton(label='%dx' % scale, value=scale, variable=size,
                                  command=lambda s=scale: self._resize(s))
        menu.add_cascade(label='Size', menu=sizes)
        menu.add_separator()
        menu.add_command(label='Settings file...', command=self._open_settings)
        menu.add_command(label='Quit', command=self.quit)
        self._menu_ref = (menu, area, sizes, wander, tricks, bubbles, width, align, size)  # keep alive
        menu.tk_popup(event.x_root, event.y_root)

    def _set(self, key, value):
        self.cfg[key] = value
        config.save(self.cfg)

    def _set_area(self, key, value):
        self._set(key, value)
        self.pet.set_area(self._zone(), self.screen)  # the pet walks over to its new area

    def _resize(self, scale):
        if scale != self.cfg['scale']:
            self._set('scale', scale)
            self.quit(restart=True)

    def _open_settings(self):
        config.save(self.cfg)
        os.startfile(config.CONFIG_FILE)

    def quit(self, restart=False):
        self.root.destroy()
        if restart:
            winapi.release_instance()
            subprocess.Popen([sys.executable] + sys.argv)

    def run(self):
        self.root.mainloop()


def main():
    winapi.make_dpi_aware()
    if not winapi.single_instance():
        return
    winapi.fine_timer(True)
    try:
        App(config.load()).run()
    except Exception:
        log('Crashed:\n' + traceback.format_exc())
        raise
    finally:
        winapi.fine_timer(False)
