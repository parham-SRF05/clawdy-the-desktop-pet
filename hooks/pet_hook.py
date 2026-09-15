"""Claude Code hook for Claude Pet.

Adds one line per event to a small log per session, which the pet reads to animate and to show
progress when you hover over it. Kept: event, tool, a short description of the action (like
"Editing app.py"), task list titles and statuses, the project folder name, and (unless turned off
with "store_task_titles": false) the first line of your request. Never code or file contents.
Everything stays on this PC. It runs in the background, prints nothing and never fails.
"""
import json
import os
import sys
import time

ROOT = os.path.join(os.path.expanduser('~'), '.claude-pet')
STATE_DIR = os.path.join(ROOT, 'sessions')
CONFIG = os.path.join(ROOT, 'config.json')
PET = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'claude_pet.pyw')

EVENTS = {'SessionStart', 'SessionEnd', 'UserPromptSubmit', 'PreToolUse', 'PostToolUse',
          'PostToolUseFailure', 'PermissionRequest', 'Notification', 'Stop', 'StopFailure',
          'SubagentStart', 'SubagentStop', 'PreCompact', 'TaskCreated', 'TaskCompleted'}
# Other notifications (e.g. "auth_success") say nothing about what the session is doing.
NOTIFICATIONS = {'permission_prompt', 'elicitation_dialog', 'elicitation_url_dialog', 'agent_needs_input'}


def short(text, limit=60):
    text = ' '.join(str(text or '').split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + '…'


def base(path):
    return os.path.basename(str(path or '').rstrip('\\/'))


def describe(tool, args):
    """A short, human description of a tool call, e.g. "Editing app.py"."""
    args = args if isinstance(args, dict) else {}
    if tool in ('Edit', 'MultiEdit', 'NotebookEdit'):
        return 'Editing ' + base(args.get('file_path') or args.get('notebook_path'))
    if tool == 'Write':
        return 'Writing ' + base(args.get('file_path'))
    if tool == 'Read':
        return 'Reading ' + base(args.get('file_path'))
    if tool == 'Grep':
        return short('Searching for "%s"' % args.get('pattern', ''))
    if tool == 'Glob':
        return short('Finding ' + str(args.get('pattern', '')))
    if tool in ('Bash', 'PowerShell'):
        return short(args.get('description') or 'Running ' + str(args.get('command', '')))
    if tool == 'WebFetch':
        url = str(args.get('url', ''))
        return short('Reading ' + (url.split('/')[2] if '://' in url else url))
    if tool == 'WebSearch':
        return short('Searching the web: ' + str(args.get('query', '')))
    if tool in ('Agent', 'Task'):
        return short('Agent: ' + str(args.get('description') or args.get('subagent_type') or 'working'))
    if tool in ('TaskCreate', 'TaskUpdate', 'TodoWrite'):
        return 'Updating the task list'
    if tool.startswith('mcp__'):
        return short('Using ' + tool.split('__', 2)[-1].replace('_', ' '))
    return short(tool)


def wants_titles():
    try:
        with open(CONFIG, encoding='utf-8') as f:
            return json.load(f).get('store_task_titles', True) is not False
    except (OSError, ValueError, AttributeError):
        return True


def record_for(data, now, titles=True):
    event = data.get('hook_event_name')
    if event not in EVENTS:
        return None
    if event == 'Notification' and data.get('notification_type') not in NOTIFICATIONS:
        return None
    tool = str(data.get('tool_name') or '')
    args = data.get('tool_input') if isinstance(data.get('tool_input'), dict) else {}
    rec = {'e': event, 't': now, 'project': base(data.get('cwd'))}
    if tool:
        rec['tool'] = tool
    if data.get('notification_type'):
        rec['notification'] = str(data['notification_type'])
    if event == 'UserPromptSubmit' and titles:
        lines = [line for line in str(data.get('prompt') or '').splitlines() if line.strip()]
        rec['title'] = short(lines[0], 80) if lines else ''
    if event == 'PreToolUse':
        rec['detail'] = describe(tool, args)
        if tool == 'TodoWrite' and isinstance(args.get('todos'), list):
            rec['todos'] = [[short(t.get('content'), 80), str(t.get('status', 'pending'))]
                            for t in args['todos'][:40] if isinstance(t, dict)]
        elif tool == 'TaskUpdate' and args.get('taskId') is not None:
            rec['task'] = {'id': str(args['taskId']), 'status': str(args.get('status') or ''),
                           'subject': short(args.get('subject'), 80) if args.get('subject') else ''}
    if event in ('TaskCreated', 'TaskCompleted'):
        rec['task'] = {'id': str(data.get('task_id', '')), 'subject': short(data.get('task_subject'), 80),
                       'status': 'completed' if event == 'TaskCompleted' else 'pending'}
    return rec


def write(state_dir, session_id, record):
    """One line appended per event: hooks run in parallel, and appends never overwrite each other."""
    name = ''.join(ch for ch in str(session_id) if ch.isalnum() or ch in '-_')[:80] or 'unknown'
    os.makedirs(state_dir, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False) + '\n'
    with open(os.path.join(state_dir, name + '.jsonl'), 'a', encoding='utf-8') as f:
        f.write(line)


def pet_running():
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.OpenMutexW.restype = ctypes.c_void_p
    handle = kernel32.OpenMutexW(0x00100000, False, 'Local\\ClaudePetInstance')  # SYNCHRONIZE
    if handle:
        kernel32.CloseHandle(ctypes.c_void_p(handle))
        return True
    return False


def start_pet():
    """Start the pet when a Claude Code session starts (unless turned off in the pet's settings)."""
    try:
        with open(CONFIG, encoding='utf-8') as f:
            if json.load(f).get('start_with_claude_code', True) is False:
                return
    except (OSError, ValueError, AttributeError):
        pass
    pythonw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
    if not os.path.exists(PET) or not os.path.exists(pythonw) or pet_running():
        return
    import subprocess
    quiet = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
    detached = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    try:  # also leave Claude Code's process group, so the pet keeps running after the hook ends
        subprocess.Popen([pythonw, PET], creationflags=detached | 0x01000000, **quiet)
    except OSError:
        subprocess.Popen([pythonw, PET], creationflags=detached, **quiet)


def main():
    text = sys.stdin.buffer.read().decode('utf-8-sig', 'replace').strip()  # tolerate a byte-order mark
    data = json.loads(text or '{}')
    event = data.get('hook_event_name')
    record = record_for(data, time.time(), titles=wants_titles() if event == 'UserPromptSubmit' else True)
    if record:
        write(STATE_DIR, data.get('session_id') or 'unknown', record)
        if event == 'SessionStart':
            start_pet()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        pass
