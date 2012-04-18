# About
This is a fork of agibsonsw's [PrintHtml](https://github.com/agibsonsw/PrintHtml) plugin.  This plugin allows the printing of a document in ST2 to an HTML file.  It duplicates ST2's theme colors and font styles.

<img src="http://dl.dropbox.com/u/342698/PrintHtml/preview.png" border="0"/>

# Features
- Print to HTML using any tmTheme for syntax highlighting
- Can handle any language supported by ST2
- Supports bold and italic theme font styles as well
- Configurable output
- Format suitable for copying and pasting in emails
- 2 included tmTheme files for color and grayscale printing (but any can be used)
- Print only selections (multi-select supported)
- Print and show highlights (multi-select supported)
- Toggle gutter on/off in browser view
- Automatically open browser print dialog (optional)
- Enable/disable configurable word wrapping

# Usage
PrintHtml comes with a number of default commands available, but these can be overridden in the settings file.  Or you can create commands directly outside of the settings file bound to the command palette, key bindings, or even the menu.

If adding a command to the settings file, it goes under the ```print_panel``` setting.  These configurations will appear under the ```Print to HTML: Show Print Menu``` command palette command.


    // Define configurations for the drop down print menu
    "print_panel": [
        // Browser print color (selections and multi-selections allowed)
        {
            "Browser Print - Color": {
                "numbers": true,
                "wrap": 900,
                "browser_print": true,
                "multi_select": true,
                "color_scheme": "Packages/PrintHtml/ColorSchemes/Print-Color.tmTheme",
                "style_gutter": false
            }
        }
     ]


The name of the command is the key value, and then you add the parameters you wish to specify.  You can use any combination of settings below.

- numbers (boolean): Display line numbers in the gutter.
- style_gutter (boolean): Style gutter with theme backgrounds and foregrounds, or just use the default background/foreground.  Default is ```true```.
- multi_select (boolean): If multiple regions are selected in a document, only print what is under those selections. By default only the first selection is recognized.  Default is ```false```
- highlight_selections (boolean): Highlights all selections in HTML output using the themes selection colors.  Multi-select option will be ignored if this is set ```true```.  Default is ```false```
- wrap (integer): Define the allowable size in px to wrap lines at.  By default wrapping is not used.
- color_scheme (string): The color scheme (tmTheme) file you would like to use.  By default the current color scheme file is used, or the the alternate default color scheme if defined in the setting ```alternate_scheme```.
- clipboard_copy (boolean): Copy html to the clipboard after generation. Default is ```false```.
- browser_print (boolean): When opening in the web browser, also open the brower's print dialog. This will be ignored if ```view_open``` is ```true```.  Default is ```false```.
- view_open (boolean): Open HTML in a Sublime Text tab instead of the web browser.  Default is ```false```.
- no_header (boolean): Do not display file name, date, and time at the top of the HTML document. Default is ```false```.

If you wish to bind a command to a key combination etc., the same settings as above can be used.

Example:


    {
        "keys": ["ctrl+alt+n"],
        "command": "print_html",
        "args": {
            "numbers": true,
            "wrap": 900,
            "browser_print": true,
            "multi_select": true,
            "color_scheme": "Packages/PrintHtml/ColorSchemes/Print-Color.tmTheme",
            "style_gutter": false
        }
    }


## Settings File options
- alternate_scheme (string or false): Defines a default theme to be used if a theme is not specified in a command.  When this is false, the current Sublime Text theme in use is used.
- valid_selection_size (integer): Minimum allowable size for a selection to be accepted for only the selection to be printed.
- linux_python2.6_lib (string): If you are on linux and Sublime Text is not including your Python 2.6 library folder, you can try and configure it here.
- print_panel (array of commands): Define print configurations to appear under the ```Print to HTML: Show Print Menu``` command palette command.

#Credits
- agibsonsw: Original idea and algorithm for the plugin
- Paul Boddie: Desktop module for open files in web browser cross platform

# Version 0.1.0
- Initial release
