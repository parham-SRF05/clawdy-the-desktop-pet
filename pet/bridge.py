"""Reads every Claude Code session's event log (written by hooks/pet_hook.py) and works out:
  - one mood for the pet (the most urgent session wins: waiting for you > working > idle),
  - each session's progress for the hover panel (current action, steps, time, tasks).
"""
import collections
import json
import os
import time

STATE_DIR = os.path.join(os.path.expanduser('~'), '.claude-pet', 'sessions')
WORKING_TIMEOUT = 600    # "working" but silent this long: the session probably closed
WAITING_TIMEOUT = 1800   # "needs you" this long: you've clearly moved on
SHOW_FOR = 3600          # sessions quiet for longer than this leave the hover panel
FRESH = 10               # only react to events newer than this (no replays when the pet starts)

TOOL_ACTIVITY = {
    'Edit': 'type', 'Write': 'type', 'MultiEdit': 'type', 'NotebookEdit': 'type',
    'Read': 'read', 'Grep': 'read', 'Glob': 'read', 'LS': 'read',
    'Bash': 'command', 'PowerShell': 'command', 'BashOutput': 'command', 'KillShell': 'command',
    'Monitor': 'command', 'WebFetch': 'web', 'WebSearch': 'web',
}
WORKING_EVENTS = {'UserPromptSubmit', 'PreToolUse', 'PostToolUse', 'PostToolUseFailure',
                  'SubagentStart', 'SubagentStop', 'PreCompact', 'TaskCreated', 'TaskCompleted'}
REACTIONS = {'Stop': 'done', 'StopFailure': 'error', 'PostToolUseFailure': 'oops',
             'SessionStart': 'hello', 'SessionEnd': 'bye', 'PermissionRequest': 'needs_you',
             'Notification': 'needs_you', 'PreCompact': 'compact'}

Mood = collections.namedtuple('Mood', 'state activity project reactions')


def activity_for(tool):
    if tool in TOOL_ACTIVITY:
        return TOOL_ACTIVITY[tool]
    if tool.startswith('mcp__'):
        return 'web'
    return 'think'


def classify(record, now):
    """('needs_you' | 'working' | 'idle', activity) from a session's latest event."""
    age = now - record.get('t', 0)
    event = record.get('e')
    if event in ('PermissionRequest', 'Notification'):
        return ('needs_you', None) if age < WAITING_TIMEOUT else ('idle', None)
    if event in WORKING_EVENTS and age < WORKING_TIMEOUT:
        if event in ('PreToolUse', 'PostToolUse'):
            return 'working', activity_for(record.get('tool', ''))
        return 'working', 'think'
    return 'idle', None


class Session:
    def __init__(self):
        self.last = {}
        self.project = ''
        self.title = ''
        self.started = None      # when the current request began
        self.finished = None     # when Claude finished it
        self.steps = 0
        self.detail = ''
        self.recent = collections.deque(maxlen=3)
        self.todos = []
        self.tasks = collections.OrderedDict()   # task id -> [subject, status]

    def apply(self, rec):
        event, t = rec.get('e'), rec.get('t', 0)
        if t >= self.last.get('t', 0):
            self.last = rec
        if rec.get('project'):
            self.project = rec['project']
        if event == 'UserPromptSubmit':
            self.started, self.finished, self.steps, self.detail = t, None, 0, ''
            self.recent.clear()
            if rec.get('title'):
                self.title = rec['title']
        elif event == 'PreToolUse':
            self.steps += 1
            self.started = self.started or t
            self.finished = None
            detail = rec.get('detail', '')
            if detail:
                self.detail = detail
                if not self.recent or self.recent[0] != detail:
                    self.recent.appendleft(detail)
        elif event in ('Stop', 'StopFailure'):
            self.finished, self.detail = t, ''
        if isinstance(rec.get('todos'), list):
            self.todos = [(str(c), str(s)) for c, s in rec['todos']]
        task = rec.get('task')
        if isinstance(task, dict) and task.get('id'):
            entry = self.tasks.get(task['id'])
            if task.get('status') == 'deleted':
                self.tasks.pop(task['id'], None)
            elif entry is None:
                self.tasks[task['id']] = [task.get('subject') or 'Task %s' % task['id'], task.get('status') or 'pending']
            else:
                entry[0] = task.get('subject') or entry[0]
                entry[1] = task.get('status') or entry[1]


