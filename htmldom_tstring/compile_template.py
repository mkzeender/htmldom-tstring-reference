"""
Loosely Adapted from jimbaker https://github.com/jimbaker/tagstr/tree/6c8f3fd34575403e77fab5065bfb44ae9063c457


"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from html.parser import HTMLParser
import itertools
import sys
from types import EllipsisType
from typing import Any, Never, TypeAlias
from enum import Enum, auto, global_enum

from string.templatelib import Interpolation, Template

# from ._eval_arg import eval_constant_arg


TemplateValue: TypeAlias = "InterpType|str"
TemplateValuesList: TypeAlias = list[TemplateValue]
HtmlTag: TypeAlias = "TemplateValuesList|TemplateValue"
HtmlChildren: TypeAlias = "list[TemplateValue|ComponentFactory]"
HtmlAttributes: TypeAlias = "list[tuple[str, TemplateValuesList|Any]|InterpType]"


@global_enum
class InterpType(Enum):
    INTERP = auto()

INTERP = InterpType.INTERP
FRAGMENT = '_'
PLACEHOLDER = "x$x"


class ReactSyntaxError(SyntaxError):
    pass


def escape_placeholder(string: str) -> str:
    return string.replace("$", "$$")


def unescape_placeholder(string: str) -> str:
    return string.replace("$$", "$")

def compile_template_strings(template: Template):
    parser = TemplateParser()

    for v in template:
        parser.feed(v)

    return parser.result()

def _unparse_interpolation_expression(i: Interpolation):
    fmt = f':{i.format_spec}' if i.format_spec else ''
    conv = f'!{i.conversion}' if i.conversion else ''
    expr = i.expression.replace('\r\n', ' ').replace('\r', '').replace('\n', '')
    return '{' + expr + conv + fmt + '}'




@dataclass
class ComponentFactory:
    tag: HtmlTag = FRAGMENT
    end_tag: HtmlTag|EllipsisType = ...
    attributes: HtmlAttributes = field(default_factory=list)
    children: HtmlChildren = field(default_factory=list)


class TemplateParser(HTMLParser):

    def __init__(self, filename: str = '<template string>'):
        super().__init__()
        self.stack = [ComponentFactory()]
        self.interps: deque[Interpolation] = deque()
        self._removed_interps: list[Interpolation] = []
        self.filename = filename
        
    def feed(self, data: str|Interpolation) -> None:
        match data:
            case str():
                super().feed(escape_placeholder(data))

            case Interpolation():
                self.interps.append(data)
                super().feed(PLACEHOLDER)

    
    def error(self, message: str, linetext: TemplateValuesList|None=None) -> Never:
        
        if linetext is not None:
            if linetext.count(INTERP) == len(self._removed_interps):
                interps = (_unparse_interpolation_expression(i) for i in reversed(self._removed_interps))
            else:
                interps = itertools.repeat('{...}')

            
            line = ''
            for s in linetext:
                match s:
                    case str():
                        line += s
                    case InterpType.INTERP:
                        line += next(interps)
            
            if sys.version_info > (3, 10):
                raise ReactSyntaxError(message, (self.filename, 1, 0, line, 1, len(line)-1))
            raise ReactSyntaxError(message, (self.filename, 1, 0, line))
        else:
            raise ReactSyntaxError(message, (self.filename, None, None, None))   
                

    def result(self) -> ComponentFactory:
        if len(self.stack) > 1:
            self.error(f'{self.stack[1].tag!r} element was never closed')
        if self.interps:
            self.error('Some interpolations were not consumed')
        
        root = self.stack[0]
        self.close()
        
        match root.children:
            case [ComponentFactory() as child]:
                return child
            case _:
                return root
            

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_vals = self.un_placeholderify(tag)

        # TODO: add logic for static tags?
        match tag_vals:
            case [(str() | InterpType.INTERP) as tag_]:
                tag_vals = tag_
            case [*_]:
                pass
        attr_list: HtmlAttributes = []

        for k, v in attrs:
            k_vals = self.un_placeholderify(k)
            v_vals = None if v is None else self.un_placeholderify(v)

            match k_vals, v_vals:
                case [InterpType.INTERP as ki], None:
                    # dict of attrs
                    attr_list.append(ki)
                case [str() as ks], [INTERP]:
                    # variable attr
                    attr_list.append((ks, INTERP))
                case [str() as ks], [str() as attr_arg]:
                    # constant attr
                    # TODO: more robust compilation for constants?
                    # attr_list.append((ks, eval_constant_arg(attr_arg)))
                    attr_list.append((ks, attr_arg))
                case [str() as ks], [*interpolated]:
                    # interpolated attr
                    attr_list.append((ks, interpolated))
                case [_, _, *_], _:
                    self.error('Interpolated attribute name not supported', linetext=v_vals)
                case _:
                    assert False, 'Should be unreachable'
        
        assert not self.interps, 'We should have consumed all interpolations at this point'

        this_node = ComponentFactory(tag_vals, attributes=attr_list)
        self.stack[-1].children.append(this_node)
        self.stack.append(this_node)

    def handle_data(self, data: str) -> None:
        interleaved_children = self.un_placeholderify(data)

        # At this point all interpolated values should have been consumed.
        assert not self.interps, "Did not interpolate all values"
        
        self.stack[-1].children.extend(interleaved_children)

    def handle_endtag(self, tag: str) -> None:
        node = self.stack.pop()
        tag_vals = self.un_placeholderify(tag)
        if not self.stack:
            self.error('Unexpected end tag.', tag_vals)
        
        assert not self.interps, 'Did not consume all interpolations'

        match node.tag, tag_vals:
            case _, [InterpType.INTERP]:
                end_tag = InterpType.INTERP
            
            case str(), [str() as s]:
                end_tag = s
                if end_tag != node.tag:
                    self.error(f'End tag {s} does not match start tag {node.tag}', tag_vals)
            
            case [*_], [str() as s]:
                self.error(f'End tag {s} does not match start tag.')
            
            case _:
                # dynamic tag name
                end_tag = tag_vals
        
        node.end_tag = end_tag

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.stack.pop()


    def handle_comment(self, data: str) -> None:
        dat = self.un_placeholderify(data)
        if INTERP in dat:
            self.error('Interpolations not allowed in comments', dat)
    
    def handle_decl(self, decl: str) -> None:
        dat = self.un_placeholderify(decl)
        if INTERP in dat:
            self.error('Interpolations not allowed in decl', dat)
    
    def handle_pi(self, data: str) -> None:
        dat = self.un_placeholderify(data)
        if INTERP in dat:
            self.error('Interpolations not allowed in PI', dat)


    def un_placeholderify(self, string: str) -> TemplateValuesList:
        
        string_parts = string.split(PLACEHOLDER)

        interleaved_values = [
            item
            for s in string_parts
            for item in (unescape_placeholder(s), INTERP) if item != ''
        ]
        # remove unnecessary trailing INTERP
        interleaved_values.pop()


        self._removed_interps = [self.interps.popleft() for _ in range(len(string_parts) - 1)]
                
        return interleaved_values

