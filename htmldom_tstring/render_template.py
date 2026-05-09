from __future__ import annotations
from collections.abc import Callable
from string.templatelib import Interpolation, Template, convert
from typing import Any, Iterator, TypeVar

from .compile_template import CompiledTemplate, TemplateValuesList, INTERP, compile_template

ComponentType = TypeVar('ComponentType')

def render(template: Template, component_factory: Callable[[str|Any, list[Any], dict[str, Any]], ComponentType]) -> ComponentType:
    """
    
    component_factory: (tag, child_list, attr_dict) -> component

    This will recursively parse a template string, calling component_factory on each child component.
    Additionally, it will recursively parse any template strings provided as children or passed as parameters.
    """

    return render_template_interpolations(
        iter(template.interpolations),
        compile_template(template),
        component_factory
    )



def render_template_interpolations(interps: Iterator[Interpolation], compiled_template: CompiledTemplate, component_factory: Callable):
    
    
    # start tag
    tag_ = compiled_template.tag
    if isinstance(tag_, list):
        tag = join_strings(tag_, interps)
    elif tag_ is INTERP:
        tag = next_value(interps, _error_tag_name)
    else:
        tag = tag_
    
    # attrs
    attr_dict = {}
    for attr in compiled_template.attributes:
        if attr is INTERP:
            attr_dict.update(next_value(interps, _error_attrs))
            continue

        k, v = attr
        if isinstance(v, list):
            attr_dict[k] = join_strings(v, interps)
        elif v is INTERP:
            attr_dict[k] = next_value(interps, component_factory)
        else:
            attr_dict[k] = v
    
    # children
    children = []
    for child in compiled_template.children:
        if isinstance(child, CompiledTemplate):
            # static child component
            children.append(render_template_interpolations(interps, child, component_factory))

        elif child is INTERP:
            
            children.append(next_value(interps, component_factory))
        else: # str
            children.append(child)

    # validate the end tag (Only necessary in debug mode?)
    end = compiled_template.end_tag
    if isinstance(end, list):
        end_tag = join_strings(end, interps)
    elif end is INTERP:
        end_tag = next_value(interps, component_factory)
    else:
        end_tag = end
    
    if end_tag not in (..., tag):
        raise RuntimeError(f'Start tag {tag!r} and end tag {end_tag!r} do not match.')
    

    
    return component_factory(tag, children, attr_dict)
    

def next_value(interps: Iterator[Interpolation], factory: Callable) -> Any:
    
    i = next(interps)

    v = convert(i.value, i.conversion)
    if i.format_spec:
        v = format(v, i.format_spec)
    if isinstance(v, Template):
        v = render(v, factory)
    return v
              

def next_string(interps: Iterator[Interpolation]) -> str:
    i = next(interps)
    return format(convert(i.value, i.conversion), i.format_spec)

def join_strings(values: TemplateValuesList, interps) -> str:
    return ''.join((next_string(interps) if v is INTERP else v) for v in values)


def _error_attrs(*_):
    raise TypeError('Template cannot be unpacked as a dictionary.')

def _error_tag_name(*_):
    raise TypeError('A Template cannot be used as a tag name.')
