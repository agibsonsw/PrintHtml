"""Add SubNotify support messages if SubNotify is installed."""
import sublime
try:
    from SubNotify.sub_notify import SubNotifyIsReadyCommand as Notify
except:
    class Notify:

        """Fallback Notify for when SubNotify is not defined."""

        @classmethod
        def is_ready(cls):
            """Return false to disable SubNotify usage."""

            return False


def notify(msg):
    """Notify message."""

    settings = sublime.load_settings("ExportHtml.sublime-settings")
    if settings.get("use_sub_notify", False) and Notify.is_ready():
        sublime.run_command("sub_notify", {"title": "ExportHtml", "msg": msg})
    else:
        sublime.status_message(msg)


def error(msg):
    """Error message."""

    settings = sublime.load_settings("ExportHtml.sublime-settings")
    if settings.get("use_sub_notify", False) and Notify.is_ready():
        sublime.run_command("sub_notify", {"title": "ExportHtml", "msg": msg, "level": "error"})
    else:
        sublime.error_message("ExportHtml:\n%s" % msg)
