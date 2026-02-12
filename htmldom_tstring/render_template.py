from __future__ import annotations
from string.templatelib import Interpolation, convert
from typing import Any, Iterator

from .compile_template import ComponentFactory, TemplateValuesList, INTERP
  

def render_template_values(interps: Iterator[Interpolation], factory: ComponentFactory):
    
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
        else:
            attr_dict[k] = v
    
    # children
    children = []
    for child in factory.children:
        if isinstance(child, ComponentFactory):
            children.append(render_template_values(interps, child))

        elif child is INTERP:
            children.append(next_value(interps))
        else:
            children.append(child)

    # end tag
    end = factory.end_tag
    if isinstance(end, list):
        end_tag = join_strings(end, interps)
    elif end is INTERP:
        end_tag = next_value(interps)
    else:
        end_tag = end
    
    if end_tag not in (..., tag):
        raise RuntimeError(f'Start tag {tag!r} and end tag {end_tag!r} do not match.')
    

    # TODO: return Component(tag=tag, )
    
    
    
    
        
    

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