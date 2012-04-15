import sublime, sublime_plugin
from os import path
import tempfile, desktop, re, sys

PACKAGE_SETTINGS = "PrintHtml.sublime-settings"
gCommentry = {}

if sublime.platform() == "linux":
	# Try and load Linux Python2.6 lib.  Default path is for Ubuntu.
	linux_lib = sublime.load_settings(PACKAGE_SETTINGS).get("linux_python2.6_lib", 
		"/usr/lib/python2.6/lib-dynload")
	if not linux_lib in sys.path and path.exists(linux_lib):
		sys.path.append(linux_lib)
from plistlib import readPlist

CSS_COMMENTS = \
"""
.tooltip {
	border-bottom: 1px dotted %(dot_colour)s;
	outline: none;
	text-decoration: none;
	position: relative;
}
.tooltip span.comment {
	border-radius: 5px 5px;
	-moz-border-radius: 5px;
	-webkit-border-radius: 5px;
	box-shadow: 5px 5px 5px rgba(0, 0, 0, 0.1);
	-webkit-box-shadow: 5px 5px rgba(0, 0, 0, 0.1);
	-moz-box-shadow: 5px 5px rgba(0, 0, 0, 0.1);
	margin-left: -999em;
	position: absolute;
	padding: 0.8em 1em;
	background: #FFFFAA; border: 1px solid #FFAD33;
	font-family: Calibri, Tahoma, Geneva, sans-serif;
	font-size: 10pt;
	font-weight: bold;
	width: 250px;
}
.tooltip:hover span.comment {
	position: absolute;
	left: 1em;
	top: 2em;
	z-index: 99;
	margin-left: 0;
}
* html a:hover { background: transparent; }
"""

class CommentHtmlCommand(sublime_plugin.WindowCommand):
	def get_metrics(self):
		curr_view = self.window.active_view()
		if curr_view is None:
			return { 'curr_view': None }		# must always check this first!
		curr_id = curr_view.id()
		curr_sel = curr_view.sel()[0]
		curr_pt = curr_sel.begin()
		word_region = curr_view.word(curr_pt)
		curr_word = curr_view.substr(word_region)
		word_pt = word_region.begin()
		return locals()							# shouldn't really do this :)

	def run(self):
		metrics = self.get_metrics()
		if metrics['curr_view'] is None:
			sublime.status_message('A view/tab must be active.')
			return
		if len(metrics['curr_word']) < 2:
			sublime.status_message('Cursor should be within a word.')
		self.more_comments = True
		self.the_input = self.window.show_input_panel('Comment>', '', self.on_done, None, self.hide_it)

	def on_done(self, text):
		metrics = self.get_metrics()
		if metrics['curr_view'] is None:
			sublime.status_message('No active view to add comment to.')
			return
		if len(metrics['curr_word']) < 2:
			sublime.status_message('Cursor should be within a word.')
			return
		if not metrics['curr_word'].isalpha():
			sublime.status_message('Cursor needs to be within a fully alphabetic word.')
			return
		if not len(text):
			sublime.status_message('Comment has no text.')
			return
		comment = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
		comment = comment.replace('\t', '&nbsp;' * 4).strip()
		if metrics['curr_id'] not in gCommentry:
			gCommentry[metrics['curr_id']] = {}
		gCommentry[metrics['curr_id']][metrics['word_pt']] = (metrics['curr_word'], comment)
		if self.more_comments:
			sublime.set_timeout(self.show_again, 200)

	def show_again(self):			# the input panel
		if self.more_comments:
			self.the_input = self.window.show_input_panel('ESC to finish>', '', self.on_done,
				None, self.hide_it)

	def hide_it(self):				# the input panel
		self.more_comments = False

