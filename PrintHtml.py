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

# HTML Code
CSS = \
"""
<!DOCTYPE html>
<html>
<head>
<title>%(title)s</title>
<style type="text/css">
    pre { border: 0; margin: 0; padding: 0; }
    table { border: 0; margin: 0; padding: 0; }
    div { float:left; width:100%%; word-wrap: break-word; }
    .code_text { font: %(font_size)dpt "%(font_face)s", Consolas, Monospace; }
    .code_page { background-color: %(page_bg)s; }
    .code_gutter { background-color: %(gutter_bg)s;}
    span { border: 0; margin: 0; padding: 0; }
    body { color: %(body_fg)s; }
</style>
</head>
"""

BODY_START = """<body class="code_page code_text">\n<pre class="code_page">"""

FILE_INFO = """<div id="file_info"><span style="color: %(color)s">%(date_time)s %(file)s\n\n</span></div>"""

TABLE_START = """<table cellspacing="0" cellpadding="0" class="code_page">"""

GUTTER_LINE = \
"""
<tr>
<td valign="top" id="L_%(table)d_%(line_id)d" class="code_text code_gutter"><span style="color: %(color)s;">%(line)s&nbsp;</span></td>
<td class="code_text"><div id="C_%(table)d_%(code_id)d">&nbsp;%(code)s\n</div></td>
</tr>
"""

LINE = \
"""
<tr>
<td class="code_text"><div id="C_%(table)d_%(code_id)d">%(code)s\n</td>
</tr>
"""

CODE = """<span style="color:%(color)s">%(content)s</span>"""

HIGHLIGHTED_CODE = """<span style="background-color: %(highlight)s; color: %(color)s;">%(content)s</span>"""

TABLE_END = """</table>"""

DIVIDER = """<span style="color: %(color)s">\n...\n\n</span>"""

BODY_END = """<pre/>\n%(js)s\n</body>\n</html>"""

PRINT = \
"""
<script type="text/javascript">
if (window.print) {
    window.print();
}
</script>
"""

WRAP = \
"""
<script type="text/javascript">
var ranges = [%(ranges)s];
var start;
var end;
var wrap_size = %(wrap_size)d;
var numbered = %(numbered)s;
var tables = %(tables)s;
var i;
var j;
document.getElementById("file_info").style.width = wrap_size + "px";
for (i = 0; i < tables; i++) {
    start = ranges[i][0]
    end = ranges[i][1]
    if (numbered) {
        for(j = start; j < end; j++) {
            var width = document.getElementById("L_" + i + "_" + j).offsetWidth;
            document.getElementById("C_" + i + "_" + j).style.width = (wrap_size - width) + "px";
        }
    } else {
        for(j = start; j < end; j++) {
            document.getElementById("C_" + i + "_" + j).style.width = wrap_size + "px";
        }
    }
}
</script>
"""


class PrintHtmlPanelCommand(sublime_plugin.WindowCommand):
    def execute(self, value):
        if value >= 0:
            view = self.window.active_view()
            if view != None:
                PrintHtml(view).run(**self.args[value])

    def run(self):
        options = sublime.load_settings(PACKAGE_SETTINGS).get("print_panel", {})
        menu = []
        self.args = []
        for opt in options:
            k, v = opt.items()[0]
            menu.append(k)
            self.args.append(v)

        if len(menu):
            self.window.show_quick_panel(
                menu,
                self.execute
            )


class PrintHtmlCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        view = self.window.active_view()
        if view != None:
            PrintHtml(view).run(**kwargs)


