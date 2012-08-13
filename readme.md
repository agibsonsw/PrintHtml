# About
This is a fork of agibsonsw's [PrintHtml](https://github.com/agibsonsw/PrintHtml) plugin.  This plugin allows the exporting of a document in ST2 to an HTML file or to BBCode.  It duplicates ST2's theme colors and font styles.

<img src="http://dl.dropbox.com/u/342698/ExportHtml/preview.png" border="0"/>

# Features
- Export to HTML using any tmTheme for syntax highlighting
- Can handle any language supported by ST2
- Supports bold and italic theme font styles as well
- Configurable output
- Format suitable for copying and pasting in emails
- 2 included tmTheme files for color and grayscale printing (but any can be used)
- Export only selections (multi-select supported)
- Export and show highlights (multi-select supported)
- Toggle gutter on/off in browser view
- Automatically open browser print dialog (optional)
- Enable/disable configurable word wrapping

# Usage: Exporting HTML
ExportHtml comes with a number of default commands available, but these can be overridden in the settings file.  Or you can create commands directly outside of the settings file bound to the command palette, key bindings, or even the menu.

If adding a command to the settings file, it goes under the ```html_panel``` setting.  These configurations will appear under the ```Export to HTML: Show Export Menu``` command palette command.


    // Define configurations for the drop down export menu
    "html_panel": [
        // Browser print color (selections and multi-selections allowed)
        {
            "Browser Print - Color": {
                "numbers": true,
                "wrap": 900,
                "browser_print": true,
                "multi_select": true,
                "color_scheme": "Packages/ExportHtml/ColorSchemes/Print-Color.tmTheme",
                "style_gutter": false
            }
        }
     ]


The name of the command is the key value, and then you add the parameters you wish to specify.  You can use any combination of settings below.

- numbers (boolean): Display line numbers in the gutter.
- style_gutter (boolean): Style gutter with theme backgrounds and foregrounds, or just use the default background/foreground.  Default is ```true```.
- multi_select (boolean): If multiple regions are selected in a document, only export what is under those selections. By default only the first selection is recognized.  Default is ```false```
- highlight_selections (boolean): Highlights all selections in HTML output using the themes selection colors.  Multi-select option will be ignored if this is set ```true```.  Default is ```false```
- wrap (integer): Define the allowable size in px to wrap lines at.  By default wrapping is not used.
- color_scheme (string): The color scheme (tmTheme) file you would like to use.  By default the current color scheme file is used, or the the alternate default color scheme if defined in the setting ```alternate_scheme```.
- clipboard_copy (boolean): Copy html to the clipboard after generation. Default is ```false```.
- browser_print (boolean): When opening in the web browser, also open the brower's print dialog. This will be ignored if ```view_open``` is ```true```.  Default is ```false```.
- view_open (boolean): Open HTML in a Sublime Text tab instead of the web browser.  Default is ```false```.
- no_header (boolean): Do not display file name, date, and time at the top of the HTML document. Default is ```false```.
- date_time_format (string): String denoting the format for date and time when displaying header.  Please see Python's documentation on ```time.strftime``` for detailed info on formatting syntax.  Default is ```"%m/%d/%y %I:%M:%S"```
- show_full_path (boolean): Show full path for filename when displaying header. Default is ```true```

If you wish to bind a command to a key combination etc., the same settings as above can be used.

Example:


    {
        "keys": ["ctrl+alt+n"],
        "command": "export_html",
        "args": {
            "numbers": true,
            "wrap": 900,
            "browser_print": true,
            "multi_select": true,
            "color_scheme": "Packages/ExportHtml/ColorSchemes/Print-Color.tmTheme",
            "style_gutter": false
        }
    }

When viewing the HTML in your web browser, regardless of the gutter settings, the gutter can be toggled to show or be hidden using ```shift+double_mouse_click```.

# Usage: Exporting BBCode
ExportHtml can also export selected code as BBCode for posting in forums. Exporting BBCode is very similar to exporting HTML code.

If adding a command to the settings file, it goes under the ```bbcode_panel``` setting.  These configurations will appear under the ```Export to BBCode: Show Export Menu``` command palette command.


    // Define configurations for the drop down export menu
    "bbcode_panel": [
        {
            "To Clipboard - Format as BBCode": {
                "numbers": false,
                "multi_select": true
            }
        }
    ]

