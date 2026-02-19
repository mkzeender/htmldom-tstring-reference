from __future__ import annotations
from string.templatelib import Interpolation, convert
from typing import Any, Iterator

import reactpy.html as reactpy_html

from .compile_template import ComponentFactory, TemplateValuesList, INTERP

HTML_TAG = set(reactpy_html.__all__)

  

def render_template_interpolations(interps: Iterator[Interpolation], factory: ComponentFactory):
    
    # start tag
    tag_ = factory.tag
    if isinstance(tag_, list):
        tag = join_strings(tag_, interps)
    elif tag_ is INTERP:
        tag = next_value(interps)
    else:
        tag = tag_
    
    # attrs
    attr_dict = {}
    for attr in factory.attributes:
        if attr is INTERP:
            attr_dict.update(next_value(interps))
            continue

        k, v = attr
        if isinstance(v, list):
            attr_dict[k] = join_strings(v, interps)
        elif v is INTERP:
            attr_dict[k] = next_value(interps)
        else:
            attr_dict[k] = v
    
    # children
    children = []
    for child in factory.children:
        if isinstance(child, ComponentFactory):
            children.append(render_template_interpolations(interps, child))

        elif child is INTERP:
            children.append(next_value(interps))
        else:
            children.append(child)

    # validate the end tag (Only necessary in debug mode?)
    end = factory.end_tag
    if isinstance(end, list):
        end_tag = join_strings(end, interps)
    elif end is INTERP:
        end_tag = next_value(interps)
    else:
        end_tag = end
    
    if end_tag not in (..., tag):
        raise RuntimeError(f'Start tag {tag!r} and end tag {end_tag!r} do not match.')
    

    
    
    
    if isinstance(tag, str):

        if tag in HTML_TAG:
            return getattr(reactpy_html, tag)(attr_dict, *children)
        else:
            # TODO: lookup tag names in the Component's global namespace?
            raise NameError('Tag name {tag!r} does not exist', name=tag)
    else:
        # TODO: should this be correct for user-defined tags? In practice, it will contain a bunch of whitespace strings
        return tag(*children, **attr_dict)
    
    
        
    

def next_value(interps: Iterator[Interpolation]) -> Any:
    
    i = next(interps)

    v = convert(i.value, i.conversion)
    if i.format_spec:
        v = format(v, i.format_spec)
    return v
              

def next_string(interps: Iterator[Interpolation]) -> str:
    i = next(interps)
    return format(convert(i.value, i.conversion), i.format_spec)

def join_strings(values: TemplateValuesList, interps) -> str:
    return ''.join((next_string(interps) if v is INTERP else v) for v in values)