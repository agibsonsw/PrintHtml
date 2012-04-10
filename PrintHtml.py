import sublime
import sublime_plugin
from xml.dom import minidom
from os import path
import tempfile
import desktop
import re


class PrintHtmlCommand(sublime_plugin.TextCommand):
    def setup(self, numbers):
        path_packages = sublime.packages_path()

        # Get get general document preferences from sublime preferences
        settings = sublime.load_settings('Preferences.sublime-settings')
        self.font_size = settings.get('font_size') or 10
        self.font_face = settings.get('font_face') or 'Consolas'
        self.tab_size = settings.get('tab_size') or 4
        self.padd_top = settings.get('line_padding_top') or 0
        self.padd_bottom = settings.get('line_padding_bottom') or 0
        self.bground = ''
        self.fground = ''
        self.gfground = ''
        self.numbers = numbers

        # Get color scheme
        alt_scheme = sublime.load_settings("PrintHtml.sublime-settings").get("alternate_scheme", False)
        scheme_file = settings.get('color_scheme') if alt_scheme == False else alt_scheme
        colour_scheme = path.normpath(scheme_file)
        doc = minidom.parse(path_packages + colour_scheme.replace('Packages', ''))
        the_array = doc.getElementsByTagName('dict')[0].getElementsByTagName('array')[0]
        colour_settings = the_array.getElementsByTagName('dict')[0]

        # Get general theme colors from color scheme file
        for key_tag in colour_settings.getElementsByTagName('key'):
            try:
                if key_tag.firstChild.data.strip() == 'background':
                    self.bground = key_tag.nextSibling.nextSibling.firstChild.data.strip()
                elif key_tag.firstChild.data.strip() == 'foreground':
                    self.fground = key_tag.nextSibling.nextSibling.firstChild.data.strip()
                elif key_tag.firstChild.data.strip() == 'gutterForeground':
                    self.gfground = key_tag.nextSibling.nextSibling.firstChild.data.strip()
            except:
                pass

        if self.gfground == '':
            self.gfground = self.fground

        # Determine start and end points and whether to parse whole file or selection
        curr_sel = self.view.sel()[0]
        if curr_sel.empty() or abs(curr_sel.end() - curr_sel.begin()) < 4:
            self.size = self.view.size()
            self.pt = 0
            self.end = 1
            self.partial = False
        else:
            self.size = curr_sel.end()
            self.pt = curr_sel.begin()
            self.end = self.pt + 1
            self.curr_row = self.view.rowcol(self.pt)[0] + 1
            self.partial = True

        # Create scope colors mapping from color scheme file
        self.colours = {self.view.scope_name(self.end).split(' ')[0]: self.fground}
        dict_items = the_array.getElementsByTagName('dict')[1:]
        for item in dict_items:
            scope = None
            colour = None
            for key_tag in item.getElementsByTagName('key'):
                try:
                    if key_tag.firstChild.data.strip() == 'scope':
                        scope = key_tag.nextSibling.nextSibling.firstChild.data.strip()
                    elif key_tag.firstChild.data.strip() == 'foreground':
                        colour = key_tag.nextSibling.nextSibling.firstChild.data.strip()
                except:
                    pass
            if scope != None and colour != None:
                self.colours[scope] = colour

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
        the_html.write('<!DOCTYPE html>\n')
        the_html.write('<html>\n<head>\n<title>' + path.basename(the_html.name) + '</title>\n')
        the_html.write('<style type=\"text/css\">\n')
        the_html.write('\tspan { display: inline; border: 0; margin: 0; padding: 0; }\n')
        if not self.numbers:
            the_html.write('\tol { list-style-type: none; }\n')
        the_html.write('\tli { color: ' + self.gfground  + '; margin-top: ' +
            str(self.padd_top) + 'pt; margin-bottom: ' + str(self.padd_bottom) + 'pt; }\n')
        the_html.write('\tbody { ')
        if self.fground != '':
            the_html.write('color: ' + self.fground + ';')
        if self.bground != '':
            the_html.write(' background-color: ' + self.bground + ';')
        the_html.write(' font: ' + str(self.font_size) + 'pt \"' + self.font_face + '\", Consolas, Monospace;')
        the_html.write('\n}\n')
        the_html.write('</style>\n</head>\n')

    def convert_view_to_html(self, the_html):
        while self.end <= self.size:
            scope_name = self.view.scope_name(self.pt)
            while self.view.scope_name(self.end) == scope_name and self.end <= self.size:
                self.end += 1
            region = sublime.Region(self.pt, self.end)

            the_colour = self.guess_colour(scope_name.strip())

            tidied_text = self.view.substr(region)
            tidied_text = tidied_text.replace('&', '&amp;')
            tidied_text = tidied_text.replace('<', '&lt;')
            tidied_text = tidied_text.replace('>', '&gt;')
            tidied_text = tidied_text.replace('\t', '&nbsp;' * self.tab_size)
            tidied_text = tidied_text.replace(' ', '&nbsp;')
            m = re.match("^(.*)\r?\n((\r?\n)+)$", tidied_text) if not self.numbers else None
            new_li = '</span></li>\n<li><span style=\"color:' + the_colour + '\">'
            if m != None:
                new_lines = ''.join(["<li><br/></li>" for c in str(m.group(2)) if c == "\n"])
                tidied_text = m.group(1) + "</span></li>\n" + new_lines + '<li><span>' + new_li
            else:
                tidied_text = tidied_text.replace('\n', new_li)
            the_html.write('<span style=\"color:' + the_colour + '\">')
            the_html.write(tidied_text + '</span>')
            self.pt = self.end
            self.end = self.pt + 1

    def write_body(self, the_html):
        the_html.write('<body>\n')
        if self.numbers and self.partial:
            the_html.write('<ol>\n<li value="%d">' % self.curr_row)  # use code's line numbering
        else:
            the_html.write('<ol>\n<li>')

        # Convert view to HTML
        self.convert_view_to_html(the_html)

        the_html.write('</li>\n</ol>')
        the_html.write('\n</body>\n</html>')

    def run(self, edit, numbers):
        self.setup(numbers)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as the_html:
            self.write_header(the_html)
            self.write_body(the_html)

        # Open in web browser
        desktop.open(the_html.name)
