"""HtmlAnnotations."""
import sublime
import sublime_plugin
from ExportHtml.lib.notify import error

PACKAGE_SETTINGS = "ExportHtml.sublime-settings"


def get_highlight_style():
    """Get the highlight style."""

    style_flag = 0
    settings = sublime.load_settings(PACKAGE_SETTINGS)
    scope = settings.get("annotation_highlight_scope", "comment")
    style = settings.get("annotation_highlight_style", "outline")
    if style == "outline":
        style_flag |= sublime.DRAW_OUTLINED
    return scope, style_flag


def clean_invalid_regions(view, annotations):
    """Cleanup regions that are no longer valid."""

    deletions = 0
    for x in range(0, int(annotations["count"])):
        key_name = "html_annotation_%d" % x
        regions = view.get_regions(key_name)
        if len(regions) and not regions[0].empty():
            annotations["annotations"]["html_annotation_%d" % x]["region"] = [regions[0].begin(), regions[0].end()]
            if deletions:
                new_key = "html_annotation_%d" % (x - deletions)
                annotations["annotations"][new_key] = annotations["annotations"][key_name]
                del annotations["annotations"][key_name]
                new_region = annotations["annotations"][new_key]["region"]
                view.erase_regions(key_name)
                scope, style = get_highlight_style()
                view.add_regions(
                    new_key,
                    [sublime.Region(new_region[0], new_region[1])],
                    scope,
                    "",
                    style
                )
        else:
            del annotations["annotations"]["html_annotation_%d" % x]
            annotations["count"] -= 1
            deletions += 1
            if len(regions):
                view.erase_regions(key_name)

    view.settings().set("annotation_comments", annotations)


def get_annotations(view):
    """Get annotations."""

    annotations = view.settings().get("annotation_comments", {"count": 0, "annotations": {}})
    clean_invalid_regions(view, annotations)
    return annotations


def clear_annotations(view):
    """Clear annotations."""

    annotations = view.settings().get("annotation_comments", {"count": 0, "annotations": {}})
    for x in range(0, int(annotations["count"])):
        view.erase_regions("html_annotation_%d" % x)
    view.settings().set("annotation_comments", {"count": 0, "annotations": {}})


def delete_annotations(view):
    """Delete annotations."""

    annotations = view.settings().get("annotation_comments", {"count": 0, "annotations": {}})
    for sel in view.sel():
        for x in range(0, int(annotations["count"])):
            region = annotations["annotations"]["html_annotation_%d" % x]["region"]
            annotation = sublime.Region(int(region[0]), int(region[1]))
            if annotation.contains(sel):
                view.erase_regions("html_annotation_%d" % x)
                break
    clean_invalid_regions(view, annotations)


def get_annotation_comment(view):
    """Get the annotation comment."""

    comment = None
    annotations = view.settings().get("annotation_comments", {"count": 0, "annotations": {}})
    if len(view.sel()):
        sel = view.sel()[0]
        for x in range(0, int(annotations["count"])):
            region = annotations["annotations"]["html_annotation_%d" % x]["region"]
            annotation = sublime.Region(int(region[0]), int(region[1]))
            if annotation.contains(sel):
                comment = annotations["annotations"]["html_annotation_%d" % x]["comment"]
    return comment


def is_selection_in_annotation(view, first_only=False):
    """Check if the current selection contains an annotation."""

    mode = view.settings().get("annotation_mode", False)
    selection = False
    if mode:
        annotations = view.settings().get("annotation_comments", {"count": 0, "annotations": {}})
        for sel in view.sel():
            for x in range(0, int(annotations["count"])):
                region = annotations["annotations"]["html_annotation_%d" % x]["region"]
                annotation = sublime.Region(int(region[0]), int(region[1]))
                if annotation.contains(sel):
                    selection = True
                    break
            if first_only:
                break
    return mode and selection


def annotations_exist(view):
    """See if annotations exist."""

    mode = view.settings().get("annotation_mode", False)
    found = False
    if mode:
        annotations = view.settings().get("annotation_comments", {"count": 0, "annotations": {}})
        if int(annotations["count"]):
            found = True
    return mode and found


def is_selected(view):
    """See text for annotation is selected."""

    mode = view.settings().get("annotation_mode", False)
    selected = not view.sel()[0].empty()
    return mode and selected


class ShowAnnotationCommentCommand(sublime_plugin.TextCommand):

    """Show the annotation."""

    def is_visible(self):
        """Check if command should be visible in menus."""

        return is_selection_in_annotation(self.view)

    def run(self, edit):
        """Run command."""

        comment = get_annotation_comment(self.view)
        if comment is not None:
            sublime.message_dialog("Annotation Comment:\n\n%s" % comment)
            sublime.set_clipboard(comment)


