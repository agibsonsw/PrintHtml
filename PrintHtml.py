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

HEADER = \
"""<!DOCTYPE html>
<html>
<head>
	<meta charset="UTF-8">
	<title>%(fname)s</title>
"""

CSS_MAIN = \
"""
	<style type="text/css">
	body { color: %(fcolor)s; background-color: %(bcolor)s; font: %(fsize)dpt '%(fface)s', Consolas, Monospace; }
	#preCode { border: 0; margin: 0; padding: 0; font: %(fsize)dpt '%(fface)s', Consolas, Monospace; }
	span { color: %(fcolor)s; background-color: %(bcolor)s; display: inline; border: 0; margin: 0; padding: 0; }
	span:hover { outline: 1px solid red; }
	* html a:hover { background: transparent; }
"""

CSS_COMMENTS = \
"""
	.tooltip {
		border-bottom: 1px dotted %(dot_colour)s;
		outline: none; text-decoration: none;
		position: relative;
	}
	.tooltip .comment {
		border-radius: 5px 5px;
		-moz-border-radius: 5px;
		-webkit-border-radius: 5px;
		box-shadow: 5px 5px 5px rgba(0, 0, 0, 0.1);
		-webkit-box-shadow: 5px 5px rgba(0, 0, 0, 0.1);
		-moz-box-shadow: 5px 5px rgba(0, 0, 0, 0.1);

		position: absolute; z-index: 99;
		width: 250px; left: 1em; top: 2em;

		margin-left: -999em;

		padding: 0.8em 1em;
		color: blue; background: #FFFFAA; border: 1px solid #FFAD33;
		font-family: Calibri, Tahoma, Geneva, sans-serif;
		font-size: %(fsize)dpt; font-weight: bold;
	}
	.tooltip:hover .comment { margin-left: 0pt; }

	#divComments { display: none; height: 400px; width: 500px; overflow: auto; margin: 0; }
	#divComments.inpage { position: static; }
	#divComments.inpage #bottom_row { display: none; }
	#divComments.overlay { position: fixed; z-index: 99; height: 400px; right:50px;
		top: 100px; bottom: auto; left: auto; }
	#divComments.overlay_bl { position: fixed; z-index: 99; height: 200px; right: auto;
		top: auto; bottom: 50px; left: 50px; overflow-y: scroll; }
	#divComments.overlay #bottom_row, #divComments.overlay_bl #bottom_row { display: table-row; }
	#tblComments {
		box-shadow: 5px 5px 5px rgba(0, 0, 0, 0.1);
		-webkit-box-shadow: 5px 5px rgba(0, 0, 0, 0.1);
		-moz-box-shadow: 5px 5px rgba(0, 0, 0, 0.1);
		border-collapse: collapse; margin: 0;
		font-family: Calibri, Tahoma, Geneva, sans-serif;
		color: #000000; background-color: lightyellow;
	}
	#tblComments th, #tblComments td { border: thin solid; padding: 5px; }
	td.nos { width: 50px; text-align: right; padding-right: 10px !important; }
	td.cmts { min-width: 400px; max-width: 600px; }
"""

CKBs_COMMENTS = \
"""
<p>Show table of comments:<input type="checkbox" name="ckbComments" id="ckbComments" value="1" onclick="listComments()">&nbsp;
Overlay table of comments:<input type="checkbox" name="ckbOverlay" id="ckbOverlay" value="1" onclick="overlayComments()">&nbsp;
Show/hide comments (disables hover):<input type="checkbox" name="ckbToggle" id="ckbToggle" value="1" onclick="toggleComments()"></p>
"""

SCOPED = \
"""<span>%(t_text)s</span>"""
SCOPEDCOLOR = \
"""<span style="color:%(colour)s;">%(t_text)s</span>"""
SCOPEDCOMMENT = \
"""<a class="tooltip" href="#" onclick="return false;">%(scoped)s<span class="comment">%(comment)s</span></a>"""

