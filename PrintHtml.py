import sublime, sublime_plugin
from xml.dom import minidom
import re
from os import path

class PrintHtmlCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.colours = {}
		path_packages = sublime.packages_path()
		settings = sublime.load_settings('Preferences.sublime-settings')
		colour_scheme = settings.get('color_scheme')
		# colour_scheme = colour_scheme.replace('/', '\\\\')
		colour_scheme = path.normpath(colour_scheme)
		colour_scheme = colour_scheme.replace('Packages', '')
		font_size = settings.get('font_size') or 10
		font_face = settings.get('font_face') or 'Consolas'
		tab_size = settings.get('tab_size') or 4
		# padd_bottom = settings.get('line_padding_bottom') or 0
		doc = minidom.parse(path_packages + colour_scheme)
		the_dict = doc.getElementsByTagName('dict')[0]
		the_array = the_dict.getElementsByTagName('array')[0]
		colour_settings = the_array.getElementsByTagName('dict')[0]
		bground = ''; fground = ''
		for key_tag in colour_settings.getElementsByTagName('key'):
			try:
				if key_tag.firstChild.data.strip() == 'background':
					bground = key_tag.nextSibling.nextSibling.firstChild.data.strip()
				elif key_tag.firstChild.data.strip() == 'foreground':
					fground = key_tag.nextSibling.nextSibling.firstChild.data.strip()
			except:
				pass
		dict_items = the_array.getElementsByTagName('dict')[1:]
		for item in dict_items:
			scope = ''; colour = ''
			for key_tag in item.getElementsByTagName('key'):
				try:
					if key_tag.firstChild.data.strip() == 'scope':
						scope = key_tag.nextSibling.nextSibling.firstChild.data.strip()
					elif key_tag.firstChild.data.strip() == 'foreground':
						colour = key_tag.nextSibling.nextSibling.firstChild.data.strip()
				except:
					pass
			if scope != '' and colour != '':
				self.colours[scope] = colour

		curr_view = self.view
		curr_file = curr_view.file_name()
		head, tail = path.split(curr_file)
		fname, ext = path.splitext(tail)
		ext = ext.replace('.', '_')
		
		curr_sel = curr_view.sel()[0]
		if curr_sel.empty() or abs(curr_sel.end() - curr_sel.begin()) < 4:
			the_html = open(head + path.sep + fname + ext + '_parsed.html', 'w')
			size = curr_view.size()
			pt = 0; end = 1
		else:
			the_html = open(head + path.sep + fname + ext + '_part.html', 'w')
			size = curr_sel.end()
			pt = curr_sel.begin()
			end = pt + 1
		the_html.write('<html>\n<head>\n<style type=\"text/css\">\n')
		the_html.write('\tspan { display: inline; border: 0; margin: 0; padding: 0; }\n')
		the_html.write('\tbody { ')
		if fground != '': the_html.write('color: ' + fground + ';')
		if bground != '': the_html.write(' background-color: ' + bground + ';')
		the_html.write(' font: ' + `font_size` + 'pt \"' + font_face + '\", Consolas, Monospace;')
		the_html.write('\n}\n')
		the_html.write('</style>\n</head>\n<body>\n')
		
		while end <= size:
			scope_name = curr_view.scope_name(pt)
			while curr_view.scope_name(end) == scope_name and end <= size:
				end += 1
			region = sublime.Region(pt, end)
			the_key = scope_name.strip()
			if self.colours.has_key(the_key):
				the_colour = self.colours[the_key]
			else:
				if re.match('source\.[a-zA-Z_]*$', the_key) is not None:
					self.colours[the_key] = fground
					the_colour = fground
				else:
					best_match = -1
					for key in self.colours:
						if curr_view.score_selector(pt, key) > best_match:
							best_match = curr_view.score_selector(pt, key)
							the_colour = self.colours[key]
					self.colours[the_key] = the_colour
			tidied_text = curr_view.substr(region)
			tidied_text = tidied_text.replace('&', '&amp;')
			tidied_text = tidied_text.replace('<', '&lt;')
			tidied_text = tidied_text.replace('>', '&gt;')
			tidied_text = tidied_text.replace('\t', '&nbsp;' * tab_size)
			tidied_text = tidied_text.replace(' ' * tab_size, '&nbsp;' * tab_size)
			tidied_text = tidied_text.replace('\n', '<br>')

			the_html.write('<span style=\"color:' + the_colour + '\">')
			the_html.write(tidied_text + '</span>')
			pt = end
			end = pt + 1
		the_html.write('</body>\n</html>')
		the_html.close()