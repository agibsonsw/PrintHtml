import sublime, sublime_plugin
from os import path
import tempfile, desktop, re, sys

PACKAGE_SETTINGS = "PrintHtml.sublime-settings"

if sublime.platform() == "linux":
	# Try and load Linux Python2.6 lib.  Default path is for Ubuntu.
	linux_lib = sublime.load_settings(PACKAGE_SETTINGS).get("linux_python2.6_lib", 
		"/usr/lib/python2.6/lib-dynload")
	if not linux_lib in sys.path and path.exists(linux_lib):
		sys.path.append(linux_lib)
from plistlib import readPlist

CSS_BODY = \
"""body { color: %(fcolor)s; background-color: %(bcolor)s; font: %(fsize)dpt '%(fface)s', Consolas, Monospace; } """

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
	left: 1em;
	top: 2em;
	z-index: 99;
}
.tooltip:hover span.comment {
	margin-left: 0;
}
.tooltip span.linenumber {
	display: none;
}
* html a:hover { background: transparent; }
"""

COMMENTS_LIST = \
"""
<script type="text/javascript">
	function listComments() {
		var the_list = '<html><head><style>';
		the_list += "%(styling)s";
		the_list += 'span.nos { display: inline-block; width: 30px; text-align:right; padding-right: 10px; }'
		the_list += '</style></head><body>';
		the_list += '<p>Comments for: %(fname)s</p>';
		var the_comments = document.getElementsByClassName('comment');
		for (i=0; i < the_comments.length; i++) {
			the_list += '<p>Line no:<span class=nos>' + the_comments[i].nextSibling.firstChild.nodeValue + '</span>';
			the_list += the_comments[i].firstChild.nodeValue + '</p>';
		}
		the_list += '<br/><p>Refresh the page to go back.</p>';
		the_list += '</body></html>';
		document.write(the_list);
	}