JS_TIDYSPACES = \
"""
<script type="text/javascript">
	function tidySpaces() {
		var olCode, spans, i, span_textnode, span_text, span_next, offLeft, newLeft;
		var olCode = document.getElementById('olCode');
		var spans = olCode.getElementsByTagName('span');
		for (i = 0; i < spans.length; i++) {
			if ( spans[i].previousSibling ) {
				span_textnode = spans[i].firstChild;
				span_text = span_textnode.data;
				tidied = span_text.replace(/\s{2,}$/,'');
				if (span_text.length && (span_text.length > tidied.length)) {
					if ( spans[i].nextSibling ) {
						span_next = spans[i].nextSibling;
						offLeft = span_next.offsetLeft;
						newLeft = (parseInt(offLeft / 50)) * 50 + 50;
						spans[i].nextSibling.style.paddingLeft = (newLeft - offLeft) + 'px';
					}
				}
			}
		}
	}
</script>
"""

JS_COMMENTS = \
"""
<script type="text/javascript">
	function listComments() {
		var comments_div = document.getElementById('divComments');
		if (!comments_div.style.display || comments_div.style.display == 'none') {
			if (!comments_div.className || comments_div.className == 'inpage')
				document.getElementById('preCode').style.display = 'none';
			comments_div.style.display = 'block';
		}
		else {
			comments_div.style.display = 'none';
			document.getElementById('preCode').style.display = 'block';
			document.getElementById('ckbComments').checked = false;
		}
	}
	function overlayComments() {
		var comments_div = document.getElementById('divComments');

		document.getElementById('preCode').style.display = 'block';
		if (document.getElementById('ckbOverlay').checked) {
			comments_div.className = (document.getElementById('ckbBottom').checked) ? 'overlay_bl' : 'overlay';
		}
		else {
			comments_div.className = 'inpage';
		}
	}
	function tableToBottom() {
		document.getElementById('divComments').className = 
			(document.getElementById('ckbBottom').checked) ? 'overlay_bl' : 'overlay';
	}
	function toggleComments() {
		var comments, newMargin, i;

		if (document.getElementsByClassName) {
			comments = document.getElementsByClassName('comment');
		}
		else if (document.querySelectorAll) {
			comments = document.querySelectorAll('.comment');
		}
		else {
			return false;
		}
		newMargin = (document.getElementById('ckbToggle').checked) ? '0pt' : '-999em';
		for (i = 0; i < comments.length; i++) {
			comments[i].style.marginLeft = newMargin;
		}
	}
	function gotoLine(line_no) {
		var code_list = document.getElementById('olCode');
		var code_lines = code_list.getElementsByTagName('li');

		// scroll the line(-5) into view (so it's not right at the top)
		line_no = (line_no - 5 + 1) * (line_no - 5 + 1 > 0);
		code_lines[line_no].scrollIntoView();
		return false;
	}
	function addComment(e) {
		var span_target, awrapper, new_comment, comment_text;

		if (!e) e = window.event;
		span_target = e.target || e.srcElement;
		if (span_target.nodeName != 'SPAN' || span_target.className == 'comment') {
			return false;
		}
		awrapper = document.createElement('a');
		awrapper.href = '#';
		awrapper.onclick = function () { return false; };
		awrapper.className = 'tooltip';
		new_comment = document.createElement('textarea');
		new_comment.className = 'comment';
		new_comment.style.marginLeft = '0pt';
		new_comment.style.backgroundColor = 'yellow';
		comment_text = document.createTextNode('New comment text');
		new_comment.appendChild(comment_text);
		awrapper.appendChild(span_target.cloneNode(true));
		awrapper.appendChild(new_comment);
		span_target.parentNode.replaceChild(awrapper, span_target);
		return false;
	}
	window.onload = function () {
		document.getElementById('olCode').ondblclick = addComment;
	};
</script>
"""

COMMENTS_TBLHEAD = \
"""
<div id="divComments" class="inpage">
<table id="tblComments"> 
	<tr><th>Line</th><th>The Comment</th><tr>
"""
COMMENTS_TBLROW = \
"""
	<tr><td class="nos"><a href="#" onclick="gotoLine(%(line_adj)s);return false;">%(line_no)s</a></td>
	<td class="cmts">%(comment)s</td></tr>
"""
COMMENTS_TBLEND = \
"""
	<tr id="bottom_row"><td colspan="2" style=\"font-size:smaller; text-align:right;\"><a href="#top">Top</a>&nbsp;&nbsp;
	<a href="#" onclick="listComments();return false;">Close</a>&nbsp;&nbsp;
	Position: bottom-left <input type="checkbox" name="ckbBottom" id="ckbBottom" value="1" onclick="tableToBottom()"></td>
	</tr>
</table>
</div>
"""

