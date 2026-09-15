"""Custom skins: your own pixel art instead of (or on top of) the built-in pet.

A skin is a folder in %USERPROFILE%\\.claude-pet\\skins\\<name>\\ containing:
  sheet.png  - a sprite sheet (hard pixel edges; transparent background)
  skin.json  - where each animation is on the sheet, for example:
      {"frame_width": 32, "frame_height": 32,
       "animations": {"idle": {"row": 0, "frames": 4, "fps": 4},
                      "walk": {"row": 1, "frames": 6, "fps": 10}}}
Animations a skin leaves out keep the built-in art. Set "skin" in config.json to the folder name.
"""
import json
import os
import tkinter as tk

SKINS_DIR = os.path.join(os.path.expanduser('~'), '.claude-pet', 'skins')


def load(master, name, skins_dir=SKINS_DIR):
    """{animation: (fps, [PhotoImage at 1x])} and the frame size, or ({}, None) if there is no skin."""
    if not name:
        return {}, None
    folder = os.path.join(skins_dir, name)
    with open(os.path.join(folder, 'skin.json'), encoding='utf-8') as f:
        meta = json.load(f)
    sheet = tk.PhotoImage(master=master, file=os.path.join(folder, meta.get('image', 'sheet.png')))
    fw, fh = int(meta.get('frame_width', 32)), int(meta.get('frame_height', 32))
    animations = {}
    for anim, info in meta.get('animations', {}).items():
        frames = []
        for i in range(int(info.get('frames', 1))):
            x0, y0 = (int(info.get('column', 0)) + i) * fw, int(info.get('row', 0)) * fh
            if x0 + fw > sheet.width() or y0 + fh > sheet.height():
                break
            frame = tk.PhotoImage(master=master, width=fw, height=fh)
            frame.tk.call(frame, 'copy', sheet, '-from', x0, y0, x0 + fw, y0 + fh, '-to', 0, 0)
            frames.append(frame)
        if frames:
            animations[anim] = (float(info.get('fps', 8)), frames)
    return animations, (fw, fh)
