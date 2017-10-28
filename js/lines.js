var page_line_info = {
  wrap: false,
  ranges: null,
  wrap_size: null,
  tables: null,
  header: null,
  gutter: false,
  table_mode: true
};

function wrap_code() {
  var width = 0,
      mode = null,
      start, end, i, j, idx, el;

  if (page_line_info.header) {
    el = document.getElementById("file_info");
    el.style.width = page_line_info.wrap_size + "px";
    el.className = "wrap";
  }
  for (i = 1; i <= page_line_info.tables; i++) {
    idx = i - 1;
    start = page_line_info.ranges[idx][0];
    end = page_line_info.ranges[idx][1];
    for(j = start; j < end; j++) {
      if (isNull(mode)) {
        mode = true;
        if (page_line_info.gutter) {
          width = document.getElementById("L_" + idx + "_" + j).offsetWidth;
        }
      }
      el = document.getElementById("C_" + idx + "_" + j);
      el.style.width = (page_line_info.wrap_size - width) + "px";
      el.className = page_line_info.table_mode ? "wrap" : "wrap code_line";
    }
  }
}

function toggle_gutter() {
  var default_mode = page_line_info.table_mode ? 'table-cell' : 'inline-block',
      mode = null,
      i, j, rows, r, tbls, cells;

  items = document.querySelectorAll('.code_gutter');
  for (i = 0; i < items.length; ++i) {
    if (isNull(mode)) {
      if (page_line_info.gutter) {
        mode = 'none';
        page_line_info.gutter = false;
      } else {
        mode = 'inline-block';
        page_line_info.gutter = true;
      }
    }
    items[i].style.display = mode;
  }
  if (page_line_info.wrap && !isNull(mode)) {
      setTimeout(function() {wrap_code();}, 500);
  }
}

function unwrap_code() {
  var i, j, idx, start, end, el;

  if (page_line_info.header) {
    document.getElementById("file_info").style.width = "100%";
  }
  for (i = 1; i <= page_line_info.tables; i++) {
    idx = i - 1;
    start = page_line_info.ranges[idx][0];
    end = page_line_info.ranges[idx][1];
    for(j = start; j < end; j++) {
      el = document.getElementById("C_" + idx + "_" + j);
      el.style.width = "100%";
      el.className = "";
    }
  }
}

function toggle_wrapping() {
  if (page_line_info.wrap) {
    page_line_info.wrap = false;
    unwrap_code();
  } else {
    page_line_info.wrap = true;
    wrap_code();
  }
}
