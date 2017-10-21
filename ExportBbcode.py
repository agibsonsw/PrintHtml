"""
ExportBbCode.

Licensed under MIT.

Copyright (C) 2012  Andrew Gibson <agibsonsw@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of
the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---------------------

Original code has been heavily modifed by Isaac Muse <isaacmuse@gmail.com> for the ExportHtml project.

"""
import sublime
import sublime_plugin
import tempfile
import re
from ExportHtml.lib.color_scheme_matcher import ColorSchemeMatcher
from ExportHtml.lib.color_scheme_tweaker import ColorSchemeTweaker
from ExportHtml.lib.notify import notify

PACKAGE_SETTINGS = "ExportHtml.sublime-settings"

NUMBERED_BBCODE_LINE = '[color=%(color)s]%(line)s [/color]%(code)s\n'

BBCODE_LINE = '%(code)s\n'

BBCODE_CODE = '[color=%(color)s]%(content)s[/color]'

BBCODE_ESCAPE = '[/color][color=%(color_open)s]%(content)s[/color][color=%(color_close)s]'

BBCODE_BOLD = '[b]%(content)s[/b]'

BBCODE_ITALIC = '[i]%(content)s[/i]'

POST_START = '[pre=%(bg_color)s]'

POST_END = '[/pre]\n'

BBCODE_MATCH = re.compile(
    r'''(?x)
    (\[/?)
    (
        (?:
            code|pre|table|tr|td|th|b|i|u|sup|color|
            url|img|list|trac|center|quote|size|li|ul|
            ol|youtube|gvideo
        )
        (?:=[^\]]+)?
    )
    (\])
    '''
)


def sublime_format_path(pth):
    """Format path for internal Sublime use."""

    m = re.match(r"^([A-Za-z]{1}):(?:/|\\)(.*)", pth)
    if sublime.platform() == "windows" and m is not None:
        pth = m.group(1) + "/" + m.group(2)
    return pth.replace("\\", "/")


class ExportBbcodePanelCommand(sublime_plugin.WindowCommand):
    """Show export BBCode panel."""

    def execute(self, value):
        """Execute command."""

        if value >= 0:
            view = self.window.active_view()
            if view is not None:
                ExportBbcode(view).run(**self.args[value])

    def run(self):
        """Run command."""

        options = sublime.load_settings(PACKAGE_SETTINGS).get("bbcode_panel", {})
        menu = []
        self.args = []
        for opt in options:
            k, v = list(opt.items())[0]
            menu.append(k)
            self.args.append(v)

        if len(menu):
            self.window.show_quick_panel(
                menu,
                self.execute
            )


class ExportBbcodeCommand(sublime_plugin.WindowCommand):
    """Export BBCode."""

    def run(self, **kwargs):
        """Run command."""

        view = self.window.active_view()
        if view is not None:
            ExportBbcode(view).run(**kwargs)


