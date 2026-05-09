# future-tstringsuv
from htmldom_tstring import stringify_component_factory, render

title_level = 1
title_style = {}
title = 'Title Hello World'
v = render(
    t"""
           <h{title_level} style={title_style}>
                  {title}
                  </{...}>
           
    """, stringify_component_factory)
print(v)