class CommentHtmlCommand(sublime_plugin.TextCommand):
	sensible_word = re.compile(r"""[a-zA-Z_]{1}[a-zA-Z_0-9]+""")

	def get_metrics(self, view):				# return word and point(s) at cursor position
		try:
			curr_id = view.id()
			curr_sel = view.sel()[0]
			curr_pt = curr_sel.begin()
			word_region = view.word(curr_pt)
			curr_word = view.substr(word_region)
			word_pt = word_region.begin()
			word_line, word_col = view.rowcol(word_pt)
		except:
			return {}
		return locals()

	def get_comment(self):					# return comment-text at cursor, or False
		if not hasattr(self.view, 'vcomments'): return ''
		metrics = self.get_metrics(self.view)
		if not len(metrics): return ''
		if self.view.vcomments.has_key(metrics['word_pt']):
			_, curr_comment, curr_line = self.view.vcomments[metrics['word_pt']]
			return curr_comment
		else:
			return ''

	def run(self, edit):
		self.more_comments = True
		self.just_added = False						# haven't just added a new comment
		if not hasattr(self.view, 'vcomments'):
			self.view.vcomments = {}
			curr_comment = ''
		else:
			curr_comment = self.get_comment()
		self.show_comment_panel(curr_comment)		# show panel and comment at cursor

	def select_comments(self):				# will clear highlight regions and current selection
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
		eov = self.view.size()
		for key_pt in sorted(self.view.vcomments.iterkeys()):
			prev_wd, prev_comment, prev_line = self.view.vcomments[key_pt]
			if key_pt >= eov:						# delete comments past end of the view
				del self.view.vcomments[key_pt]
				print "Comment past end-of-view deleted: %s (was line %d)" % (prev_comment, prev_line)
				continue
			curr_wd_region = self.view.word(key_pt)
			curr_wd = self.view.substr(curr_wd_region)
			if curr_wd == prev_wd:
				sels.add(curr_wd_region)
				if len(sels) == 1: self.view.show(curr_wd_region)
			else:
				curr_line, _ = self.view.rowcol(curr_wd_region.begin())
				print "DELETED: Commented word was \'%s\' on line %d now \'%s\' on line %d comment: %s" \
					% (prev_wd, prev_line, curr_wd, curr_line, prev_comment)
				del self.view.vcomments[key_pt]				# delete mis-positioned comment
		if not len(self.view.vcomments):
			sublime.status_message('Comments no longer in original positions - deleted.')

	def select_next(self, direction = 'down'):
		if not len(self.view.vcomments):
			sublime.status_message('No comments to select.')
			return
		sels = self.view.sel()
		curr_pt = sels[0].begin()
		if direction == 'down':
			sorted_pts = (key_pt for key_pt in sorted(self.view.vcomments.iterkeys()) if key_pt > curr_pt)
		else:
			sorted_pts = (key_pt for key_pt in reversed(sorted(self.view.vcomments.iterkeys())) if key_pt < curr_pt)
		try:
			next_pt = sorted_pts.next()
		except StopIteration:
			next_pt = None
		if next_pt:
			next_wd, next_comment, next_line = self.view.vcomments[next_pt]
			if next_pt >= self.view.size():						# next comment is beyond the view-size
				sublime.status_message("Comment is past end-of-view - use \'recover\' command: %s (was line %d)" \
					% (next_comment, next_line))
				print "Comment past end-of-view: %s (was line %d)" % (next_comment, next_line)
				return
			sels.clear()
			next_wd_region = self.view.word(next_pt)
			curr_wd = self.view.substr(next_wd_region)
			if curr_wd != next_wd: 
				next_wd_begin = next_wd_region.begin()
				sublime.status_message('The word has changed - was \'%s\'' % next_wd)
				curr_line, _ = self.view.rowcol(next_pt)
				print "Commented word was \'%s\' on line %d now \'%s\' on line %d comment: %s" \
					% (next_wd, next_line, curr_wd, curr_line, next_comment)
				# re-position the comment anyway, as the begin-point for the current word may be different,
				# but remember the previous word so that they can move it
				if not self.view.vcomments.has_key(next_wd_begin):
					self.view.vcomments[next_wd_begin] = (next_wd, next_comment, curr_line)
					if next_wd_region.begin() != next_pt:
						del self.view.vcomments[next_pt]		# delete comment from its previous position
			sels.add(next_wd_region)
			self.view.show(next_wd_region)
			return
		else:
			sublime.status_message('No next comment.')
			return

	def highlight_comments(self):			# highlight all comments, including mis-positioned ones
		try:
			self.view.erase_regions("comments")
			self.view.erase_regions("comment_errs")
		except:
			pass
		if not len(self.view.vcomments):
			sublime.status_message('No comments to highlight.')
			return

		beyond_eov = False				# are their any comments beyond the view-size?
		sels = self.view.sel()
		sels.clear()
		comment_regions = []
		comment_errors = []
		eov = self.view.size()
		for key_pt in sorted(self.view.vcomments.iterkeys()):
			prev_wd, prev_comment, prev_line = self.view.vcomments[key_pt]
			if key_pt >= eov:							# comment is beyond the view-size
				print "Comment is past end-of-view - use \'recover\' command: %s (was line %d)" \
					% (prev_comment, prev_line)
				beyond_eov = True
				continue
			curr_wd_region = self.view.word(key_pt)
			curr_wd = self.view.substr(curr_wd_region)
			if curr_wd == prev_wd:
				if not len(comment_regions) and not len(comment_errors):
					self.view.show(curr_wd_region)					# show the 1st highlighted region
				comment_regions.append(curr_wd_region)
			else:
				curr_wd_begin = curr_wd_region.begin()
				curr_line, _ = self.view.rowcol(curr_wd_begin)
				print "Commented word was \'%s\' on line %d now \'%s\' on line %d comment: %s" \
					% (prev_wd, prev_line, curr_wd, curr_line, prev_comment)
				# re-position the comment anyway, as the begin-point for the current word may be different,
				# but remember the previous word so that they can move it
				if not self.view.vcomments.has_key(curr_wd_begin):
					self.view.vcomments[curr_wd_begin] = (prev_wd, prev_comment, prev_line)
					del self.view.vcomments[key_pt]					# delete the comment from its previous position
				if not len(comment_regions) and not len(comment_errors):
					self.view.show(curr_wd_region)					# show the 1st highlighted region
				comment_errors.append(curr_wd_region)
		if len(comment_regions):
			self.view.add_regions("comments", comment_regions, "comment", "")
		if len(comment_errors):
			self.view.add_regions("comment_errs", comment_errors, "invalid", "")
		if beyond_eov:
			sublime.status_message('There are comment(s) beyond the view-size - use \'recover\' command.')

	def remove_highlights(self):
		if not len(self.view.vcomments):
			sublime.status_message('There are no remaining comments.')
		try:
			self.view.erase_regions("comments")
			self.view.erase_regions("comment_errs")
			sublime.status_message('Removed comment highlighting.')
		except:
			pass

	def add_comment(self, text):					# at cursor position
		metrics = self.get_metrics(self.view)
		if not len(metrics):
			sublime.status_message('Unable to read word at cursor.')
			return
		elif len(metrics['curr_word']) < 2:
			sublime.status_message('Cursor should be within a word (2 characters min).')
		elif not re.match(self.sensible_word, metrics['curr_word']):
			sublime.status_message("Cursor needs to be within a \'sensible\' word, " \
				+ "and cannot start with a number: " + metrics['curr_word'])
		else:										# add the comment to the dictionary
			comment = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
			comment = comment.replace('\t', ' ' * 4).strip()
			self.view.vcomments[metrics['word_pt']] = (metrics['curr_word'], comment, metrics['word_line'])
			self.just_added = True					# don't re-display the comment text

	def delete_comment(self):						# at cursor position
		if not len(self.view.vcomments):
			sublime.status_message('No comments to delete.')
			return
		metrics = self.get_metrics(self.view)
		if not len(metrics):
			sublime.status_message('Unable to read word at cursor.')
			return
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

	def push_comments(self, direction = 'down'):				# move selected comment(s) down or up
																# or recover ones beyond the view-size
		if not len(self.view.vcomments):
			sublime.status_message('There are no comments for the current view.')
			return
		sels = self.view.sel()
		curr_sel = sels[0]
		
		if curr_sel.empty() and direction != 'recover':
			metrics = self.get_metrics(self.view)
			if not len(metrics):
				sublime.status_message('Unable to read word at cursor.')
				return
			else:
				pt_begin = pt_end = metrics['word_pt']
		elif direction == 'recover':
			pt_begin = self.view.size()
			pt_end = max(self.view.vcomments.iterkeys())
			if pt_end < pt_begin:
				sublime.status_message('There are no comments beyond the view-size.')
				return
		else:
			pt_begin = curr_sel.begin(); pt_end = curr_sel.end()
		sels.clear()

		if direction == 'down':		# push comment(s) down, starting with the last one in the selection
			sorted_pts = (key_pt for key_pt in reversed(sorted(self.view.vcomments.iterkeys())) \
				if pt_begin <= key_pt <= pt_end)
		else:
			sorted_pts = (key_pt for key_pt in sorted(self.view.vcomments.iterkeys()) \
				if pt_begin <= key_pt <= pt_end)
		moved_comment = False				# were we able to move any comment(s)?
		for next_pt in sorted_pts:
			prev_wd, prev_comment, prev_line = self.view.vcomments[next_pt]
			if direction == 'down':
				new_region = self.view.find(prev_wd, next_pt + 1, sublime.LITERAL)
			else:
				new_regions = (r for r in reversed(self.view.find_all(prev_wd, sublime.LITERAL)) \
					if r.begin() < next_pt)
				try:
					new_region = new_regions.next()
				except StopIteration:
					new_region = None
			if new_region:
				new_region_begin = new_region.begin()
				new_comment_line, _ = self.view.rowcol(new_region_begin)
				if self.view.vcomments.has_key(new_region_begin):
					_, old_comment, old_line = self.view.vcomments[new_region_begin]
					print "A comment has been over-written at line %d comment: %s" % (old_line, old_comment)
				self.view.vcomments[new_region_begin] = (prev_wd, prev_comment, new_comment_line)
				if new_region_begin != next_pt:		# delete the comment from its previous position
					del self.view.vcomments[next_pt]
				sels.add(new_region)
				if len(sels) == 1:
					self.view.show(new_region)			# show the first new region
					moved_comment = True				# found at least one comment to move
		if not moved_comment:
			sublime.status_message('Was unable to move any comment(s).')

	def process_commentary(self, text, caller_id):					# on_done for comments panel
		self.more_comments = False					# assume there is a problem with commentary
		window = sublime.active_window()
		view = window.active_view() if window != None else None
		if view is None:
			sublime.status_message('No active view.')
			return
		elif view.id() != caller_id:
			sublime.status_message('Not the same view - cancelled.')
			return
		if not len(text):					# They pressed Enter, attempt to display comment at cursor
			display_text = self.get_comment()
			if display_text != '':
				self.more_comments = True
				self.show_again()
			return

		self.more_comments = True					# okay to continue displaying the panel
		comment_command = text.strip().upper()
		if comment_command in ('SELECT', 'SEL', 'SEL ALL', 'SELECT ALL'):	# select commented words
			self.select_comments()
		elif comment_command in ('NEXT', 'NXT', 'DOWN', 'DWN'):				# select the next comment
			self.select_next('down')
		elif comment_command in ('PREV', 'PREVIOUS', 'UP'):					# select the previous comment
			self.select_next('up')
		elif comment_command in ('HIGH', 'HIGHLIGHT'):						# highlight all comments
			self.highlight_comments()
		elif comment_command in ('REMOVE', 'REMOVE HIGHLIGHT', 'REMOVE HIGHLIGHTS'):	# remove highlights
			self.remove_highlights()
		elif comment_command in ('DEL', 'DELETE'):							# delete comment at cursor
			self.delete_comment()
		elif comment_command in ('DEL ALL', 'DELALL', 'DELETE ALL', 'DELETEALL'):	# delete all comments
			self.delete_all_comments()
		elif comment_command in ('PUSH', 'PUSH DOWN', 'PUSH D', 'PUSH DWN', 'PUSHDOWN'):	# push comment(s) downwards
			self.push_comments('down')
		elif comment_command in ('PUSH UP', 'PUSH U', 'PUSHUP'):			# push comment(s) upwards
			self.push_comments('up')
		elif comment_command in ('RECOVER', 'RECOVER COMMENTS', 'RECOVER COMMENT'):
			self.push_comments('recover')					# recover comments that are beyond the view-size
		else:
			self.add_comment(text)							# add new comment at cursor
		self.show_again()									# the "commments panel"

	def show_comment_panel(self, existing_comment):
		caller_id = self.view.id()
		self.view.window().show_input_panel('Comment>', existing_comment, \
			lambda txt: self.process_commentary(txt, caller_id), None, self.hide_it)

	def show_again(self):									# the input panel
		if self.more_comments:
			if self.just_added:				# don't show comment text if it has just been added
				self.just_added = False
				curr_comment = ''
			else:
				curr_comment = self.get_comment()
			self.show_comment_panel(curr_comment)

	def hide_it(self):										# the input panel
		self.more_comments = False

class QuickCommentsCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		window = sublime.active_window()
		view = window.active_view() if window != None else None
		if view is None or view.id() != self.view.id():
			sublime.status_message('Click into the view/tab first.')
			return
		if not hasattr(self.view, 'vcomments'):
			sublime.status_message('No comments for this view.')
			return
		the_comments = []
		for key_pt in sorted(self.view.vcomments.iterkeys()):
			the_comments.append("Line no %5d %s" % (self.view.vcomments[key_pt][2], 
				self.view.vcomments[key_pt][1]))
		window.show_quick_panel(the_comments, self.on_chosen)

	def on_chosen(self, index):
		if index == -1: return
		sorted_keys = (k for (i, k) in enumerate(sorted(self.view.vcomments.iterkeys())) if i == index)
		try:
			the_key = sorted_keys.next()
		except StopIteration:
			sublime.status_message('Comment-point not found.')
			return
		if the_key > self.view.size():
			sublime.status_message('Commented word is no longer within the view-size - use \'recover\' command.')
			return
		sels = self.view.sel()
		sels.clear()
		comment_region = self.view.word(the_key)
		sels.add(comment_region)
		self.view.show(comment_region)
		if self.view.substr(comment_region) != self.view.vcomments[the_key][0]:
			sublime.status_message('The comment is no longer on its original word.')
		else:
			sublime.status_message("Comment: %s" % (self.view.vcomments[the_key][1]))

