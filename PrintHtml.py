import sublime
import sublime_plugin
from os import path
import tempfile
import desktop
import sys
import datetime

PACKAGE_SETTINGS = "PrintHtml.sublime-settings"

if sublime.platform() == "linux":
    # Try and load Linux Python2.6 lib.  Default path is for Ubuntu.
    linux_lib = sublime.load_settings(PACKAGE_SETTINGS).get("linux_python2.6_lib", "/usr/lib/python2.6/lib-dynload")
    if not linux_lib in sys.path and path.exists(linux_lib):
        sys.path.append(linux_lib)
from plistlib import readPlist

CSS = \
"""
<!DOCTYPE html>
<html>
<head>
<title>%s</title>
<style type="text/css">
    pre { border: 0; margin: 0; padding: 0;  }
    table { border: 0; margin: 0; padding: 0; }
    .code_text { font: %spt "%s", Consolas, Monospace; }
    .code_page { background-color: %s; }
    .code_gutter { background-color: %s;}
    span { border: 0; margin: 0; padding: 0; }
    body { color: %s; }
</style>
</head>
"""

BODY_START = """<body class="code_page code_text">\n<pre>"""

BODY_END = """<pre/>\n</body>\n</html>"""

TABLE_START = """<table cellspacing="0" cellpadding="0">"""

TABLE_END = """</table>"""

GUTTER_LINE = \
"""
<tr>
<td valign="top" class="code_text code_gutter"><span style="color: %s;">%s&nbsp;</span></td>
<td class="code_text">&nbsp;%s\n</td>
</tr>
"""

LINE = \
"""
<tr>
<td class="code_text">%s\n</td>
</tr>
"""

CODE = """<span style="color:%s">%s</span>"""

HIGHLIGHTED_CODE = """<span style="background-color: %s; color: %s;">%s</span>"""

FILE_INFO = """<span style="color: %s">%s%s\n\n</span>"""


