"""Changelog."""
import sublime
import sublime_plugin
import webbrowser

CSS = '''
html { {{'.background'|css}} }
div.export-html { padding: 0; margin: 0; {{'.background'|css}} }
.export-html h1, .export-html h2, .export-html h3,
.export-html h4, .export-html h5, .export-html h6 {
    {{'.string'|css}}
}
.export-html blockquote { {{'.comment'|css}} }
.export-html a { text-decoration: none; }
'''


class ExportHtmlChangesCommand(sublime_plugin.WindowCommand):
    """Changelog command."""

    def run(self):
        """Show the changelog in a new view."""
        try:
            import mdpopups
            has_phantom_support = (mdpopups.version() >= (1, 10, 0)) and (int(sublime.version()) >= 3118)
        except Exception:
            has_phantom_support = False

        text = sublime.load_resource('Packages/ExportHtml/CHANGES.md')
        view = self.window.new_file()
        view.set_name('ExportHtml - Changelog')
        view.settings().set('gutter', False)
        if has_phantom_support:
            mdpopups.add_phantom(
                view,
                'changelog',
                sublime.Region(0),
                text,
                sublime.LAYOUT_INLINE,
                wrapper_class="export-html",
                css=CSS,
                on_navigate=self.on_navigate
            )
        else:
            view.run_command('insert', {"characters": text})
        view.set_read_only(True)
        view.set_scratch(True)

    def on_navigate(self, href):
        """Open links."""
        webbrowser.open_new_tab(href)
