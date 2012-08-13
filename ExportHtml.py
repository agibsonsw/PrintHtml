import sublime
import sublime_plugin
from os import path
import tempfile
import sys
import time
import webbrowser
import re
from HtmlAnnotations import get_annotations
import ExportHtmlLib.desktop as desktop

PACKAGE_SETTINGS = "ExportHtml.sublime-settings"

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
    td { padding: 0; }
    table { border: 0; margin: 0; padding: 0; }
    td div {
        float:left;
        width:100%%;
        white-space: -moz-pre-wrap; /* Mozilla */
        white-space: -hp-pre-wrap; /* HP printers */
        white-space: -o-pre-wrap; /* Opera 7 */
        white-space: -pre-wrap; /* Opera 4-6 */
        white-space: pre-wrap; /* CSS 2.1 */
        white-space: pre-line; /* CSS 3 (and 2.1 as well, actually) */
        word-wrap: break-word; /* IE */
    }
    .code_text { font: %(font_size)dpt "%(font_face)s", Consolas, Monospace; }
    .code_page { background-color: %(page_bg)s; }
    .code_gutter { display: %(display_mode)s; background-color: %(gutter_bg)s; }
    .code_line { padding-left: 10px; }
    span { border: 0; margin: 0; padding: 0; }
    span.bold { font-weight: bold; }
    span.italic { font-style: italic; }
    span.normal { font-style: normal; }
    span.underline { text-decoration:underline; }
    body { color: %(body_fg)s; }
    %(annotations)s
</style>
</head>
"""

CSS_ANNOTATIONS = \
"""
    .tooltip {
        border-bottom: 2px dotted %(dot_colour)s;
        outline: none;
        text-decoration: none;
        position: relative;
        color: black;
    }
    .tooltip div.annotation {
        border-radius: 5px 5px;
        -moz-border-radius: 5px;
        -webkit-border-radius: 5px;
        box-shadow: 5px 5px 5px rgba(0, 0, 0, 0.1);
        -webkit-box-shadow: 5px 5px rgba(0, 0, 0, 0.1);
        -moz-box-shadow: 5px 5px rgba(0, 0, 0, 0.1);
        white-space: -moz-pre-wrap; /* Mozilla */
        white-space: -hp-pre-wrap; /* HP printers */
        white-space: -o-pre-wrap; /* Opera 7 */
        white-space: -pre-wrap; /* Opera 4-6 */
        white-space: pre-wrap; /* CSS 2.1 */
        white-space: pre-line; /* CSS 3 (and 2.1 as well, actually) */
        word-wrap: break-word; /* IE */
        margin-left: -999em;
        position: absolute;
        padding: 0.8em 1em;
        background: lightyellow; border: solid black;
        font-family: Calibri, Tahoma, Geneva, sans-serif;
        font-size: 10pt;
        font-weight: bold;
        width: 250px;
        left: 1em;
        top: 2em;
        z-index: 99;
    }
    .tooltip:hover div.annotation {
        margin-left: 0;
    }

    div#comment_list {
        visibility: hidden;
        display: none;
        margin: auto auto;
        text-align: center;
        position: fixed;
        z-index: 99;
        left:0px;
        top: 0px;
    }
    div#comment_wrapper {
        max-height: 200px;
        overflow: auto;
        border: solid;
        -moz-border-radius: 5px;
        -webkit-border-radius: 5px;
        box-shadow: 5px 5px 5px rgba(0, 0, 0, 0.1);
        -webkit-box-shadow: 5px 5px rgba(0, 0, 0, 0.1);
        -moz-box-shadow: 5px 5px rgba(0, 0, 0, 0.1);
    }
    table#comment_table {
        border: thin solid; border-collapse: collapse;
        color: #000000; background-color: lightyellow; margin: auto auto;
    }
    div.table_footer { text-align:right; font-size: 8pt; font-weight: bold;}
    a.table_close { float: right; }
    a.table_close:link { color: black; text-decoration: None;}
    a.table_close:active { color: black; text-decoration: None;}
    a.table_close:visited { color: black; text-decoration: None;}
    a.table_close:hover { color: red; text-decoration: None;}
    table#comment_table th, table#comment_table td { border: thin solid; padding: 5px; }
    td.annotation_link { width: 60px; text-align: right; padding-right: 20px; }
    .annotation_comment { width: 500px; }
    div.annotation_comment { float: left; text-align: left; }

    * html a:hover { background: transparent; }