class ExportBbcode(object):
    """Take the content of a Sublime view and export BBCode representation."""

    def __init__(self, view):
        """Initialize."""

        self.view = view

    def process_inputs(self, **kwargs):
        """Handle the inputs."""

        return {
            "numbers": bool(kwargs.get("numbers", False)),
            "color_scheme": kwargs.get("color_scheme", None),
            "multi_select": bool(kwargs.get("multi_select", False)),
            "ignore_selections": bool(kwargs.get("ignore_selections", False)),
            "clipboard_copy": bool(kwargs.get("clipboard_copy", True)),
            "view_open": bool(kwargs.get("view_open", False)),
            "filter": kwargs.get("filter", "")
        }

    def setup(self, **kwargs):
        """Setup for export."""

        # Get get general document preferences from sublime preferences
        settings = sublime.load_settings('Preferences.sublime-settings')
        eh_settings = sublime.load_settings(PACKAGE_SETTINGS)
        self.tab_size = settings.get('tab_size', 4)
        self.char_limit = int(eh_settings.get("valid_selection_size", 4))
        self.bground = ''
        self.fground = ''
        self.gbground = ''
        self.gfground = ''
        self.numbers = kwargs["numbers"]
        self.hl_continue = None
        self.curr_hl = None
        self.sels = []
        self.ignore_selections = kwargs["ignore_selections"]
        if self.ignore_selections:
            self.multi_select = False
        else:
            self.multi_select = self.check_sel() if kwargs["multi_select"] else False
        self.size = self.view.size()
        self.pt = 0
        self.end = 0
        self.curr_row = 0
        self.empty_space = None

        # Get color scheme
        if kwargs["color_scheme"] is not None:
            alt_scheme = kwargs["color_scheme"]
        else:
            alt_scheme = eh_settings.get("alternate_scheme", False)
        scheme_file = self.view.settings().get('color_scheme') if alt_scheme is False else alt_scheme
        self.csm = ColorSchemeMatcher(
            scheme_file,
            color_filter=(lambda x: ColorSchemeTweaker().tweak(x, kwargs["filter"]))
        )

        self.fground = self.csm.get_special_color('foreground', simulate_transparency=True)
        self.bground = self.csm.get_special_color('background', simulate_transparency=True)
        self.gfground = self.fground
        self.gbground = self.bground

    def setup_print_block(self, curr_sel, multi=False):
        """Determine start and end points and whether to parse whole file or selection."""

        if (
            self.ignore_selections or
            curr_sel is None or
            (
                not multi and
                (curr_sel.empty() or curr_sel.size() <= self.char_limit)
            )
        ):
            self.size = self.view.size()
            self.pt = 0
            self.end = 1
            self.curr_row = 1
        else:
            self.size = curr_sel.end()
            self.pt = curr_sel.begin()
            self.end = self.pt + 1
            self.curr_row = self.view.rowcol(self.pt)[0] + 1
        self.start_line = self.curr_row

        self.gutter_pad = len(str(self.view.rowcol(self.size)[0])) + 1

    def check_sel(self):
        """Check if multi-selection."""

        multi = False
        for sel in self.view.sel():
            if not sel.empty() and sel.size() >= self.char_limit:
                multi = True
                self.sels.append(sel)
        return multi

    def print_line(self, line, num):
        """Format a line for output."""
        if self.numbers:
            bbcode_line = NUMBERED_BBCODE_LINE % {
                "color": self.gfground,
                "line": str(num).rjust(self.gutter_pad),
                "code": line
            }
        else:
            bbcode_line = BBCODE_LINE % {"code": line}

        return bbcode_line

    def convert_view_to_bbcode(self, bbcode):
        """Begin converting the view to BBCode."""

        for line in self.view.split_by_newlines(sublime.Region(self.end, self.size)):
            self.empty_space = None
            self.size = line.end()
            line = self.convert_line_to_bbcode()
            bbcode.write(self.print_line(line, self.curr_row))
            self.curr_row += 1

    def repl(self, m, color):
        """Replace method to escape BBCode content."""

        return m.group(1) + (
            BBCODE_ESCAPE % {
                "color_open": color,
                "color_close": color,
                "content": m.group(2)
            }
        ) + m.group(3)

    def format_text(self, line, text, color, style):
        """Format the text for output."""

        text = text.replace('\t', ' ' * self.tab_size).replace('\n', '')
        if self.empty_space is not None:
            text = self.empty_space + text
            self.empty_space = None
        if text.strip(' ') == '':
            self.empty_space = text
        else:
            code = ""
            text = BBCODE_MATCH.sub(lambda m: self.repl(m, color), text)
            bold = False
            italic = False
            for s in style.split(' '):
                if s == "bold":
                    bold = True
                if s == "italic":
                    italic = True
            code += (BBCODE_CODE % {"color": color, "content": text})
            if italic:
                code = (BBCODE_ITALIC % {"content": code})
            if bold:
                code = (BBCODE_BOLD % {"content": code})
            line.append(code)

    def convert_line_to_bbcode(self):
        """Conver the line to BBCode."""

        line = []

        while self.end <= self.size:
            # Get text of like scope up to a highlight
            scope_name = self.view.scope_name(self.pt)
            while self.view.scope_name(self.end) == scope_name and self.end < self.size:
                self.end += 1
            color_match = self.csm.guess_color(scope_name)
            color = color_match.fg_simulated
            style = color_match.style

            region = sublime.Region(self.pt, self.end)
            # Normal text formatting
            text = self.view.substr(region)
            self.format_text(line, text, color, style)

            # Continue walking through line
            self.pt = self.end
            self.end = self.pt + 1

        # Join line segments
        return ''.join(line)

    def write_body(self, bbcode):
        """Write the body of the BBCode output."""
        bbcode.write(POST_START % {"bg_color": self.bground})

        # Convert view to HTML
        if self.multi_select:
            count = 0
            total = len(self.sels)
            for sel in self.sels:
                self.setup_print_block(sel, multi=True)
                self.convert_view_to_bbcode(bbcode)
                count += 1

                if count < total:
                    bbcode.write("\n" + (BBCODE_CODE % {"color": self.fground, "content": "..."}) + "\n\n")

        else:
            sels = self.view.sel()
            self.setup_print_block(sels[0] if len(sels) else None)
            self.convert_view_to_bbcode(bbcode)

        bbcode.write(POST_END)

    def run(self, **kwargs):
        """Run the command."""

        inputs = self.process_inputs(**kwargs)
        self.setup(**inputs)

        delete = False if inputs["view_open"] else True

        with tempfile.NamedTemporaryFile(mode='w+', delete=delete, suffix='.txt', encoding='utf-8') as bbcode:
            self.write_body(bbcode)
            if inputs["clipboard_copy"]:
                bbcode.seek(0)
                sublime.set_clipboard(bbcode.read())
                notify("BBCode copied to clipboard")

        if inputs["view_open"]:
            self.view.window().open_file(bbcode.name)
