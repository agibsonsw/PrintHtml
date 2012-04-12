import sublime
import sublime_plugin
from os import path
import tempfile
import desktop
import re
import sys

PACKAGE_SETTINGS = "PrintHtml.sublime-settings"

if sublime.platform() == "linux":
	# Try and load Linux Python2.6 lib.  Default path is for Ubuntu.
	linux_lib = sublime.load_settings(PACKAGE_SETTINGS).get("linux_python2.6_lib", 
		"/usr/lib/python2.6/lib-dynload")
	if not linux_lib in sys.path and path.exists(linux_lib):
		sys.path.append(linux_lib)
from plistlib import readPlist

class PrintHtmlCommand(sublime_plugin.TextCommand):
	def setup(self, numbers):
		path_packages = sublime.packages_path()

		# Get general document preferences from sublime preferences
		settings = sublime.load_settings('Preferences.sublime-settings')
		self.font_size = settings.get('font_size') or 10
		self.font_face = settings.get('font_face') or 'Consolas'
		self.tab_size = settings.get('tab_size') or 4
		self.padd_top = settings.get('line_padding_top') or 0
		self.padd_bottom = settings.get('line_padding_bottom') or 0
		self.numbers = numbers

		# Get color scheme
		alt_scheme = sublime.load_settings(PACKAGE_SETTINGS).get("alternate_scheme", False)
		scheme_file = settings.get('color_scheme') if alt_scheme == False else alt_scheme
		colour_scheme = path.normpath(scheme_file)
		plist_file = readPlist(path_packages + colour_scheme.replace('Packages', ''))
		colour_settings = plist_file["settings"][0]["settings"]

		# Get general theme colors from color scheme file
		self.bground = colour_settings["background"] if "background" \
			in colour_settings else '#FFFFFF'
		self.fground = colour_settings["foreground"] if "foreground" \
			in colour_settings else '#000000'
		self.gfground = colour_settings["gutterForeground"] if "gutterForeground" \
			in colour_settings else self.fground

		# Determine start and end points and whether to parse whole file or selection
		curr_sel = self.view.sel()[0]
		if curr_sel.empty() or abs(curr_sel.end() - curr_sel.begin()) < 4:
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
			temp_line = ''
			while self.end <= self.line_end:
				scope_name = self.view.scope_name(self.pt)
				while (self.end <= self.line_end and (self.view.scope_name(self.end) == scope_name 
						or (self.view.substr(self.end) in ['\t', ' ', '']))):
					self.end += 1

				the_colour = self.guess_colour(scope_name.strip())				
				tidied_text = self.view.substr(sublime.Region(self.pt, self.end))

				tidied_text = tidied_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
				tidied_text = tidied_text.replace('\t', '&nbsp;' * self.tab_size).strip('\r\n')
				if len(tidied_text):
					without_init_sp = tidied_text.lstrip(' ')
					init_spaces = len(tidied_text) - len(without_init_sp)
					if init_spaces:
						tidied_text = ('&nbsp;' * init_spaces) + without_init_sp
					temp_line += '<span style=\"color:' + the_colour + '\">'
					temp_line += tidied_text + '</span>'
				self.pt = self.end
				self.end = self.pt + 1
			if temp_line != '':
				the_html.write(temp_line)
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
		# included empty line (br) to allow copying of last line and line number without issue

	def run(self, edit, numbers):
		self.setup(numbers)

		with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as the_html:
			self.write_header(the_html)
			self.write_body(the_html)

		# Open in web browser
		desktop.open(the_html.name)
