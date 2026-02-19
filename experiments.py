# future-tstringsuv
from htmldom_tstring.compile_template import compile_template

title_level = 1
title_style = {}
title = 'Title Hello World'
v = compile_template(t"<h{title_level} style={title_style}>{title}</{...}>")
...