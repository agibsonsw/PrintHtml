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
	p { margin-top: 8px; margin-bottom: 4px; }
	#preCode { border: 0; margin: 0; padding: 0; font: %(fsize)dpt '%(fface)s', Consolas, Monospace; }
	span { color: %(fcolor)s; background-color: %(bcolor)s; display: inline; border: 0; margin: 0; padding: 0; }
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

SCOPEDCOLOR = \
"""<span style="color:%(colour)s;">%(t_text)s</span>"""
SCOPEDCOMMENT = \
"""<a class="tooltip" href="#" onclick="return false;">%(scoped)s<span class="comment">%(comment)s</span></a>"""

JS_TIDYSPACES = \
"""
<script type="text/javascript">
	function tidySpaces() {
		var olCode, spans, i, span_textnode, span_text, span_next, offLeft, newLeft;
		if (document.getElementsByClassName) {
			spans = document.getElementsByClassName('tidy');
			if (spans != 'undefined' && spans.length) {
				for ( i = 0; i < spans.length; i++ )
					spans[i].style.paddingLeft = (spans[i].style.paddingLeft == '0px') ? 
						spans[i].prevValue : '0px';
				return;
			}
		}
		olCode = document.getElementById('olCode');
		spans = olCode.getElementsByTagName('span');
		for (i = 0; i < spans.length; i++) {
			if ( spans[i].previousSibling ) {
				if ( spans[i].className && spans[i].className == 'comment')
					continue;
				span_textnode = spans[i].firstChild;
				span_text = span_textnode.data;
				tidied = span_text.replace(/\s{2,}$/,'');
				if (span_text.length && (span_text.length > tidied.length)) {
					if ( spans[i].nextSibling ) {
						span_next = spans[i];
						while ( (span_next = span_next.nextSibling) && span_next.className 
							&& span_next.className == 'comment' && span_next.nextSibling )
							;		// do nothing, get next span (or 'a' tag)
						if ( span_next ) {
							offLeft = span_next.offsetLeft;
							newLeft = (parseInt(offLeft / 60)) * 60 + 60;
							span_next.style.paddingLeft = (newLeft - offLeft) + 'px';
							span_next.className = 'tidy';
							span_next.prevValue = span_next.style.paddingLeft;
						}
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
			comments_div.className = (document.getElementById('ckbBottom').checked) ? 
				'overlay_bl' : 'overlay';
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

	def get_metrics(self, pt = None):				# return word, begin(), etc., at cursor or point
		try:
			if pt is None:
				sel = self.view.sel()[0]
				pt = sel.begin()
			word_region = self.view.word(pt)
			word = self.view.substr(word_region)
			word_pt = word_region.begin()
			line, col = self.view.rowcol(word_pt)
		except:
			return {}
		return locals()

	def same_word(self, pt):						# is the comment still on the same word?
		try:
			word_region = self.view.word(pt)
			curr_word = self.view.substr(word_region)
		except:
			return False
		return (self.view.vcomments[pt][0] == curr_word)

	def adjust_comment(self, key_pt):				# correct the begin-point for the comment,
		current = self.get_metrics(key_pt)			# but remember the previous word (so it can be moved)
		if not len(current):
			return False							# unable to adjust
		existing_wd, existing_comment, existing_line = self.view.vcomments[key_pt]
		if current['word_pt'] in self.view.vcomments:
			return False							# there is already a comment on the cursor's word
		else:
			self.view.vcomments[current['word_pt']] = (existing_wd, existing_comment, current['line'])
			if current['word_pt'] != key_pt:
				del self.view.vcomments[key_pt]		# delete comment from its previous position
			return True

	def get_comment(self):							# return comment-text at cursor, or False
		if not hasattr(self.view, 'vcomments'): return ''
		selection = self.get_metrics()
		if not len(selection): return ''
		if selection['word_pt'] in self.view.vcomments:
			return self.view.vcomments[selection['word_pt']][1]
		else:
			return ''

	def run(self, edit):
		self.more_comments = True
		self.just_added = False						# haven't just added a new comment
		if not hasattr(self.view, 'highlighted'):
			self.view.highlighted = False
		if not hasattr(self.view, 'vcomments'):
			self.view.vcomments = {}
			curr_comment = ''
		else:
			curr_comment = self.get_comment()
		self.show_comment_panel(curr_comment)		# show panel and comment at cursor

	def select_comments(self):						# clears current selection and deletes any
		sels = self.view.sel()						# comments that are no longer on the same word
		sels.clear()
		eov = self.view.size()
		for key_pt in sorted(self.view.vcomments):
			prev_wd, prev_comment, prev_line = self.view.vcomments[key_pt]
			if key_pt >= eov:						# delete comments past end of the view
				del self.view.vcomments[key_pt]
				print "Comment past end-of-view deleted: %s (was line %d)" % (prev_comment, prev_line)
				continue
			current = self.get_metrics(key_pt)
			if len(current) and current['word'] != '' and self.same_word(key_pt):
				sels.add(current['word_region'])
				if len(sels) == 1:							# show 1st comment region
					self.view.show(current['word_region'])
			else:
				print "DELETED: Commented word was '%s' on line %d comment: %s" \
					% (prev_wd, prev_line, prev_comment)
				del self.view.vcomments[key_pt]				# delete mis-positioned comment
		if not len(self.view.vcomments):
			return 'Comments no longer in original positions - deleted.'

	def select_next(self, direction = 'down'):
		message = None
		selection = self.get_metrics()
		if not len(selection):
			return 'Ensure the cursor is somewhere in the view.'
		curr_pt = selection['pt']
		sels = self.view.sel()
		if direction == 'down':
			sorted_pts = (key_pt for key_pt in sorted(self.view.vcomments) if key_pt > curr_pt)
		else:
			sorted_pts = (key_pt for key_pt in reversed(sorted(self.view.vcomments)) if key_pt < curr_pt)
		try:
			next_pt = sorted_pts.next()
		except StopIteration:
			next_pt = None
		if next_pt:
			next_wd, next_comment, next_line = self.view.vcomments[next_pt]
			if next_pt >= self.view.size():						# next comment is beyond the view-size
				print "Comment past end-of-view: %s (was line %d)" % (next_comment, next_line)
				return "Comment is past end-of-view - use 'recover' command: %s (was line %d)" \
					% (next_comment, next_line)
			current = self.get_metrics(next_pt)
			if not len(current):					# problem reading points' word, etc.
				return "Unable to read details at next comment point."
			if not self.same_word(next_pt):
				message = "The word has changed - was '%s'" % next_wd
				print "Commented word was '%s' on line %d now '%s' on line %d comment: %s" \
					% (next_wd, next_line, current['word'], current['line'], next_comment)
				# re-position the comment anyway, as the begin-point for the current word may be different,
				# but remember the previous word so that they can move it
				self.adjust_comment(next_pt)
			sels.clear()
			sels.add(current['word_region'])
			self.view.show(current['word_region'])
		else:
			return 'No comment %s cursor.' % ({"down": "after", "up": "before"}.get(direction))
		return message

	def highlight_comments(self):			# highlight all comments, including mis-positioned ones
		comment_regions = []
		comment_errors = []
		eov = self.view.size()
		beyond_eov = False							# are their any comments beyond the view-size?

		for key_pt in sorted(self.view.vcomments):
			prev_wd, prev_comment, prev_line = self.view.vcomments[key_pt]
			if key_pt >= eov:							# comment is beyond the view-size
				print "Comment is past end-of-view - use 'recover' command: %s (was line %d)" \
					% (prev_comment, prev_line)
				beyond_eov = True
				continue
			current = self.get_metrics(key_pt)
			if not len(current) or current['word'] == '':			# problem reading points' word, etc.
				print "DELETED: Could not find a location for comment: %s" % (prev_comment)
				del self.view.vcomments[key_pt]
				continue
			if self.same_word(key_pt):
				if not len(comment_regions) and not len(comment_errors):
					self.view.show(current['word_region'])			# show the 1st highlighted region
				comment_regions.append(current['word_region'])
			else:
				print "Commented word was '%s' on line %d now '%s' on line %d comment: %s" \
					% (prev_wd, prev_line, current['word'], current['line'], prev_comment)
				self.adjust_comment(key_pt)
				if not len(comment_regions) and not len(comment_errors):
					self.view.show(current['word_region'])					# show the 1st highlighted region
				comment_errors.append(current['word_region'])
		if len(comment_regions):
			self.view.add_regions("comments", comment_regions, "comment", "")
			self.view.highlighted = True
		if len(comment_errors):
			self.view.add_regions("comment_errs", comment_errors, "invalid", "")
			self.view.highlighted = True
		if beyond_eov:
			return "There are comment(s) beyond the view-size - use 'recover' command."

	def remove_highlights(self):
		try:
			self.view.erase_regions("comments")
			self.view.erase_regions("comment_errs")
			self.view.highlighted = False
			return 'Removed comment highlighting.'
		except:
			return None

	def remove_highlight(self, pt):							# utility fn - not called as a 'command'
		high_cs = self.view.get_regions("comments")
		high_errs = self.view.get_regions("comment_errs")
		if not len(high_cs) and not len(high_errs):
			return
		comment_regions = []
		for r in high_cs:
			if not r.contains(pt):
				comment_regions.append(r)
		self.view.erase_regions("comments")
		if len(comment_regions):
			self.view.add_regions("comments", comment_regions, "comment", "")
		comment_errors = []
		for r in high_errs:
			if not r.contains(pt):
				comment_errors.append(r)
		self.view.erase_regions("comment_errs")
		if len(comment_errors):
			self.view.add_regions("comment_errs", comment_errors, "invalid", "")

		if not len(self.view.get_regions("comments")) and not len(self.view.get_regions("comment_errs")):
			self.view.highlighted = False

	def add_highlight(self, new_region, error = False):		# utility fn - not called as a 'command'
		if error:
			highs = self.view.get_regions("comment_errs") or []
			highs.append(new_region)
			self.view.erase_regions("comment_errs")
			self.view.add_regions("comment_errs", highs, "invalid", "")
		else:
			highs = self.view.get_regions("comments") or []
			highs.append(new_region)
			self.view.erase_regions("comments")
			self.view.add_regions("comments", highs, "comment", "")
		if not len(self.view.get_regions("comments")) and not len(self.view.get_regions("comment_errs")):
			self.view.highlighted = False

	def add_comment(self, text):					# at cursor position
		selection = self.get_metrics()
		if not len(selection):
			return 'Unable to read word at cursor.'
		elif len(selection['word']) < 2:
			return 'Cursor should be within a word (2 characters min).'
		elif not re.match(self.sensible_word, selection['word']):
			return "Cursor needs to be within a 'sensible' word, " \
				+ "and cannot start with a number: " + selection['word']
		else:										# add the comment to the dictionary
			comment = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
			comment = comment.replace('\t', ' ' * 4).strip()
			self.view.vcomments[selection['word_pt']] = (selection['word'], comment, selection['line'])
			if self.view.highlighted:
				self.add_highlight(selection['word_region'], False)		# False == not an error region
			self.just_added = True					# don't re-display the comment text


	def delete_comment(self):						# at cursor position
		selection = self.get_metrics()
		if not len(selection):
			return 'Unable to read word at cursor.'
		else:										# delete the comment from the dictionary
			if selection['word_pt'] in self.view.vcomments:
				del self.view.vcomments[selection['word_pt']]
				if self.view.highlighted:
					self.remove_highlight(selection['word_pt'])
				return 'Comment at cursor deleted.'
			else:
				return 'No comment found at cursor.'

	def delete_all_comments(self):
		self.view.vcomments = {}
		return 'All comments deleted.'

	def push_comments(self, direction = 'down'):				# move selected comment(s) down or up
		selection = self.get_metrics()							# or recover ones beyond the view-size
		if not len(selection):
			return 'Ensure the cursor is in a word in the view.'
		sels = self.view.sel()
		curr_sel = sels[0]
		if curr_sel.empty() and direction != 'recover':
			if selection['word_pt'] in self.view.vcomments:
					pt_begin = pt_end = selection['word_pt']
			else:
				return 'No comment found at cursor.'
		elif direction == 'recover':
			pt_begin = self.view.size()
			pt_end = max(self.view.vcomments)
			if pt_end < pt_begin:
				return 'There are no comments beyond the view-size.'
		else:
			pt_begin = curr_sel.begin(); pt_end = curr_sel.end()
		if pt_begin == pt_end:
			sorted_pts = [pt_begin]				# just the current comment to move
		else:
			sorted_pts = [key_pt for key_pt in sorted(self.view.vcomments) if pt_begin <= key_pt <= pt_end]
			if direction == 'down':
				sorted_pts = reversed(sorted_pts)

		sels.clear()
		moved_comment = False					# were we able to move any comment(s)?

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
				if new_region_begin in self.view.vcomments:
					_, old_comment, old_line = self.view.vcomments[new_region_begin]
					print "Already a comment at line %d comment: %s" % (new_comment_line, old_comment)
					sels.add(new_region)
					self.view.show(new_region)
					return "Already a comment at line %d comment: %s" % (new_comment_line, old_comment)
				self.view.vcomments[new_region_begin] = (prev_wd, prev_comment, new_comment_line)
				if new_region_begin != next_pt:			# delete the comment from its previous position
					del self.view.vcomments[next_pt]
					if self.view.highlighted:
						self.remove_highlight(next_pt)
				if self.view.highlighted:
					self.add_highlight(new_region, False)
					if not moved_comment:				# select the first (new) highlighted region
						sels.add(new_region)
						self.view.show(new_region)
						moved_comment = True
				else:
					sels.add(new_region)
					if not moved_comment:
						self.view.show(new_region)			# show the first new region
						moved_comment = True				# found at least one comment to move
		if not moved_comment:
			return 'Was unable to move any comment(s).'

	def pull_comment(self, direction = 'down'):
		selection = self.get_metrics()
		if not len(selection):
			return 'Ensure the cursor is in a word in the view.'
		sels = self.view.sel()
		if len(sels) > 1:
			return "'Pull' doesn't work with multi-selection."
		curr_wd = selection['word']
		if len(curr_wd) < 2:
			return 'Cursor should be within a word (2 characters min).'
		elif not re.match(self.sensible_word, curr_wd):
			return "Cursor needs to be within a 'sensible' word, " \
				+ "and cannot start with a number: " + curr_wd
		curr_pt = selection['word_pt']
		if curr_pt in self.view.vcomments:
			return 'There is already a comment at the cursor.'

		if direction == 'down':
			sorted_pts = (key_pt for key_pt in reversed(sorted(self.view.vcomments)) if key_pt < curr_pt)
		else:
			sorted_pts = (key_pt for key_pt in sorted(self.view.vcomments) if key_pt > curr_pt)
		try:
			next_pt = sorted_pts.next()
		except StopIteration:
			next_pt = None
		if next_pt:
			next_wd, next_comment, next_line = self.view.vcomments[next_pt]
			self.view.vcomments[curr_pt] = (curr_wd, next_comment, selection['line'])
			del self.view.vcomments[next_pt]
			if self.view.highlighted:
				self.remove_highlight(next_pt)		# that is, from its 'previous' position
			sels.clear()
			sels.add(selection['word_region'])
			if self.view.highlighted:
				self.add_highlight(selection['word_region'], False)
			self.view.show(selection['word_region'])
		else:
			return 'There is no comment to pull %s to the cursor position.' % (direction)

	def follow_highlights(self):
		if not self.view.highlighted:
			return 'View comments are not currently highlighted.'
		high_cs = self.view.get_regions("comments")
		high_errs = self.view.get_regions("comment_errs")
		if not len(high_cs) and not len(high_errs):
			return 'There are no highlighted regions to follow.'
		if len(high_errs):
			return 'There are errors highlighted which need to be corrected.'
		if len(high_cs) != len(self.view.vcomments):
			return 'There are not the same number of comments as highlights.'
		_ = self.remove_highlights()
		comment_regions = []
		comment_errors = []
		for pt, area in zip(sorted(self.view.vcomments), high_cs):
			prev_wd, prev_comment, _ = self.view.vcomments[pt]
			c_highlight = self.get_metrics(area.begin())
			if not len(c_highlight):
				continue								# unable to read metrics at highlight
			if c_highlight['word'] == prev_wd:
				comment_regions.append(c_highlight['word_region'])
			else:
				comment_errors.append(c_highlight['word_region'])
			if c_highlight['word_pt'] != pt:
				self.view.vcomments[c_highlight['word_pt']] = (prev_wd, prev_comment, c_highlight['line'])
				del self.view.vcomments[pt]

		if len (comment_regions):
			self.view.add_regions("comments", comment_regions, "comment", "")
			self.view.highlighted = True
		if len(comment_errors):
			self.view.add_regions("comment_errs", comment_errors, "invalid", "")
			self.view.highlighted = True
			return 'Some comments are in the wrong position.'

	def process_commentary(self, text, caller_id):					# on_done for comments panel
		self.more_comments = False						# assume there is a problem with commentary
		window = sublime.active_window()
		view = window.active_view() if window != None else None
		if view is None:
			sublime.status_message('No active view.')
			return
		elif view.id() != caller_id:
			sublime.status_message('Not the same view - cancelled.')
			return
		text = text.strip()
		if not len(text):					# They pressed Enter, attempt to display comment at cursor
			display_text = self.get_comment()
			if display_text != '':
				self.more_comments = True
				self.show_again()
			return

		self.more_comments = True					# okay to continue displaying the panel

		comment_command = text.strip().upper()
		has_comments = hasattr(self.view, 'vcomments') and (len(self.view.vcomments) > 0)
		message = None								# possible message to display in the status bar

		if comment_command in ('SELECT', 'SEL', 'SEL ALL', 'SELECT ALL'):		# select commented words
			_ = self.remove_highlights()
			message = self.select_comments() if has_comments else 'There are no comments to select.'

		elif comment_command in ('NEXT', 'NXT', 'DOWN', 'DWN', 'SELECT NEXT'):	# select the next comment
			message = self.select_next('down') if has_comments else 'There are no comments to select.'

		elif comment_command in ('PREV', 'PREVIOUS', 'UP', 'SELECT PREV'):		# select the previous comment
			message = self.select_next('up') if has_comments else 'There are no comments to select.'

		elif comment_command in ('HIGH', 'HIGHLIGHT'):							# highlight all comments
			_ = self.remove_highlights()
			message = self.highlight_comments() if has_comments else 'There are no comments to highlight.'

		elif comment_command in ('REMOVE', 'REMOVE HIGHLIGHT', 'REMOVE HIGHLIGHTS'):	# remove highlights
			message = self.remove_highlights()

		elif comment_command in ('DEL', 'DELETE'):								# delete comment at cursor
			message = self.delete_comment() if has_comments else 'There are no comments to delete.'

		elif comment_command in ('DEL ALL', 'DELALL', 'DELETE ALL', 'DELETEALL'):		# delete all comments
			_ = self.remove_highlights()
			message = self.delete_all_comments() if has_comments else 'There are no comments to delete.'

		elif comment_command in ('PUSH', 'PUSH DOWN', 'PUSH D', 'PUSH DWN', 'PUSHDOWN'):	# push comment(s) downwards
			message = self.push_comments('down') if has_comments else 'No comments to push down.'

		elif comment_command in ('PUSH UP', 'PUSH U', 'PUSHUP'):			# push comment(s) upwards
			message = self.push_comments('up') if has_comments else 'No comments to push up.'

		elif comment_command in ('PULL', 'PULL DOWN', 'PULL D', 'PULLDOWN'):		# pull comment down to cursor
			message = self.pull_comment('down') if has_comments else 'No comments to pull down.'

		elif comment_command in ('PULL UP', 'PULL U', 'PULLUP'):					# pull comment up to cursor
			message = self.pull_comment('up') if has_comments else 'No comments to pull up.'

		elif comment_command in ('RECOVER', 'RECOVER COMMENTS', 'RECOVER COMMENT'):	# recover comments beyond view
			message = self.push_comments('recover') if has_comments else 'No comments in the current view.'

		elif comment_command in ('FOLLOW', 'FOLLOW HIGHLIGHTS'):		# move/adjust comments to highlighted regions
			message = self.follow_highlights() if has_comments else 'There are no comments for the current view.'

		else:
			message = self.add_comment(text)							# add new comment at cursor
			
		if message is not None:
			sublime.status_message(message)
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
		for key_pt in sorted(self.view.vcomments):
			the_comments.append("Line no %5d %s" % (self.view.vcomments[key_pt][2] + 1, 
				self.view.vcomments[key_pt][1]))
		window.show_quick_panel(the_comments, self.on_chosen)

	def on_chosen(self, index):
		if index == -1: return
		sorted_keys = (k for (i, k) in enumerate(sorted(self.view.vcomments)) if i == index)
		try:
			the_key = sorted_keys.next()
		except StopIteration:
			sublime.status_message("Comment-point not found.")
			return
		if the_key > self.view.size():
			sublime.status_message("Comment is no longer within the view-size - use 'recover' command.")
			return
		sels = self.view.sel()
		sels.clear()
		comment_region = self.view.word(the_key)
		sels.add(comment_region)
		self.view.show(comment_region)
		if self.view.substr(comment_region) != self.view.vcomments[the_key][0]:
			sublime.status_message("The comment is no longer on its original word.")
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
			self.colours[the_key] = the_colour or self.fground
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
					for x in range(self.pt, self.end):
						if x in self.view.vcomments:
							the_word, the_comment, the_line = self.view.vcomments[x]
							# has the pt moved since the comment was created?
							if self.view.substr(self.view.word(x)) != the_word:
								the_comment = None				# no longer pts at the same word
								del self.view.vcomments[x]		# delete the comment/ dict entry
							break

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
		temp_body += '<p id=\"pTidy\">Attempt to tidy spaces:<input type=\"checkbox\" name=\"ckbTidy\"' \
			+ 'id=\"ckbTidy\" value=\"1\" onclick=\"tidySpaces()\"></p>'

		if self.has_comments:
			temp_body += CKBs_COMMENTS				# the checkbox options

		temp_body += '<pre id=\"preCode\"><ol id=\"olCode\"><li value="%d">' % (self.curr_row)	# use code's line numbering
		
		the_html.write((temp_body).encode('utf-8', 'xmlcharrefreplace'))

		# Convert view to HTML
		self.convert_view_to_html(the_html)

		the_html.write(('</ol></pre>\n<br/>\n').encode('utf-8', 'xmlcharrefreplace'))
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