class PrintHtmlCommand(sublime_plugin.TextCommand):
    def setup(self, numbers, highlight_selections):
        path_packages = sublime.packages_path()

        # Get get general document preferences from sublime preferences
        settings = sublime.load_settings('Preferences.sublime-settings')
        self.font_size = settings.get('font_size', 10)
        self.font_face = settings.get('font_face', 'Consolas')
        self.tab_size = settings.get('tab_size', 4)
        self.padd_top = settings.get('line_padding_top', 0)
        self.padd_bottom = settings.get('line_padding_bottom', 0)
        self.bground = ''
        self.fground = ''
        self.gbground = ''
        self.gfground = ''
        self.sbground = ''
        self.sfground = ''
        self.numbers = numbers
        self.highlight_selections = highlight_selections
        self.hl_continue = None
        self.curr_hl = None

        # Get color scheme
        alt_scheme = sublime.load_settings(PACKAGE_SETTINGS).get("alternate_scheme", False)
        scheme_file = settings.get('color_scheme') if alt_scheme == False else alt_scheme
        colour_scheme = path.normpath(scheme_file)
        plist_file = readPlist(path_packages + colour_scheme.replace('Packages', ''))
        colour_settings = plist_file["settings"][0]["settings"]

        # Get general theme colors from color scheme file
        if "background" in colour_settings:
            self.bground = colour_settings["background"]
        if 'foreground' in colour_settings:
            self.fground = colour_settings["foreground"]
        if 'gutter' in colour_settings:
            self.gbground = colour_settings["gutter"]
        if 'gutterForeground' in colour_settings:
            self.gfground = colour_settings["gutterForeground"]
        if 'selectionForeground' in colour_settings:
            self.sfground = colour_settings["selectionForeground"]
        if 'selection' in colour_settings:
            self.sbground = colour_settings["selection"]

        if self.bground == '':
            self.bground == '#FFFFFF'

        if self.fground == '':
            self.fground == '#000000'

        if self.gfground == '':
            self.gfground = self.fground

        if self.gbground == '':
            self.gbground = self.bground

        if self.sfground == '':
            self.gfground = self.bground

        if self.sbground == '':
            self.sbground = self.fground

        # Determine start and end points and whether to parse whole file or selection
        curr_sel = self.view.sel()[0]
        if curr_sel.empty() or self.highlight_selections or abs(curr_sel.end() - curr_sel.begin()) < 4:
            self.size = self.view.size()
            self.pt = 0
            self.end = 1
            self.curr_row = 1
            self.partial = False
        else:
            self.size = curr_sel.end()
            self.pt = curr_sel.begin()
            self.end = self.pt + 1
            self.curr_row = self.view.rowcol(self.pt)[0] + 1
            self.partial = True

        self.gutter_pad = len(str(self.view.rowcol(self.size)[0])) + 1

        self.highlights = []
        if self.highlight_selections:
            for sel in self.view.sel():
                if not sel.empty():
                    self.highlights.append(sel)

        # Create scope colors mapping from color scheme file
        self.colours = {self.view.scope_name(self.end).split(' ')[0]: self.fground}
        for item in plist_file["settings"]:
            scope = None
            colour = None
            if 'scope' in item:
                scope = item['scope']
            if 'settings' in item and 'foreground' in item['settings']:
                colour = item['settings']['foreground']

            if scope != None and colour != None:
                self.colours[scope] = colour

    def print_line(self, line, num=None):
        if num == None:
            html_line = LINE % line
        else:
            html_line = GUTTER_LINE % (self.gfground, str(num).rjust(self.gutter_pad).replace(" ", '&nbsp;'), line)

        return html_line

    def guess_colour(self, the_key):
        the_colour = None
        if the_key in self.colours:
            the_colour = self.colours[the_key]
        else:
            best_match = 0
            for key in self.colours:
                if self.view.score_selector(self.pt, key) > best_match:
                    best_match = self.view.score_selector(self.pt, key)
                    the_colour = self.colours[key]
            self.colours[the_key] = the_colour
        return the_colour

    def write_header(self, the_html):
        header = CSS % (
            path.basename(the_html.name),  # Title
            str(self.font_size),           # Code font size
            self.font_face,                # Code font face
            self.bground,                  # Page background color
            self.gbground,                 # Gutter background color
            self.fground                   # Default text color
        )
        the_html.write(header)

    def convert_view_to_html(self, the_html):
        for line in self.view.split_by_newlines(sublime.Region(self.end, self.size)):
            self.size = line.end()
            line = self.convert_line_to_html(the_html)
            if self.numbers:
                the_html.write(self.print_line(line, self.curr_row))
            else:
                the_html.write(self.print_line(line))
            self.curr_row += 1

    def convert_line_to_html(self, the_html):
        line = []
        hl_found = False

        # Continue highlight form last line
        if self.hl_continue != None:
            self.curr_hl = self.hl_continue
            self.hl_continue = None

        while self.end <= self.size:
            # Get next highlight region
            if self.highlight_selections and self.curr_hl == None and len(self.highlights) > 0:
                self.curr_hl = self.highlights.pop(0)

            # See if we are starting a highlight region
            if self.curr_hl != None and self.pt == self.curr_hl.begin():
                hl_found = True
                if self.curr_hl.end() <= self.size:
                    self.end = self.curr_hl.end()
                else:
                    # Highlight is bigger than line, mark for continuation
                    self.end = self.size
                    self.hl_continue = sublime.Region(self.size + 1, self.curr_hl.end())
            else:
                # Get text of like scope up to a highlight
                scope_name = self.view.scope_name(self.pt)
                while self.view.scope_name(self.end) == scope_name and self.end <= self.size:
                    # Kick out if we hit a highlight region
                    if self.curr_hl != None and self.end == self.curr_hl.begin():
                        break
                    self.end += 1
                the_colour = self.guess_colour(scope_name)

            # Format text to HTML
            html_encode_table = {
                '&':  '&amp;',
                '>':  '&gt;',
                '<':  '&lt;',
                '\t': '&nbsp;' * self.tab_size,
                ' ':  '&nbsp;',
                '\n': ''
            }
            tidied_text = ''.join(html_encode_table.get(c, c) for c in self.view.substr(sublime.Region(self.pt, self.end)))

            # Highlight span if needed
            if hl_found:
                line.append(HIGHLIGHTED_CODE % (self.sbground, self.sfground, tidied_text))
                hl_found = False
                self.curr_hl = None
            else:
                line.append(CODE % (the_colour, tidied_text))

            self.pt = self.end
            self.end = self.pt + 1
        return ''.join(line)

    def write_body(self, the_html):
        the_html.write(BODY_START)

        # Write file name
        fname = self.view.file_name()
        if fname == None or not path.exists(fname):
            fname = "Untitled"
        date_time = datetime.datetime.now().strftime("%m/%d/%y %I:%M:%S ")
        the_html.write(FILE_INFO % (self.fground, date_time, fname))

        the_html.write(TABLE_START)

        # Convert view to HTML
        self.convert_view_to_html(the_html)

        the_html.write(TABLE_END)

        # Write empty line to allow copying of last line and line number without issue
        the_html.write(BODY_END)

    def run(self, edit, numbers=False, highlight_selections=False, clipboard=False):
        self.setup(numbers, highlight_selections)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as the_html:
            self.write_header(the_html)
            self.write_body(the_html)
            if clipboard:
                the_html.seek(0)
                sublime.set_clipboard(the_html.read())

        # Open in web browser
        desktop.open(the_html.name)
