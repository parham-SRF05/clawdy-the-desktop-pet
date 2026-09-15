"""Everything Clawdy says, and which apps and websites it recognises.

Add your own lines in config.json, e.g. "custom_lines": {"chrome": ["My own Chrome joke"]}.
"""

# program file name -> app key
APPS = {
    'chrome.exe': 'chrome', 'msedge.exe': 'edge', 'firefox.exe': 'firefox', 'brave.exe': 'brave',
    'opera.exe': 'browser', 'opera_gx.exe': 'browser', 'vivaldi.exe': 'browser', 'arc.exe': 'browser',
    'code.exe': 'vscode', 'cursor.exe': 'cursor', 'windsurf.exe': 'ide', 'devenv.exe': 'ide',
    'pycharm64.exe': 'ide', 'idea64.exe': 'ide', 'webstorm64.exe': 'ide', 'rider64.exe': 'ide',
    'sublime_text.exe': 'ide', 'notepad++.exe': 'notepad', 'notepad.exe': 'notepad',
    'windowsterminal.exe': 'terminal', 'wt.exe': 'terminal', 'cmd.exe': 'terminal',
    'powershell.exe': 'terminal', 'pwsh.exe': 'terminal', 'mintty.exe': 'terminal',
    'claude.exe': 'claude', 'explorer.exe': 'explorer',
    'steam.exe': 'steam', 'steamwebhelper.exe': 'steam', 'epicgameslauncher.exe': 'steam',
    'acs.exe': 'assetto', 'content manager.exe': 'contentmanager',
    'spotify.exe': 'spotify', 'discord.exe': 'discord', 'telegram.exe': 'chat', 'whatsapp.exe': 'chat',
    'winword.exe': 'word', 'excel.exe': 'excel', 'powerpnt.exe': 'powerpoint',
    'githubdesktop.exe': 'github', 'obs64.exe': 'obs', 'vlc.exe': 'video', 'taskmgr.exe': 'taskmanager',
    'photoshop.exe': 'art', 'figma.exe': 'art', 'blender.exe': 'art',
}
BROWSERS = {'chrome', 'edge', 'firefox', 'brave', 'browser'}
CODING = {'vscode', 'cursor', 'ide', 'notepad'}

# website keyword (in a browser's window title, lowercase) -> key
SITES = [
    ('youtube', 'youtube'), ('github', 'github_site'), ('stack overflow', 'stackoverflow'),
    ('chatgpt', 'chatgpt'), ('gemini', 'chatgpt'), ('claude', 'claude_site'), ('reddit', 'reddit'),
    ('netflix', 'movie'), ('twitch', 'movie'), ('prime video', 'movie'), ('gmail', 'mail'), ('outlook', 'mail'),
    ('formula 1', 'f1'), ('f1.com', 'f1'), (' x ', 'social'), ('twitter', 'social'), ('instagram', 'social'),
    ('tiktok', 'social'), ('assetto', 'assetto_site'), ('google docs', 'word'),
]

# what Clawdy does while saying something about an app, and while you use it
ANIM = {
    'chrome': 'web', 'edge': 'web', 'firefox': 'web', 'brave': 'web', 'browser': 'web',
    'vscode': 'type', 'cursor': 'type', 'ide': 'type', 'notepad': 'type', 'word': 'type',
    'terminal': 'command', 'claude': 'wave', 'explorer': 'read', 'excel': 'read', 'github': 'command',
    'steam': 'celebrate', 'assetto': 'celebrate', 'contentmanager': 'celebrate', 'spotify': 'dance',
    'discord': 'happy', 'chat': 'happy', 'powerpoint': 'think', 'obs': 'wave', 'video': 'sit',
    'taskmanager': 'error', 'art': 'think',
    'youtube': 'sit', 'github_site': 'read', 'stackoverflow': 'read', 'chatgpt': 'error', 'claude_site': 'celebrate',
    'reddit': 'read', 'movie': 'sit', 'mail': 'read', 'f1': 'celebrate', 'social': 'look', 'assetto_site': 'dance',
    'idle': 'sit', 'back': 'wave', 'morning': 'wave', 'night': 'sleep', 'battery_low': 'error',
    'charging': 'happy', 'dizzy': 'dizzy', 'hello_pet': 'wave',
}