class Bridge:
    def __init__(self, state_dir=STATE_DIR):
        self.state_dir = state_dir
        self.offsets = {}    # file -> bytes read
        self.partial = {}    # file -> unfinished last line
        self.sessions = {}   # file -> Session
        self.new = []        # records read in this poll

    def _read(self, name, path, size):
        offset = self.offsets.get(name, 0)
        if size < offset:  # file was replaced: start again
            offset, self.sessions[name], self.partial[name] = 0, Session(), b''
        if size == offset:
            return
        try:
            with open(path, 'rb') as f:
                f.seek(offset)
                chunk = f.read(size - offset)
        except OSError:
            return
        self.offsets[name] = offset + len(chunk)
        data = self.partial.get(name, b'') + chunk
        lines = data.split(b'\n')
        self.partial[name] = lines.pop()  # a line still being written stays for next time
        session = self.sessions.setdefault(name, Session())
        for line in lines:
            try:
                rec = json.loads(line.decode('utf-8'))
            except ValueError:
                continue
            if isinstance(rec, dict) and 'e' in rec:
                session.apply(rec)
                self.new.append(rec)

    def _scan(self):
        self.new = []
        try:
            entries = [e for e in os.scandir(self.state_dir) if e.name.endswith('.jsonl')]
        except OSError:
            entries = []
        present = set()
        for entry in entries:
            present.add(entry.name)
            try:
                self._read(entry.name, entry.path, entry.stat().st_size)
            except OSError:
                continue
        for gone in set(self.sessions) - present:
            for table in (self.sessions, self.offsets, self.partial):
                table.pop(gone, None)

    def poll(self, now=None):
        now = time.time() if now is None else now
        self._scan()
        reactions = [REACTIONS[r['e']] for r in self.new
                     if r.get('e') in REACTIONS and now - r.get('t', 0) < FRESH]
        waiting, working = [], []
        for s in self.sessions.values():
            state, activity = classify(s.last, now)
            if state == 'needs_you':
                waiting.append(s)
            elif state == 'working':
                working.append((s, activity))
        if waiting:
            latest = max(waiting, key=lambda s: s.last.get('t', 0))
            return Mood('needs_you', None, latest.project, reactions)
        if working:
            latest, activity = max(working, key=lambda item: item[0].last.get('t', 0))
            return Mood('working', activity, latest.project, reactions)
        return Mood('idle', None, '', reactions)

    def progress(self, now=None):
        """Recently active sessions, most urgent first, for the hover panel."""
        now = time.time() if now is None else now
        out = []
        for s in self.sessions.values():
            last_t = s.last.get('t', 0)
            if not s.last or now - last_t > SHOW_FOR or s.last.get('e') == 'SessionEnd':
                continue
            state, _ = classify(s.last, now)
            if state == 'idle' and s.finished:
                state = 'done'
            tasks = [(v[0], v[1]) for v in s.tasks.values()] or list(s.todos)
            out.append({'state': state, 'project': s.project, 'title': s.title, 'detail': s.detail,
                        'steps': s.steps, 'started': s.started, 'finished': s.finished, 'tasks': tasks,
                        'recent': list(s.recent), 'time': last_t})
        rank = {'needs_you': 0, 'working': 1, 'done': 2, 'idle': 3}
        out.sort(key=lambda p: (rank[p['state']], -p['time']))
        return out[:3]

    def cleanup(self, older_than=86400):
        """Forget sessions that ended long ago (and files from older versions of the pet)."""
        cutoff = time.time() - older_than
        try:
            for entry in os.scandir(self.state_dir):
                old_format = entry.name.endswith(('.json', '.tmp'))
                if old_format or (entry.name.endswith('.jsonl') and entry.stat().st_mtime < cutoff):
                    os.remove(entry.path)
        except OSError:
            pass