"""

ANNOTATE_OPEN = """<a class="tooltip" href="javascript:void(0)">%(code)s"""

ANNOTATE_CLOSE = """<div class="annotation">%(comment)s</div></a>"""

BODY_START = """<body class="code_page code_text">\n<pre class="code_page">"""

FILE_INFO = """<tr><td colspan="2"><div id="file_info"><span style="color: %(color)s">%(date_time)s %(file)s\n\n</span></div></td></tr>"""

TABLE_START = """<table cellspacing="0" cellpadding="0" class="code_page">"""

LINE = (
    '<tr>' +
    '<td valign="top" id="L_%(table)d_%(line_id)d" class="code_text code_gutter">' +
    '<span style="color: %(color)s;">%(line)s&nbsp;</span>' +
    '</td>' +
    '<td class="code_text code_line">' +
    '<div id="C_%(table)d_%(code_id)d">%(code)s\n</div>' +
    '</td>' +
    '</tr>'
)

CODE = """<span class="%(class)s" style="color:%(color)s">%(content)s</span>"""

HIGHLIGHTED_CODE = """<span class="%(class)s" style="background-color: %(highlight)s; color: %(color)s;">%(content)s</span>"""

TABLE_END = """</table>"""

ROW_START = """<tr><td>"""

ROW_END = """</td></tr>"""

DIVIDER = """<span style="color: %(color)s">\n...\n\n</span>"""

ANNOTATION_TBL_START = (
    '<div id="comment_list" style="display:none"><div id="comment_wrapper">' +
    '<table id="comment_table">' +
    '<tr><th>Line/Col</th><th>Comments' +
    '<a href="javascript:void(0)" class="table_close" onclick="toggle_comments();return false;">(close)</a>'
    '</th></tr>'
)

ANNOTATION_TBL_END = """</table></div></div>"""

ANNOTATION_ROW = (
    '<tr>' +
    '<td class="annotation_link">' +
    '<a href="javascript:void(0)" onclick="scroll_to_line(\'C_%(table)d_%(row)d\');return false;">%(link)s</a>' +
    '</td>' +
    '<td class="annotation_comment"><div class="annotation_comment">%(comment)s</div></td>' +
    '<tr>'
)

ANNOTATION_FOOTER = (
    '<tr><td colspan=2>' +
    '<div class="table_footer"><label>Position </label>' +
    '<select id="dock" size="1" onchange="dock_table();">' +
    '<option value="0" selected="selected">center</option>' +
    '<option value="1">top</option>' +
    '<option value="2">bottom</option>' +
    '<option value="3">left</option>' +
    '<option value="4">right</option>' +
    '<option value="5">top left</option>' +
    '<option value="6">top right</option>' +
    '<option value="7">bottom left</option>' +
    '<option value="8">bottom right</option>' +
    '</select>' +
    '</div>' +
    '</td></tr>'
)

BODY_END = """</pre>\n%(js)s\n</body>\n</html>\n"""

DOUBLE_CLICK_EVENTS = \
"""
<script type="text/javascript">
function double_click_events(e) {
    var evt = e ? e : window.event;
    if (evt.shiftKey && typeof toggle_gutter !== "undefined") {
        toggle_gutter();
    } else if (evt.altKey && typeof toggle_comments !== "undefined") {
        toggle_comments();
    }
}
document.getElementsByTagName('body')[0].ondblclick = function (e) { double_click_events(e); };
</script>
"""

TOGGLE_GUTTER = \
"""
<script type="text/javascript">
function toggle_gutter() {
    var i, j, mode, rows, r, tbls, rows, r,
        tables = %(tables)s;
    tbls  = document.getElementsByTagName('table');
    for (i = 1; i <= tables; i++) {
        rows = tbls[i].getElementsByTagName('tr');
        r = rows.length;
        for (j = 0; j < r; j++) {
            cels = rows[j].getElementsByTagName('td');
            if (mode == null) {
                if (cels[0].style.display == 'none') {
                    mode = 'table-cell';
                } else {
                    mode = 'none';
                }
            }
            cels[0].style.display = mode;
        }
    }
    if (typeof wrap_code !== "undefined" && mode != null) {
        if (mode == 'table-cell') {
            setTimeout("wrap_code(true)", 500)
        } else {
            setTimeout("wrap_code(false)", 500)
        }
    }
}
</script>
"""

PRINT = \
"""
<script type="text/javascript">
function page_print() {
    if (window.print) {
        window.print();
    }
}
document.getElementsByTagName('body')[0].onload = function (e) { page_print(); self.onload = null; }
</script>
"""

WRAP = \
"""
<script type="text/javascript">
function wrap_code(numbered) {
    var start, end, i, j, idx,
        pad = 10,
        ranges = [%(ranges)s],
        wrap_size = %(wrap_size)d,
        tables = %(tables)s,
        header = %(header)s;
    if (header) {
        document.getElementById("file_info").style.width = wrap_size + "px";
    }
    for (i = 1; i <= tables; i++) {
        idx = i - 1;
        start = ranges[idx][0];
        end = ranges[idx][1];
        if (numbered) {
            for(j = start; j < end; j++) {
                var width = document.getElementById("L_" + idx + "_" + j).offsetWidth;
                document.getElementById("C_" + idx + "_" + j).style.width = (wrap_size - width - pad) + "px";
            }
        } else {
            for(j = start; j < end; j++) {
                document.getElementById("C_" + idx + "_" + j).style.width = (wrap_size - pad) + "px";
            }
        }
    }
}
wrap_code(%(numbered)s)
</script>
"""

TOGGLE_COMMENTS = \
"""
<script type="text/javascript">
function toggle_comments() {
    var comments_div = document.getElementById('comment_list'),
        mode = comments_div.style.display;
    if (mode == 'none') {
        comments_div.style.display = 'block';
        position_table(comments_div)
    } else {
        comments_div.style.visibility = 'hidden'
        comments_div.style.display = 'none';
    }
}