LINES = {
    'chrome': ["Chrome! Say goodbye to your RAM.", "Opening 47 tabs again?", "Chrome's here. Hide the memory!",
               "Browsing time! Don't forget about me."],
    'edge': ["Edge? Bold choice.", "Microsoft Edge... are you okay?"],
    'firefox': ["Firefox! A browser of culture.", "A fox on fire. Classic."],
    'brave': ["Brave! Very brave."],
    'browser': ["Off to the internet! Bring snacks."],
    'vscode': ["Code time! I'll grab my laptop.", "VS Code! Let's write some features. And bugs.",
               "Tabs or spaces? Choose wisely."],
    'cursor': ["Cursor, huh? I see what you did there.", "Coding! I'll type along."],
    'ide': ["Serious IDE energy. Let's build.", "Coding session! I'm on it too."],
    'notepad': ["Notepad. The purest editor.", "Old school! I like it."],
    'terminal': ["The terminal! Feeling like a hacker?", "Careful with rm -rf!", "Type fast, look cool."],
    'claude': ["Hey, that's my family!", "Say hi to Claude for me!"],
    'explorer': ["Looking for a file? It's in Downloads. It's always in Downloads.",
                 "Organising files? Brave."],
    'steam': ["Steam! Work can wait, right?", "Game time? I'll cheer for you!"],
    'assetto': ["Race time! Mind the rear at Spa.", "Lights out and away we go!"],
    'contentmanager': ["Content Manager! Which car today?", "Going racing? Don't forget your delta screen!"],
    'spotify': ["Music! Play something I can dance to.", "Ooh, can I pick the next song?"],
    'discord': ["Discord! Tell them I said hi.", "Gaming or gossip?"],
    'chat': ["New messages? I won't read them. Promise."],
    'word': ["Writing time! You've got this.", "Big words, small pet. Let's go."],
    'excel': ["Spreadsheets! So many little boxes. Like me!"],
    'powerpoint': ["A presentation! Add more transitions."],
    'github': ["GitHub Desktop! Commit early, commit often."],
    'obs': ["Recording? Let me fix my hair."],
    'video': ["Movie time? I'll be quiet."],
    'taskmanager': ["Task Manager? Please don't end me!", "Careful in there... I live in pythonw.exe."],
    'art': ["Making art? I'll pose."],
    'youtube': ["YouTube? Just one video, sure.", "A quick break... right?"],
    'github_site': ["GitHub! Push it real good.", "Checking the repo? Proud of you."],
    'stackoverflow': ["Copy-paste engineering. I respect it.", "The answer's always the second one."],
    'chatgpt': ["ChatGPT?! I'm right here!", "Hey! What about Claude?"],
    'claude_site': ["That's where I'm from!", "Claude! My favourite."],
    'reddit': ["Reddit! See you in three hours."],
    'movie': ["Movie night? I'll bring the popcorn."],
    'mail': ["Inbox zero? I believe in you."],
    'f1': ["F1! Box box!", "Checking the standings?"],
    'social': ["Doomscrolling detected.", "Just five more minutes..."],
    'assetto_site': ["More Assetto mods? Yes please!"],
    'idle': ["Hello? Anyone there?", "I'll just wait here then..."],
    'back': ["Welcome back!", "You're back! I missed you."],
    'morning': ["Good morning! Ready to build?", "Morning! Coffee first?"],
    'night': ["It's really late... bed time?", "Still up? Your future self says sleep."],
    'battery_low': ["Battery low! Plug me in!", "I'm running on fumes here!"],
    'charging': ["Mmm, electricity.", "Charging! I feel stronger already."],
    'dizzy': ["Stop poking me!", "Whoa... the room is spinning."],
    'poke': ["Hehe!", "Boop!", "That tickles!", "Hi there!"],
    'done': ["Done!", "All done!", "Ta-da!", "Finished! High five?"],
    'hello_pet': ["Hi! I'm Clawdy.", "Hello! Let's have a good day."],
}