</script>
"""

class CommentHtmlCommand(sublime_plugin.TextCommand):
	sensible_word = re.compile(r"""[a-zA-Z_]{1}[a-zA-Z_0-9]+""")
	def get_metrics(self, view):
		try:
			curr_id = view.id()
			curr_sel = view.sel()[0]
			curr_pt = curr_sel.begin()
			word_region = view.word(curr_pt)
			curr_word = view.substr(word_region)
			word_pt = word_region.begin()
		except:
			return {}
		return locals()							# shouldn't really do this :)

	def check_word(self, the_word):
		unsuitable = 0; error_msg = ''
		if len(the_word) < 2:
			return (1, "Cursor should be within a word (2 characters min).")
		elif not re.match(self.sensible_word, the_word):
			return (2, "Cursor needs to be within a \'sensible\' word, " \
				+ "and cannot start with a number: " + the_word)
		else:
			return (unsuitable, error_msg)		# word is okay

	def run(self, edit):
		metrics = self.get_metrics(self.view)
		if not len(metrics):
			sublime.status_message('Unable to read word at cursor.')
		else:
			unsuitable, error_msg = self.check_word(metrics['curr_word'])
			if unsuitable:
				sublime.status_message(error_msg)
		self.more_comments = True
		self.curr_comment = ''
		if not hasattr(self.view, 'vcomments'):
			self.view.vcomments = {}
		else:
			try:
				if self.view.vcomments.has_key(metrics['word_pt']):
					_, self.curr_comment = self.view.vcomments[metrics['word_pt']]
			except:
				pass
		self.show_comment_panel(self.curr_comment)

	def select_comments(self):
		try:
			self.view.erase_regions("comments")
			self.view.erase_regions("comment_errs")
		except:
			pass
		if not len(self.view.vcomments):
			sublime.status_message('No comments to select.')
			return
		sels = self.view.sel()
		sels.clear()
		for key_pt in sorted(self.view.vcomments.iterkeys()):
			curr_wd_region = self.view.word(key_pt)
			curr_wd = self.view.substr(curr_wd_region)
			prev_wd, prev_comment = self.view.vcomments[key_pt]
			if curr_wd == prev_wd:
				sels.add(curr_wd_region)
			else:
				print "Commented word was \'%s\' now \'%s\' comment: %s" % (prev_wd, curr_wd, prev_comment)
				del self.view.vcomments[key_pt]
		if not len(self.view.vcomments):
			sublime.status_message('Comments no longer in original positions - deleted.')

	def highlight_comments(self):
		try:
			self.view.erase_regions("comments")
			self.view.erase_regions("comment_errs")
		except:
			pass
		if not len(self.view.vcomments):
			sublime.status_message('No comments to highlight.')
		else:
			sels = self.view.sel()
			sels.clear()
			comment_regions = []
			comment_errors = []
			for key_pt in sorted(self.view.vcomments.iterkeys()):
				curr_wd_region = self.view.word(key_pt)
				curr_wd = self.view.substr(curr_wd_region)
				prev_wd, prev_comment = self.view.vcomments[key_pt]
				if curr_wd == prev_wd:
					comment_regions.append(curr_wd_region)
				else:
					print "Commented word was \'%s\' now \'%s\' comment: %s" % (prev_wd, curr_wd, prev_comment)
					comment_errors.append(curr_wd_region)
			if len(comment_regions):
				self.view.add_regions("comments", comment_regions, "comment", "")
			if len(comment_errors):
				self.view.add_regions("comment_errs", comment_errors, "invalid", "")

	def remove_highlights(self):
		if not len(self.view.vcomments):
			sublime.status_message('There are no remaining comments.')
		try:
			self.view.erase_regions("comments")
			self.view.erase_regions("comment_errs")
			sublime.status_message('Removed comment highlighting.')
		except:
			pass

	def add_comment(self, text):
		metrics = self.get_metrics(self.view)
		if not len(metrics):
			sublime.status_message('Unable to read word at cursor.')
			return
		unsuitable, error_msg = self.check_word(metrics['curr_word'])
		if unsuitable:
			sublime.status_message(error_msg)
		else:									# add the comment to the dictionary
			comment = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
			comment = comment.replace('\t', '&nbsp;' * 4).strip()
			self.view.vcomments[metrics['word_pt']] = (metrics['curr_word'], comment)

	def delete_comment(self):
		if not len(self.view.vcomments):
			sublime.status_message('No comments to delete.')
			return
		metrics = self.get_metrics(self.view)
		if not len(metrics):
			sublime.status_message('Unable to read word at cursor.')
			return
		unsuitable, error_msg = self.check_word(metrics['curr_word'])
		if unsuitable:
			sublime.status_message(error_msg)
		else:									# delete the comment from the dictionary
			if self.view.vcomments.has_key(metrics['word_pt']):
				del self.view.vcomments[metrics['word_pt']]
				sublime.status_message('Comment at cursor deleted.')
			else:
				sublime.status_message('No comment found at cursor.')

	def delete_all_comments(self):
		if len(self.view.vcomments):
			self.view.vcomments = {}
			sublime.status_message('All comments deleted.')
		else:
			sublime.status_message('No comments to delete.')
		try:
			self.view.erase_regions("comments")
			self.view.erase_regions("comment_errs")
		except:
			pass

	def push_comment_down(self):
		if not len(self.view.vcomments):
			sublime.status_message('There are no comments for the current view.')
			return ''
		metrics = self.get_metrics(self.view)
		if not len(metrics):
			sublime.status_message('Unable to read word at cursor.')
			return ''
		unsuitable, error_msg = self.check_word(metrics['curr_word'])
		if unsuitable:
			sublime.status_message(error_msg)
		else:									# push this comment downwards
			prev_pt = metrics['word_pt']
			if self.view.vcomments.has_key(prev_pt):
				prev_wd, prev_comment = self.view.vcomments[prev_pt]
				new_region = self.view.find(prev_wd, prev_pt + 1, sublime.LITERAL)
				if new_region:
					self.view.vcomments[new_region.begin()] = (prev_wd, prev_comment)
					del self.view.vcomments[prev_pt]
					new_comment_line, _ = self.view.rowcol(new_region.begin())
					sublime.status_message('Comment pushed downwards to line ' + str(new_comment_line + 1))
					sels = self.view.sel()
					sels.clear()
					self.view.sel().add(new_region)
					self.view.show(new_region)
					return prev_comment
				else:
					sublime.status_message('The current text does not occur further down.')
			else:
				sublime.status_message('No comment found at cursor.')
		return ''

	def push_comment_up(self):
		if not len(self.view.vcomments):
			sublime.status_message('There are no comments for the current view.')
			return ''
		metrics = self.get_metrics(self.view)
		if not len(metrics):
			sublime.status_message('Unable to read word at cursor.')
			return ''
		unsuitable, error_msg = self.check_word(metrics['curr_word'])
		if unsuitable:
			sublime.status_message(error_msg)
		else:									# push this comment upwards
			prev_pt = metrics['word_pt']
			if self.view.vcomments.has_key(prev_pt):
				prev_wd, prev_comment = self.view.vcomments[prev_pt]
				new_regions = (r for r in reversed(self.view.find_all(prev_wd, sublime.LITERAL)) if r.begin() < prev_pt)
				# (a generator expression)
				try:
					new_region = new_regions.next()
				except StopIteration:
					new_region = None
				if new_region:
					self.view.vcomments[new_region.begin()] = (prev_wd, prev_comment)
					del self.view.vcomments[prev_pt]
					new_comment_line, _ = self.view.rowcol(new_region.begin())
					sublime.status_message('Comment pushed upwards to line ' + str(new_comment_line + 1))
					sels = self.view.sel()
					sels.clear()
					self.view.sel().add(new_region)
					self.view.show(new_region)
					return prev_comment
				else:
					sublime.status_message('The current text does not occur further up.')
			else:
				sublime.status_message('No comment found at cursor.')
		return ''

	def process_commentry(self, text, caller_id):
		self.more_comments = False		# assume there is a problem with commentary
		display_text = ''				# the text to display in the panel, if shown again
		if not len(text):
			sublime.status_message('Comment has no text.')
			return
		window = sublime.active_window()
		view = window.active_view() if window != None else None
		if view is None:
			sublime.status_message('No active view.')
			return
		elif view.id() != caller_id:
			sublime.status_message('Not the same view - cancelled.')
			return
		self.more_comments = True		# okay to continue displaying the panel
		comment_command = text.strip().upper()
		if comment_command in ('SEL', 'SELECT'):						# select commented words
			self.select_comments()
		elif comment_command in ('HIGH', 'HIGHLIGHT'):					# highlight all comments
			self.highlight_comments()
		elif comment_command in ('REMOVE', 'REMOVE HIGHLIGHT', 'REMOVE HIGHLIGHTS'):	# remove highlights
			self.remove_highlights()
		elif comment_command in ('DEL', 'DELETE'):						# delete comment at cursor
			self.delete_comment()
		elif comment_command in ('DEL ALL', 'DELALL', 'DELETE ALL', 'DELETEALL'):	# delete all comments
			self.delete_all_comments()
		elif comment_command in ('PUSH', 'PUSH D', 'PUSH DOWN', 'PUSHDOWN'):		# push this comment downwards
			display_text = self.push_comment_down()
		elif comment_command in ('PUSH U', 'PUSH UP', 'PUSHUP'):		# push this comment upwards
			display_text = self.push_comment_up()
		else:															# add new comment at cursor
			self.add_comment(text)
		self.show_again(display_text)									# the "commments" panel

	def show_comment_panel(self, existing_comment):
		caller_id = self.view.id()
		self.view.window().show_input_panel('Comment>', existing_comment, \
			lambda txt: self.process_commentry(txt, caller_id), None, self.hide_it)

	def show_again(self, display_text = ''):			# the input panel
		if self.more_comments:
			self.show_comment_panel(display_text)

	def hide_it(self):				# the input panel
		self.more_comments = False

class PrintHtmlCommand(sublime_plugin.TextCommand):
	def setup(self, numbers):
		path_packages = sublime.packages_path()
		if not hasattr(self.view, 'vcomments'):
			self.view.vcomments = {}
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
		self.fname = self.view.file_name()
		if self.fname == None or not path.exists(self.fname):
			self.fname = "Untitled"
		the_html.write('<!DOCTYPE html>\n')
		the_html.write('<html>\n<head>\n<meta charset=\"UTF-8\">\n')
		the_html.write('<title>' + path.basename(the_html.name) + '</title>\n')

		the_html.write('<style type=\"text/css\">\n')
		self.vid = self.view.id()
		self.comments = False
		if len(self.view.vcomments):
			self.comments = True
			the_html.write((CSS_COMMENTS % { "dot_colour": self.fground }).encode('utf-8', 
				'xmlcharrefreplace') + '\n')

		the_html.write('span { display: inline; border: 0; margin: 0; padding: 0; }\n')
		if not self.numbers:
			the_html.write('ol { list-style-type: none; list-style-position: inside; ' 
				+ 'margin: 0px; padding: 0px; }\n')
		the_html.write('li { color: ' + self.gfground + '; margin-top: ' +
			str(self.padd_top) + 'pt; margin-bottom: ' + str(self.padd_bottom) + 'pt; }\n')

		the_html.write((CSS_BODY % {"fcolor": self.fground, "bcolor": self.bground, 
					"fsize": self.font_size, "fface": self.font_face}).encode('utf-8', 'xmlcharrefreplace'))
		the_html.write('</style>\n')

		if self.comments:
			the_html.write((COMMENTS_LIST % {"fname": (self.fname).replace('\\', '\\\\'), 
				"styling": (CSS_BODY % {"fcolor": self.fground, "bcolor": self.bground,
					"fsize": self.font_size, "fface": self.font_face})}).encode('utf-8', 'xmlcharrefreplace'))
		the_html.write('</head>\n')

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
						if x in self.view.vcomments:
							the_word, the_comment = self.view.vcomments[x]
							# has the pt moved since the comment was created?
							if self.view.substr(self.view.word(x)) != the_word:
								the_comment = None				# no longer pts at the same word
								del self.view.vcomments[x]		# delete the comment/ dict entry
							break

				tidied_text = tidied_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
				tidied_text = tidied_text.replace('\t', '&nbsp;' * self.tab_size).strip('\r\n')
				text_len = len(tidied_text)						# re-check the length
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
						the_span += '<span class=\"comment\">' + the_comment + '</span>'
						line_no, _ = self.view.rowcol(self.pt - 1)
						the_span += '<span class=\"linenumber\">' + str(line_no + 1) + '</a>'
					html_line += the_span
				the_html.write(html_line.encode('utf-8', 'xmlcharrefreplace'))
				temp_line[:] = []
				the_html.write('</li>\n<li>')

	def write_body(self, the_html):
		the_html.write('<body>\n')

		# Write file name (set in write_header)
		the_html.write('<span style=\"color:' + self.fground + '\">' + self.fname + '</span>\n')
		if self.comments:
			the_html.write('<br/>Show list of comments: ')
			the_html.write('<input type=\"checkbox\" name=\"ckbComments\" value=\"1\" onclick=\"listComments()\">\n')
		if self.numbers:
			the_html.write('<ol>\n<li value="%d">' % self.curr_row)  # use code's line numbering
		else:
			the_html.write('<ol>\n<li>')

		# Convert view to HTML
		self.convert_view_to_html(the_html)

		the_html.write('</li>\n</ol>\n<br/>\n')
		# included empty line (br) to allow copying of last line without issue
		if self.comments:
			# an option to list the comments could be added
			pass
		the_html.write('</body>\n</html>')

	def run(self, edit, numbers):
		self.setup(numbers)
		with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as the_html:
			self.write_header(the_html)
			self.write_body(the_html)

		# Open in web browser
		desktop.open(the_html.name)