The name of the command is the key value, and then you add the parameters you wish to specify.  You can use any combination of settings below.

- numbers (boolean): Display line numbers in the gutter.
- multi_select (boolean): If multiple regions are selected in a document, only export what is under those selections. By default only the first selection is recognized.  Default is ```false```
- color_scheme (string): The color scheme (tmTheme) file you would like to use.  By default the current color scheme file is used, or the the alternate default color scheme if defined in the setting ```alternate_scheme```.
- clipboard_copy (boolean): Copy BBCode to the clipboard after generation. Default is ```true```.
- view_open (boolean): Open txt file of BBCode in a Sublime Text tab.  Default is ```false```.
- no_header (boolean): Do not display file name, date, and time at the top of the HTML document. Default is ```false```.

If you wish to bind a command to a key combination etc., the same settings as above can be used.

Example:


    {
        "keys": ["ctrl+alt+n"],
        "command": "export_bbcode",
        "args": {
            "numbers": false,
            "multi_select": true
        }
    }

# Usage: Annotations (HTML only)
Annotations are comments you can make on selected text.  When the HTML is generated, the selected text will be underlined, and when the mouse hovers over them, a tooltip will appear with your comment.

<img src="http://dl.dropbox.com/u/342698/ExportHtml/annotation_preview.png" border="0"/>

In order to use annotations, you must enter into an "Annotation Mode".  This puts your file in a read only state.  At this point, you can select text and create annotations using the annotation commands provided.  When you leave the "Annotation Mode", all annotations will be lost.  So you must print before leaving annotation mode.

You can access the annotation commands from the command palette or from the context menu.

The commands are as follows:

- Enable Annotation Mode: Turn annotation mode on.
- Disable Annotation Mode: Turn annotation mode off.
- Annotate Selection: Annote the given selection (no multi-select support currently).
- Delete Annotation(s): Delete the annotation region the the cursor resides in (multi-select support).
- Delete All Annotations: Delete all annotation regions.
- Show Annotation Comment: Show the annotation comment of the region under the cursor.

You can navigate the annotations in the generate HTML by using a jump table.  You can show the jump table at any time wiht ```alt+double_mouse_click```.  If it gets in the way, you can dock in the bottom right.

<img src="http://dl.dropbox.com/u/342698/ExportHtml/annotation_table_preview.png" border="0"/>


# Settings File options
- alternate_scheme (string or false): Defines a default theme to be used if a theme is not specified in a command.  When this is false, the current Sublime Text theme in use is used.
- alternate_font_size (int or false): Define an alternate font_size to use by default instead of the current one in use.  Use the current one in use if set to a literal ```false```.  Default is ```false```.
- alternate_font_face (string or false): Define an alternate font_face to use by default instead of the current one in use.  Use the current one in use if set to a literal ```false```.  Default is ```false```.
- valid_selection_size (integer): Minimum allowable size for a selection to be accepted for only the selection to be printed.
- linux_python2.6_lib (string): If you are on linux and Sublime Text is not including your Python 2.6 library folder, you can try and configure it here.
- html_panel (array of commands): Define export configurations to appear under the ```Export to HTML: Show Export Menu``` command palette command.
- bbcode_panel (array of commands): Define export configurations to appear under the ```Export to BBCode: Show Export Menu``` command palette command.

#Credits
- agibsonsw: Original idea and algorithm for the plugin
- Paul Boddie: Desktop module for open files in web browser cross platform
- Print-Color and Print-Grayscale tmThemes were derived from Monokai Bright

# Version 0.4.1
- Add date_time_format and show_full_path options
- Some internal adjustments

# Version 0.4.0
- Fix regression with option numbers = false
- Fix issue where if transparency was included in hex color, color would not render
- Fix regression where annotation table would not show

# Version 0.3.2
- Allow alternate font size and face via the settings file
- Tweak annotation jump table style and code

# Version 0.3.1
- Position annotation jump table in different locations via drop down list

# Version 0.3.0
- Add annotation jump table for the HTML.  Show table with "alt+double_click"

# Version 0.2.0
- Fix issue where html is opened twice
- New annotation feature
- New export to BBCode
- Rename PrintHTML to ExportHTML
- Fix HTML Title (display actual file name of content)
- Update documentation

# Version 0.1.1
- Fix status returnd as None for Windows

# Version 0.1.0
- Initial release