function dock_table() {
    var comments_div = document.getElementById('comment_list');
    position_table(comments_div)
}

function position_table(el) {
    var x, y,
        sel = document.getElementById('dock'),
        option = sel.options[sel.selectedIndex].value;
    switch(option) {
        case "0": x = 'center'; y = 'center';  break;
        case "1": x = 'center'; y = 'top';     break;
        case "2": x = 'center'; y = 'bottom';  break;
        case "3": x = 'left';   y = 'center';  break;
        case "4": x = 'right';  y = 'center';  break;
        case "5": x = 'left';   y = 'top';     break;
        case "6": x = 'right';  y = 'top';     break;
        case "7": x = 'left';   y = 'bottom';  break;
        case "8": x = 'right';  y = 'bottom';  break;
        default: break;
    }
    setTimeout(function () {position_el.set(el, x, y); el.style.visibility = 'visible';}, 300)
}
</script>
"""

POSITION = \
"""
<script type="text/javascript">
var position_el = {
    center : function (el, dim) {
        var c = win_attr.get_center(),
            top    = (c.y - (el.offsetHeight/2)),
            left   = (c.x - (el.offsetWidth/2));
        if (dim == null || dim === 'y') el.style.top  = (top < 0)  ? 0 + 'px' : top  + 'px';
        if (dim == null || dim === 'x') el.style.left = (left < 0) ? 0 + 'px' : left + 'px';
    },

    set : function (el, x, y) {
        var left, top;

        if (typeof x === "undefined") x = null;
        if (typeof y === "undefined") y = null;

        if (y === 'center') {
            position_el.center(el, 'y');
        } else if (y === 'top') {
            el.style.top = 0 + 'px';
        } else if (y === 'bottom') {
            top = (win_attr.get_size('y') - (el.offsetHeight));
            el.style.top = (top < 0) ? 0 + 'px' : top + 'px';
        } else if (y.match(/^[\\d]+(%%|px|em|mm|cm|in|pt|pc)$/) != null) {
            el.style.top = y;
        }

        if (x === "center") {
            position_el.center(el, 'x');
        } else if (x === 'left') {
            el.style.left = 0 + 'px';
        } else if (x === 'right') {
            left = (win_attr.get_size('x') - (el.offsetWidth));
            el.style.left = (left < 0) ? 0 + 'px' : left + 'px';
        } else if (x.match(/^[\\d]+(%%|px|em|mm|cm|in|pt|pc)$/) != null) {
            el.style.left = x;
        }
    }
};