class PrintHtml(object):
    def __init__(self, view):
        self.view = view

    def setup(self, numbers, highlight_selections, browser_print, color_scheme, wrap, multi_select, style_gutter):
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
        self.browser_print = browser_print
        self.wrap = int(wrap) if wrap != None and int(wrap) > 0 else False
        self.hl_continue = None
        self.curr_hl = None
        self.sels = []
        self.multi_select = self.check_sel() if multi_select and not highlight_selections else False
        self.size = self.view.size()
        self.pt = 0
        self.end = 0
        self.curr_row = 0
        self.partial = False
        self.tables = 0

        # Get color scheme
        if color_scheme != None:
            alt_scheme = color_scheme
        else:
            alt_scheme = sublime.load_settings(PACKAGE_SETTINGS).get("alternate_scheme", False)
        scheme_file = settings.get('color_scheme') if alt_scheme == False else alt_scheme
        colour_scheme = path.normpath(scheme_file)
        plist_file = readPlist(path_packages + colour_scheme.replace('Packages', ''))
        colour_settings = plist_file["settings"][0]["settings"]

        # Get general theme colors from color scheme file
        self.bground = colour_settings.get("background", '#FFFFFF')
        self.fground = colour_settings.get("foreground", '#000000')
        self.sbground = colour_settings.get("selection", self.fground)
        self.sfground = colour_settings.get("selectionForeground", self.bground)
        self.gbground = colour_settings.get("gutter", self.bground) if style_gutter else self.bground
        self.gfground = colour_settings.get("gutterForeground", self.fground) if style_gutter else self.fground

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

    def setup_print_block(self, curr_sel, multi=False):
        # Determine start and end points and whether to parse whole file or selection
        if not multi and (curr_sel.empty() or self.highlight_selections or abs(curr_sel.end() - curr_sel.begin()) < 4):
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
        self.start_line = self.curr_row

        self.gutter_pad = len(str(self.view.rowcol(self.size)[0])) + 1

    def check_sel(self):
        multi = False
        for sel in self.view.sel():
            if not sel.empty():
                multi = True
                self.sels.append(sel)
        return multi

    def print_line(self, line, num):
        if not self.numbers:
            html_line = LINE % {
                "code_id": num,
                "code": line,
                "table": self.tables
            }
        else:
            html_line = GUTTER_LINE % {
                "line_id": num,
                "color": self.gfground,
                "line": str(num).rjust(self.gutter_pad).replace(" ", '&nbsp;'),
                "code_id": num,
                "code": line,
                "table": self.tables
            }

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
        header = CSS % {
            "title":     path.basename(the_html.name),
            "font_size": self.font_size,
            "font_face": self.font_face,
            "page_bg":   self.bground,
            "gutter_bg": self.gbground,
            "body_fg":   self.fground
        }
        the_html.write(header)

    def convert_view_to_html(self, the_html):
        for line in self.view.split_by_newlines(sublime.Region(self.end, self.size)):
            self.size = line.end()
            line = self.convert_line_to_html(the_html)
            the_html.write(self.print_line(line, self.curr_row))
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
                line.append(HIGHLIGHTED_CODE % {"highlight": self.sbground, "color": self.sfground, "content": tidied_text})
                hl_found = False
                self.curr_hl = None
            else:
                line.append(CODE % {"color": the_colour, "content": tidied_text})

            self.pt = self.end
            self.end = self.pt + 1
        return ''.join(line)

    def write_body(self, the_html):
        processed_rows = ""
        the_html.write(BODY_START)

        # Write file name
        fname = self.view.file_name()
        if fname == None or not path.exists(fname):
            fname = "Untitled"
        date_time = datetime.datetime.now().strftime("%m/%d/%y %I:%M:%S")
        the_html.write(FILE_INFO % {"color": self.fground, "date_time": date_time, "file": fname})

        the_html.write(TABLE_START)

        # Convert view to HTML
        if self.multi_select:
            count = 0
            total = len(self.sels)
            for sel in self.sels:
                self.setup_print_block(sel, multi=True)
                processed_rows += "[" + str(self.curr_row) + ","
                self.convert_view_to_html(the_html)
                count += 1
                self.tables = count
                processed_rows += str(self.curr_row) + "],"

                if count < total:
                    the_html.write(TABLE_END)
                    the_html.write(DIVIDER % {"color": self.fground})
                    the_html.write(TABLE_START)
        else:
            self.setup_print_block(self.view.sel()[0])
            processed_rows += "[" + str(self.curr_row) + ","
            self.convert_view_to_html(the_html)
            processed_rows += str(self.curr_row) + "],"
            self.tables += 1

        js_options = []
        if self.wrap:
            js_options.append(
                WRAP % {
                    "ranges":     processed_rows,
                    "wrap_size": self.wrap,
                    "numbered":  ("true" if self.numbers else "false"),
                    "tables":    self.tables
                }
            )

        if self.browser_print:
            js_options.append(PRINT)

        the_html.write(TABLE_END)

        # Write empty line to allow copying of last line and line number without issue
        the_html.write(BODY_END % {"js": ''.join(js_options)})

    def run(
        self, numbers=False, highlight_selections=False,
        clipboard_copy=False, browser_print=False, color_scheme=None,
        wrap=None, view_open=False, multi_select=False, style_gutter=True
    ):
        self.setup(numbers, highlight_selections, browser_print, color_scheme, wrap, multi_select, style_gutter)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as the_html:
            self.write_header(the_html)
            self.write_body(the_html)
            if clipboard_copy:
                the_html.seek(0)
                sublime.set_clipboard(the_html.read())

        if view_open:
            self.view.window().open_file(the_html.name)
        else:
            # Open in web browser
            desktop.open(the_html.name)
