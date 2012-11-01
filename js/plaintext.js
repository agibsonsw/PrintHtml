/*jshint globalstrict: true*/
"use strict";

function toggle_plain_text() {
    var lines = document.querySelectorAll("td.code_line"),
        line_len = lines.length,
        i, text = "", pre,
        orig_pre = document.querySelectorAll("pre.code_page")[0],
        plain_pre = document.querySelectorAll("pre.simple_code_page");
    if (plain_pre.length > 0) {
        document.body.removeChild(plain_pre[0]);
        orig_pre.style.display = 'block';
        document.body.className = "code_page";
    } else {
        for (i = 1; i < line_len; i++) {
            text += lines[i].textContent;
        }
        pre = document.createElement('pre');
        pre.className = "simple_code_page";
        pre.appendChild(document.createTextNode(text));
        orig_pre.style.display = 'none';
        document.body.appendChild(pre);
        document.body.className = "simple_code_page";
    }
}