var win_attr = {
    get_center : function (dim) {
        var c = {
            'x' : (win_attr.get_size('x')/2),
            'y' : (win_attr.get_size('y')/2)
        };
        return ((dim) ? c[dim] : c);
    },

    get_size : function(dir) {
        dir = (dir === 'x') ? 'Width' : 'Height';
        return ((window['inner'+dir]) ?
            window['inner'+dir] :
            ((window.document.documentElement && window.document.documentElement['client'+dir]) ?
                window.document.documentElement['client'+dir] :
                window.document.body['client'+dir]
            )
        );
    }
};
</script>
"""

SCROLL_TO_LINE = \
"""
<script type="text/javascript">
function scroll_to_line(value) {
    var pos = 0,
        el = document.getElementById(value);
    window.scrollTo(0, 0);
    while(el) {
        pos += el.offsetTop;
        el = el.offsetParent;
    }
    pos -= win_attr.get('y');
    if (pos < 0) {
        pos = 0;
    }
    window.scrollTo(0, pos);
}
</script>
"""


class ExportHtmlPanelCommand(sublime_plugin.WindowCommand):
    def execute(self, value):
        if value >= 0:
            view = self.window.active_view()
            if view != None:
                ExportHtml(view).run(**self.args[value])

    def run(self):
        options = sublime.load_settings(PACKAGE_SETTINGS).get("html_panel", {})
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


class ExportHtmlCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        view = self.window.active_view()
        if view != None:
            ExportHtml(view).run(**kwargs)


class ExportHtml(object):
    def __init__(self, view):
        self.view = view

    def setup(
            self, numbers, highlight_selections, browser_print,
            color_scheme, wrap, multi_select, style_gutter,
            no_header, date_time_format, show_full_path
        ):
        path_packages = sublime.packages_path()

        # Get get general document preferences from sublime preferences
        eh_settings = sublime.load_settings(PACKAGE_SETTINGS)
        settings = sublime.load_settings('Preferences.sublime-settings')
        alternate_font_size = eh_settings.get("alternate_font_size", False)
        alternate_font_face = eh_settings.get("alternate_font_face", False)
        self.font_size = settings.get('font_size', 10) if alternate_font_size == False else alternate_font_size
        self.font_face = settings.get('font_face', 'Consolas') if alternate_font_face == False else alternate_font_face
        self.tab_size = settings.get('tab_size', 4)
        self.padd_top = settings.get('line_padding_top', 0)
        self.padd_bottom = settings.get('line_padding_bottom', 0)
        self.char_limit = int(eh_settings.get("valid_selection_size", 4))
        self.bground = ''
        self.fground = ''
        self.gbground = ''
        self.gfground = ''
        self.sbground = ''
        self.sfground = ''
        self.numbers = numbers
        self.date_time_format = date_time_format
        self.show_full_path = show_full_path
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
        self.tables = 0
        self.curr_annot = None
        self.curr_comment = None
        self.annotations = self.get_annotations()
        self.open_annot = False
        self.no_header = no_header
        self.annot_tbl = []

        fname = self.view.file_name()
        if fname == None or not path.exists(fname):
            fname = "Untitled"
        self.file_name = fname

        # Get color scheme
        if color_scheme != None:
            alt_scheme = color_scheme
        else:
            alt_scheme = eh_settings.get("alternate_scheme", False)
        scheme_file = settings.get('color_scheme') if alt_scheme == False else alt_scheme
        colour_scheme = path.normpath(scheme_file)
        plist_file = readPlist(path_packages + colour_scheme.replace('Packages', ''))
        colour_settings = plist_file["settings"][0]["settings"]

        # Get general theme colors from color scheme file
        self.bground = self.strip_transparency(colour_settings.get("background", '#FFFFFF'))
        self.fground = self.strip_transparency(colour_settings.get("foreground", '#000000'))
        self.sbground = self.strip_transparency(colour_settings.get("selection", self.fground))
        self.sfground = self.strip_transparency(colour_settings.get("selectionForeground", self.bground))
        self.gbground = self.strip_transparency(colour_settings.get("gutter", self.bground)) if style_gutter else self.bground
        self.gfground = self.strip_transparency(colour_settings.get("gutterForeground", self.fground)) if style_gutter else self.fground

        self.highlights = []
        if self.highlight_selections:
            for sel in self.view.sel():
                if not sel.empty():
                    self.highlights.append(sel)

        # Create scope colors mapping from color scheme file
        self.colours = {self.view.scope_name(self.end).split(' ')[0]: {"color": self.fground, "style": "normal"}}
        for item in plist_file["settings"]:
            scope = item.get('scope', None)
            colour = None
            style = []
            if 'scope' in item:
                scope = item['scope']
            if 'settings' in item:
                colour = item['settings'].get('foreground', None)
                if 'fontStyle' in item['settings']:
                    for s in item['settings']['fontStyle'].split(' '):
                        if s == "bold" or s == "italic":  # or s == "underline":
                            style.append(s)

            if len(style) == 0:
                style.append('normal')

            if scope != None and colour != None:
                self.colours[scope] = {"color": self.strip_transparency(colour), "style": ' '.join(style)}

    def strip_transparency(self, color):
        m = re.match("^(#[A-Fa-f\d]{6})([A-Fa-f\d]{2})", color)
        if m != None:
            color = m.group(1)
        return color

    def setup_print_block(self, curr_sel, multi=False):
        # Determine start and end points and whether to parse whole file or selection
        if not multi and (curr_sel.empty() or self.highlight_selections or curr_sel.size() <= self.char_limit):
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
        multi = False
        for sel in self.view.sel():
            if not sel.empty() and sel.size() >= self.char_limit:
                multi = True
                self.sels.append(sel)
        return multi

    def print_line(self, line, num):
        html_line = LINE % {
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
        the_style = None
        if the_key in self.colours:
            the_colour = self.colours[the_key]["color"]
            the_style = self.colours[the_key]["style"]
        else:
            best_match = 0
            for key in self.colours:
                if self.view.score_selector(self.pt, key) > best_match:
                    best_match = self.view.score_selector(self.pt, key)
                    the_colour = self.colours[key]["color"]
                    the_style = self.colours[key]["style"]
            self.colours[the_key] = {"color": the_colour, "style": the_style}
        return the_colour, the_style

    def write_header(self, the_html):
        header = CSS % {
            "title":     path.basename(self.file_name),
            "font_size": self.font_size,
            "font_face": self.font_face,
            "page_bg":   self.bground,
            "gutter_bg": self.gbground,
            "body_fg":   self.fground,
            "display_mode": ('table-cell' if self.numbers else 'none'),
            "annotations": (CSS_ANNOTATIONS % {"dot_colour": self.fground})
        }
        the_html.write(header)

    def convert_view_to_html(self, the_html):
        for line in self.view.split_by_newlines(sublime.Region(self.end, self.size)):
            self.size = line.end()
            line = self.convert_line_to_html(the_html)
            the_html.write(self.print_line(line, self.curr_row))
            self.curr_row += 1

    def html_encode(self, text):
        # Format text to HTML
        encode_table = {
            '&':  '&amp;',
            '>':  '&gt;',
            '<':  '&lt;',
            '\t': '&nbsp;' * self.tab_size,
            ' ':  '&nbsp;',
            '\n': ''
        }

        return ''.join(encode_table.get(c, c) for c in text).encode('ascii', 'xmlcharrefreplace')

    def get_annotations(self):
        annotations = get_annotations(self.view)
        comments = []
        for x in range(0, int(annotations["count"])):
            region = annotations["annotations"]["html_annotation_%d" % x]["region"]
            comments.append((region, annotations["annotations"]["html_annotation_%d" % x]["comment"]))
        comments.sort()
        return comments

    def annotate_text(self, line, the_colour, the_style, highlight=False):
        pre_text = None
        annot_text = None
        post_text = None
        start = None

        # Pretext Check
        if self.pt >= self.curr_annot.begin():
            # Region starts with an annotation
            start = self.pt
        else:
            # Region has text before annoation
            pre_text = self.html_encode(self.view.substr(sublime.Region(self.pt, self.curr_annot.begin())))
            start = self.curr_annot.begin()

        if self.end == self.curr_annot.end():
            # Region ends annotation
            annot_text = self.html_encode(self.view.substr(sublime.Region(start, self.end)))
            self.curr_annot = None
        elif self.end > self.curr_annot.end():
            # Region has text following annotation
            annot_text = self.html_encode(self.view.substr(sublime.Region(start, self.curr_annot.end())))
            post_text = self.html_encode(self.view.substr(sublime.Region(self.curr_annot.end(), self.end)))
            self.curr_annot = None
        else:
            # Region ends but annotation is not finished
            annot_text = self.html_encode(self.view.substr(sublime.Region(start, self.end)))
            self.curr_annot = sublime.Region(self.end, self.curr_annot.end())

        # Print the separate parts pre text, annotation, post text
        if pre_text != None:
            self.format_text(line, pre_text, the_colour, the_style, highlight=highlight)
        if annot_text != None:
            self.format_text(line, annot_text, the_colour, the_style, highlight=highlight, annotate=True)
            if self.curr_annot == None:
                self.curr_comment = None
        if post_text != None:
            self.format_text(line, post_text, the_colour, the_style, highlight=highlight)

    def add_annotation_table_entry(self, ):
        row, col = self.view.rowcol(self.annot_pt)
        self.annot_tbl.append(
            (
                self.tables, self.curr_row, "Line %d Col %d" % (row + 1, col + 1),
                self.curr_comment.encode('ascii', 'xmlcharrefreplace')
            )
        )
        self.annot_pt = None

    def format_text(self, line, text, the_colour, the_style, highlight=False, annotate=False):
        if highlight:
            # Highlighted code
            code = HIGHLIGHTED_CODE % {"highlight": self.sbground, "color": the_colour, "content": text, "class": the_style}
        else:
            # Normal code
            code = CODE % {"color": the_colour, "content": text, "class": the_style}
        if annotate:
            if self.curr_annot != None and not self.open_annot:
                # Open an annotation
                if self.annot_pt != None:
                    self.add_annotation_table_entry()
                code = ANNOTATE_OPEN % {"code": code}
                self.open_annot = True
            elif self.curr_annot == None:
                if self.open_annot:
                    # Close an annotation
                    code += ANNOTATE_CLOSE % {"comment": self.curr_comment.encode('ascii', 'xmlcharrefreplace')}
                    self.open_annot = False
                else:
                    # Do a complete annotation
                    if self.annot_pt != None:
                        self.add_annotation_table_entry()
                    code = (
                        ANNOTATE_OPEN % {"code": code} +
                        ANNOTATE_CLOSE % {"comment": self.curr_comment.encode('ascii', 'xmlcharrefreplace')}
                    )
        line.append(code)

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
                the_colour = self.sfground
                the_style = "normal"
            else:
                # Get text of like scope up to a highlight
                scope_name = self.view.scope_name(self.pt)
                while self.view.scope_name(self.end) == scope_name and self.end < self.size:
                    # Kick out if we hit a highlight region
                    if self.curr_hl != None and self.end == self.curr_hl.begin():
                        break
                    self.end += 1
                the_colour, the_style = self.guess_colour(scope_name)

            # Get new annotation
            if (self.curr_annot == None or self.curr_annot.end() < self.pt) and len(self.annotations):
                self.curr_annot, self.curr_comment = self.annotations.pop(0)
                self.annot_pt = self.curr_annot[0]
                while self.pt > self.curr_annot[1]:
                    if len(self.annotations):
                        self.curr_annot, self.curr_comment = self.annotations.pop(0)
                        self.annot_pt = self.curr_annot[0]
                    else:
                        self.curr_annot = None
                        self.curr_comment = None
                        break
                self.curr_annot = sublime.Region(self.curr_annot[0], self.curr_annot[1])

            region = sublime.Region(self.pt, self.end)
            if self.curr_annot != None and region.intersects(self.curr_annot):
                # Apply annotation within the text and format the text
                self.annotate_text(line, the_colour, the_style, highlight=hl_found)
            else:
                # Normal text formatting
                tidied_text = self.html_encode(self.view.substr(region))
                self.format_text(line, tidied_text, the_colour, the_style, highlight=hl_found)

            if hl_found:
                # Clear highlight flags and variables
                hl_found = False
                self.curr_hl = None

            # Continue walking through line
            self.pt = self.end
            self.end = self.pt + 1

        # Close annotation if open at end of line
        if self.open_annot:
            line.append(ANNOTATE_CLOSE % {"comment": self.curr_comment})
            self.open_annot = False

        # Join line segments
        return ''.join(line)

    def write_body(self, the_html):
        processed_rows = ""
        the_html.write(BODY_START)

        the_html.write(TABLE_START)
        if not self.no_header:
            # Write file name
            date_time = time.strftime(self.date_time_format, time.localtime())
            the_html.write(
                FILE_INFO % {
                    "color": self.fground,
                    "date_time": date_time,
                    "file": self.file_name if self.show_full_path else path.basename(self.file_name)
                }
            )

        the_html.write(ROW_START)
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
                    the_html.write(ROW_END)
                    the_html.write(ROW_START)
                    the_html.write(DIVIDER % {"color": self.fground})
                    the_html.write(ROW_END)
                    the_html.write(ROW_START)
                    the_html.write(TABLE_START)
        else:
            self.setup_print_block(self.view.sel()[0])
            processed_rows += "[" + str(self.curr_row) + ","
            self.convert_view_to_html(the_html)
            processed_rows += str(self.curr_row) + "],"
            self.tables += 1

        the_html.write(TABLE_END)
        the_html.write(ROW_END)
        the_html.write(TABLE_END)

        js_options = []
        if len(self.annot_tbl):
            self.add_comments_table(the_html)
            js_options.append(POSITION)
            js_options.append(TOGGLE_COMMENTS)
            js_options.append(SCROLL_TO_LINE)

        # Write javascript snippets
        if self.wrap:
            js_options.append(
                WRAP % {
                    "ranges":     processed_rows.rstrip(','),
                    "wrap_size": self.wrap,
                    "tables":    self.tables,
                    "numbered": ("true" if self.numbers else "false"),
                    "header": ("false" if self.no_header else "true")
                }
            )

        if self.browser_print:
            js_options.append(PRINT)

        js_options.append(TOGGLE_GUTTER % {"tables": self.tables})
        js_options.append(DOUBLE_CLICK_EVENTS)

        # Write empty line to allow copying of last line and line number without issue
        the_html.write(BODY_END % {"js": ''.join(js_options)})

    def add_comments_table(self, the_html):
        the_html.write(ANNOTATION_TBL_START)
        the_html.write(''.join([ANNOTATION_ROW % {"table": t, "row": r, "link": l, "comment": c} for t, r, l, c in self.annot_tbl]))
        the_html.write(ANNOTATION_FOOTER)
        the_html.write(ANNOTATION_TBL_END)

    def run(
        self, numbers=False, highlight_selections=False,
        clipboard_copy=False, browser_print=False, color_scheme=None,
        wrap=None, view_open=False, multi_select=False, style_gutter=True,
        no_header=False, date_time_format="%m/%d/%y %I:%M:%S", show_full_path=True
    ):
        self.setup(
            bool(numbers), bool(highlight_selections), bool(browser_print),
            color_scheme, wrap, bool(multi_select), bool(style_gutter),
            bool(no_header), date_time_format, bool(show_full_path)
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as the_html:
            self.write_header(the_html)
            self.write_body(the_html)
            if bool(clipboard_copy):
                the_html.seek(0)
                sublime.set_clipboard(the_html.read())
                sublime.status_message("Export to HTML: copied to clipboard")

        if bool(view_open):
            self.view.window().open_file(the_html.name)
        else:
            # Open in web browser; check return code, if failed try webbrowser
            status = desktop.open(the_html.name, status=True)
            if not status:
                webbrowser.open(the_html.name, new=2)