class PrintHtmlCommand(sublime_plugin.WindowCommand):
	def setup(self, numbers):
		path_packages = sublime.packages_path()

		# Get general document preferences from sublime preferences
		settings = sublime.load_settings('Preferences.sublime-settings')
		self.font_size = settings.get('font_size', 10)
		self.font_face = settings.get('font_face', 'Consolas')
		self.tab_size = settings.get('tab_size', 4)
		self.padd_top = settings.get('line_padding_top', 0)
		self.padd_bottom = settings.get('line_padding_bottom', 0)
		self.numbers = numbers

		# Get color scheme
		alt_scheme = sublime.load_settings(PACKAGE_SETTINGS).get("alternate_scheme", False)
		scheme_file = settings.get('color_scheme') if alt_scheme == False else alt_scheme
		colour_scheme = path.normpath(scheme_file)
		plist_file = readPlist(path_packages + colour_scheme.replace('Packages', ''))
		colour_settings = plist_file["settings"][0]["settings"]

		# Get general theme colors from color scheme file
		self.bground = colour_settings.get('background', '#FFFFFF')
		self.fground = colour_settings.get('foreground', '#000000')
		self.gfground = colour_settings.get('gutterForeground', self.fground)

		# Determine start and end points and whether to parse whole file or selection
		curr_sel = self.view.sel()[0]
		if curr_sel.empty() or abs(curr_sel.end() - curr_sel.begin()) < 4:
			self.size = self.view.size()
			self.pt = 0
			self.end = 1
			self.curr_row = 1
			self.partial = False			# print entire view
		else:
			self.size = curr_sel.end()
			self.pt = curr_sel.begin()
			self.end = self.pt + 1
			self.curr_row = self.view.rowcol(self.pt)[0] + 1
			self.partial = True				# printing selection

		# Create scope colour-mapping from colour-scheme file
		self.colours = { self.view.scope_name(self.end).split(' ')[0]: self.fground }
		for item in plist_file["settings"]:
			scope = item.get('scope', None)
			if 'settings' in item and 'foreground' in item['settings']:
				colour = item['settings']['foreground']
			else:
				colour = None
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
		return the_colour or self.fground

	def write_header(self, the_html):
		the_html.write('<!DOCTYPE html>\n')
		the_html.write('<html>\n<head>\n<meta charset=\"UTF-8\">\n')
		the_html.write('<title>' + path.basename(the_html.name) + '</title>\n')

		the_html.write('<style type=\"text/css\">\n')
		self.vid = self.view.id()
		self.comments = False
		if self.vid in gCommentry:
			self.comments = True
			the_html.write((CSS_COMMENTS % { "dot_colour": self.fground }).encode('utf-8', 
				'xmlcharrefreplace') + '\n')	
		the_html.write('\tspan { display: inline; border: 0; margin: 0; padding: 0; }\n')
		if not self.numbers:
			the_html.write('\tol { list-style-type: none; list-style-position: inside; ' 
				+ 'margin: 0px; padding: 0px; }\n')
		the_html.write('\tli { color: ' + self.gfground + '; margin-top: ' +
			str(self.padd_top) + 'pt; margin-bottom: ' + str(self.padd_bottom) + 'pt; }\n')

		the_html.write('\tbody { \n\t')
		the_html.write('color: ' + self.fground + '; background-color: ' + self.bground + ';\n\t')
		the_html.write('font: ' + str(self.font_size) + 'pt \"' + self.font_face + '\", Consolas, Monospace;')
		the_html.write('}\n')					# close body-css

		the_html.write('</style>\n</head>\n')

	def convert_view_to_html(self, the_html):
		for line in self.view.split_by_newlines(sublime.Region(self.pt, self.size)):
			self.pt = line.begin(); self.end = self.pt + 1
			if line.empty():
				the_html.write('<br/></li>\n<li>')
				continue
			self.line_end = line.end()
			temp_line = []

			while self.end <= self.line_end:
				scope_name = self.view.scope_name(self.pt)
				while (self.end < self.line_end and (self.view.scope_name(self.end) == scope_name 
						or (self.view.substr(self.end) in ('\t', ' ', '')))):
					self.end += 1

				region = sublime.Region(self.pt, self.end)
				if region.empty():
					self.pt = self.end
					self.end = self.pt + 1
					continue

				tidied_text = self.view.substr(region)
				text_len = len(tidied_text)
				the_colour = self.guess_colour(scope_name.strip())
				the_comment = None

				if text_len and self.comments:
					for x in range(self.pt, self.end):
						if x in gCommentry[self.vid]:
							the_word, the_comment = gCommentry[self.vid][x]
							# has the pt moved since the comment was created?
							if self.view.substr(self.view.word(x)) != the_word:
								the_comment = None				# no longer pts at the same word
								del gCommentry[self.vid][x]		# delete the comment/ dict entry
							break

				tidied_text = tidied_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
				tidied_text = tidied_text.replace('\t', '&nbsp;' * self.tab_size).strip('\r\n')
				text_len = len(tidied_text)			# re-check the length
				if text_len:
					init_spaces = text_len - len(tidied_text.lstrip(' '))
					if init_spaces:
						tidied_text = (init_spaces * '&nbsp;') + tidied_text.lstrip(' ')
					temp_line.append((the_colour, tidied_text, the_comment))
				self.pt = self.end
				self.end = self.pt + 1

			if len(temp_line):
				html_line = ''
				for (the_colour, tidied_text, the_comment) in temp_line:
					the_span = '<span style=\"color:' + the_colour + '\">' + tidied_text + '</span>'
					if the_comment is not None:
						the_span = '<a class=\"tooltip\" href=\"#\">' + the_span
						the_span += '<span class=\"comment\">' + the_comment + '</span></a>'
					html_line += the_span
				the_html.write(html_line.encode('utf-8', 'xmlcharrefreplace'))
				temp_line[:] = []
			the_html.write('</li>\n<li>')

	def write_body(self, the_html):
		the_html.write('<body>\n')

		# Write file name
		fname = self.view.file_name()
		if fname == None or not path.exists(fname):
			fname = "Untitled"
		the_html.write('<span style=\"color:' + self.fground + '\">' + fname + '</span>\n')
		if self.numbers:
			the_html.write('<ol>\n<li value="%d">' % self.curr_row)  # use code's line numbering
		else:
			the_html.write('<ol>\n<li>')

		# Convert view to HTML
		self.convert_view_to_html(the_html)

		the_html.write('</li>\n</ol>\n<br/>\n</body>\n</html>')
		# included empty line (br) to allow copying of last line without issue

	def run(self, numbers):
		self.view = self.window.active_view()
		if self.view is None:
			sublime.status_message('A view/tab must be active.')
		else:
			self.setup(numbers)
			with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as the_html:
				self.write_header(the_html)
				self.write_body(the_html)

			# Open in web browser
			desktop.open(the_html.name)