class ClearAnnotationsCommand(sublime_plugin.TextCommand):

    """Clear the annotations."""

    def is_visible(self):
        """Check if command should be visible in menus."""

        return annotations_exist(self.view)

    def run(self, edit):
        """Run command."""

        clear_annotations(self.view)


class DeleteAnnotationsCommand(sublime_plugin.TextCommand):

    """Delete the annotations."""

    def is_visible(self):
        """Check if command should be visible in menus."""

        return is_selection_in_annotation(self.view)

    def run(self, edit):
        """Run command."""

        delete_annotations(self.view)


class EnableAnnotationModeCommand(sublime_plugin.TextCommand):

    """Enable annotation mode."""

    def is_visible(self):
        """Check if command should be visible in menus."""

        return not self.view.settings().get("annotation_mode", False)

    def run(self, edit):
        """Run command."""

        self.view.run_command("toggle_annotation_html_mode")


class DisableAnnotationModeCommand(sublime_plugin.TextCommand):

    """Disable annotation mode."""

    def is_visible(self):
        """Check if command should be visible in menus."""

        return self.view.settings().get("annotation_mode", False)

    def run(self, edit):
        """Run command."""

        self.view.run_command("toggle_annotation_html_mode")


class ToggleAnnotationHtmlModeCommand(sublime_plugin.TextCommand):

    """Toggle annotation mode."""

    def is_enabled(self):
        """Check if command is enabled."""

        return not self.view.settings().get('is_widget')

    def run(self, edit):
        """Run command."""

        mode = False if self.view.settings().get("annotation_mode", False) else True
        self.view.settings().set("annotation_mode", mode)
        if mode:
            self.view.settings().set("annotation_read_mode", self.view.is_read_only())
            self.view.set_read_only(True)
            self.view.set_status("html_annotation_mode", "Annotation Mode: ON")
        else:
            clear_annotations(self.view)
            self.view.set_read_only(self.view.settings().get("annotation_read_mode", False))
            self.view.erase_status("html_annotation_mode")


class AddAnnotationCommand(sublime_plugin.TextCommand):

    """Add an annotation."""

    def is_visible(self):
        """Check if command should be visible in menus."""

        return is_selected(self.view)

    def run(self, edit):
        """Run command."""

        AnnotateHtml(self.view).run()


class EditAnnotationCommand(sublime_plugin.TextCommand):

    """Edit the current annotation."""

    def is_visible(self):
        """Check if command should be visible in menus."""

        return is_selection_in_annotation(self.view, first_only=True)

    def run(self, edit):
        """Run command."""

        AnnotateHtml(self.view).run()


class AnnotateHtml(object):

    """AnnotateHtml."""

    def __init__(self, view):
        """Initialize."""

        self.view = view

    def subset_annotation_adjust(self):
        """Show annotation at selection if exists."""

        subset = None
        comment = ""
        parent = None
        intersect = False
        for k, v in self.annotations["annotations"].items():
            region = sublime.Region(int(v["region"][0]), int(v["region"][1]))
            if region.contains(self.sel):
                subset = region
                comment = v["comment"]
                parent = k
                break
            elif region.intersects(self.sel):
                intersect = True
                break
        if subset is not None:
            self.sel = subset
        return comment, parent, intersect

    def add_annotation(self, s, view_id, subset):
        """Add the annotation."""

        window = sublime.active_window()
        view = window.active_view() if window is not None else None
        if s != "" and view is not None and view_id == view.id():
            if subset is None:
                idx = self.annotations["count"]
                key_name = ("html_annotation_%d" % idx)
            else:
                key_name = subset

            self.annotations["annotations"][key_name] = {
                "region": [self.sel.begin(), self.sel.end()],
                "comment": s
            }
            if subset is None:
                self.annotations["count"] += 1
            self.view.settings().set("annotation_comments", self.annotations)

            scope, style = get_highlight_style()
            self.view.add_regions(
                key_name,
                [self.sel],
                scope,
                "",
                style
            )

    def annotation_panel(self, default_comment, subset):
        """Show annotation input panel."""

        view_id = self.view.id()
        self.view.window().show_input_panel(
            ("Annotate region (%d, %d)" % (self.sel.begin(), self.sel.end())),
            default_comment,
            lambda x: self.add_annotation(x, view_id=view_id, subset=subset),
            None,
            None
        )

    def run(self):
        """Run command."""

        self.sel = self.view.sel()[0]
        self.annotations = get_annotations(self.view)
        comment, subset, intersects = self.subset_annotation_adjust()
        if not intersects:
            self.annotation_panel(comment, subset)
        else:
            error("Cannot have intersecting annotation regions!")