class PrintHtmlCommand(sublime_plugin.TextCommand):
	def setup(self, numbers):
		path_packages = sublime.packages_path()
		if not hasattr(self.view, 'vcomments'):
			self.view.vcomments = {}				# create empty dictionary anyway
			self.has_comments = False
		else:
			self.has_comments = (len(self.view.vcomments) > 0)

		fname = self.view.file_name()
		if fname == None or not path.exists(fname):
			fname = "Untitled"
		self.file_name = fname

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
		if curr_sel.empty() or len(self.view.lines(curr_sel)) < 2:	# don't print just 1 line
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

	def add_comments_table(self, the_html):
		the_html.write((COMMENTS_TBLHEAD).encode('utf-8', 'xmlcharrefreplace'))

		for (line_no, comment) in self.comments_list:
			the_html.write((COMMENTS_TBLROW % {"line_adj": str(line_no - self.curr_row), \
				"line_no": str(line_no + 1), "comment": comment}).encode('utf-8', 'xmlcharrefreplace'))

		the_html.write((COMMENTS_TBLEND).encode('utf-8', 'xmlcharrefreplace'))

	def write_header(self, the_html):
		the_html.write((HEADER % {"fname": self.file_name}).encode('utf-8', 'xmlcharrefreplace'))

		the_html.write((CSS_MAIN % {"fcolor": self.fground, "bcolor": self.bground, \
					"fsize": self.font_size, "fface": self.font_face}).encode('utf-8', 'xmlcharrefreplace'))

		if self.numbers:
			the_html.write(('\t#olCode { list-style-type: decimal; list-style-position: outside; }\n' \
				).encode('utf-8', 'xmlcharrefreplace'))
		else:
			the_html.write(('\t#olCode { list-style-type: none; list-style-position: inside; ' \
							+ 'margin: 0px; padding: 0px; }\n').encode('utf-8', 'xmlcharrefreplace'))

		the_html.write(('\tli { color: %s; margin-top: %dpt; margin-bottom: %dpt; }\n' \
			% (self.gfground, self.padd_top, self.padd_bottom)).encode('utf-8', 'xmlcharrefreplace'))

		if self.has_comments:
			the_html.write((CSS_COMMENTS % { "dot_colour": self.fground, "fsize": self.font_size } \
				).encode('utf-8', 'xmlcharrefreplace'))

		the_html.write(('\t</style>\n').encode('utf-8', 'xmlcharrefreplace'))

		the_html.write(JS_TIDYSPACES)

		if self.has_comments:
			the_html.write((JS_COMMENTS).encode('utf-8', 'xmlcharrefreplace'))	# JavaScript code to display comments

		the_html.write(('</head>\n').encode('utf-8', 'xmlcharrefreplace'))

	def convert_view_to_html(self, the_html):
		first_line = True
		if self.has_comments:
			self.comments_list = []		# (line number, comment) for the commments-table
			sorted_keys = sorted(self.view.vcomments.keys())			# temporary list of comment-points
		for line in self.view.split_by_newlines(sublime.Region(self.pt, self.size)):
			self.pt = line.begin(); self.end = self.pt + 1
			if line.empty():
				if first_line:
					the_html.write(('\n</li>').encode('utf-8', 'xmlcharrefreplace'))
					first_line = False
				else:
					the_html.write(('<li>\n</li>').encode('utf-8', 'xmlcharrefreplace'))
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
				the_colour = self.guess_colour(scope_name.strip())
				the_comment = None

				if len(tidied_text) and self.has_comments:
					comment_keys = (k for k in sorted_keys if self.pt <= k < self.end)
					try:
						comment_key = comment_keys.next()	# is there a comment in the region?
					except StopIteration:
						comment_key = None
					if comment_key:
						sorted_keys.remove(comment_key)		# remove from the temporary list
						the_word, the_comment, the_line = self.view.vcomments[comment_key]
						# has the pt moved since the comment was created?
						if self.view.substr(self.view.word(comment_key)) != the_word:
							the_comment = None				# no longer pts at the same word
							del self.view.vcomments[comment_key]		# delete the comment/ dict entry

				if len(tidied_text):			# re-check the length
					tidied_text = tidied_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
					tidied_text = tidied_text.replace('\t', ' ' * self.tab_size).strip('\r\n')
					temp_line.append((the_colour, tidied_text, the_comment))

				self.pt = self.end
				self.end = self.pt + 1

			if len(temp_line):
				if first_line:
					html_line = ''; first_line = False			# 1st opening-li is already in place
				else:
					html_line = '<li>'
				for (the_colour, tidied_text, the_comment) in temp_line:
					if the_colour == self.fground:
						the_span = (SCOPED % { "t_text": tidied_text })
					else:
						the_span = ( SCOPEDCOLOR % { "colour": the_colour, "t_text": tidied_text })
					if the_comment is not None:
						the_span = ( SCOPEDCOMMENT % { "scoped": the_span, "comment": the_comment })
						line_no, _ = self.view.rowcol(self.pt - 1)
						self.comments_list.append((line_no, the_comment))		# used to create the comments table
					html_line += the_span
				the_html.write((html_line + '</li>').encode('utf-8', 'xmlcharrefreplace'))
				temp_line[:] = []
			elif first_line:
				the_html.write(('\n</li>').encode('utf-8', 'xmlcharrefreplace'))
			first_line = False

	def write_body(self, the_html):
		temp_body = '<body>\n'
		temp_body += '<p id=\"top\" style=\"color:%s\">%s</p>\n' % (self.fground, self.file_name)
		temp_body += '<p>Tidy spaces: <input type=\"checkbox\" name=\"ckbTidy\" id=\"ckbTidy\" value=\"1\"' \
			+ 'onclick=\"tidySpaces()\"></p>'

		if self.has_comments:
			temp_body += CKBs_COMMENTS				# the checkbox options

		temp_body += '<pre id=\"preCode\"><ol id=\"olCode\"><li value="%d">' % (self.curr_row)	# use code's line numbering
		
		the_html.write((temp_body).encode('utf-8', 'xmlcharrefreplace'))

		# Convert view to HTML
		self.convert_view_to_html(the_html)

		the_html.write(('</ol>\n</pre>\n<br/>\n').encode('utf-8', 'xmlcharrefreplace'))
		# included empty line (br) to allow copying of last line without issue

	def run(self, edit, numbers):
		window = sublime.active_window()
		view = window.active_view() if window != None else None
		if view is None or view.id() != self.view.id():
			sublime.status_message('Click into the view/tab first.')
			return
		self.setup(numbers)
		with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as the_html:
			self.write_header(the_html)
			self.write_body(the_html)
			if self.has_comments and len(self.view.vcomments):			# check if all comments were deleted
				self.add_comments_table(the_html)						# initially, display: none

			the_html.write(('</body>\n</html>').encode('utf-8', 'xmlcharrefreplace'))

			# Open in web browser
			desktop.open(the_html.name)