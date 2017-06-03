"""
Open browser.

Licensed under MIT
Copyright (c) 2014 - 2017 Isaac Muse <isaacmuse@gmail.com>
"""
import webbrowser
import subprocess
import sys
import os
import json

if sys.platform.startswith('win'):
    PLATFORM = "windows"
elif sys.platform == "darwin":
    PLATFORM = "osx"
else:
    PLATFORM = "linux"


def to_unicode(string, encoding='utf-8'):
    """Convert byte string to unicode."""

    return str(string, encoding) if isinstance(string, bytes) else string


def open_in_browser(name):
    """Auto open HTML."""

    if PLATFORM == "osx":
        web_handler = None
        try:
            # In case HTML is defaulted to an editor or something, try to check URL handling.
            launch_services = os.path.expanduser(
                '~/Library/Preferences/com.apple.LaunchServices/com.apple.launchservices.secure.plist'
            )
            if not os.path.exists(launch_services):
                launch_services = os.path.expanduser('~/Library/Preferences/com.apple.LaunchServices.plist')
            with open(launch_services, "rb") as f:
                content = f.read()
            args = ["plutil", "-convert", "json", "-o", "-", "--", "-"]
            p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            p.stdin.write(content)
            out = p.communicate()[0]
            plist = json.loads(to_unicode(out))
            for handler in plist['LSHandlers']:
                if handler.get('LSHandlerURLScheme', '') == "http":
                    web_handler = handler.get('LSHandlerRoleAll', None)
                    break
        except Exception:
            pass
        if web_handler is not None:
            # Open with the URL handler we found
            subprocess.Popen(['open', '-b', web_handler, name])
        else:
            # Just open normaly as we never found a web_handler
            subprocess.Popen(['open', name])
    elif PLATFORM == "windows":
        webbrowser.open(name, new=2)
    else:
        # Linux
        try:
            # Maybe...?
            subprocess.Popen(['xdg-open', name])
        except OSError:
            # Well we gave it our best shot...
            webbrowser.open(name, new=2)
