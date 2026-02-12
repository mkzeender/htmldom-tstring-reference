from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser

from types import EllipsisType
from typing import Any, TypeAlias

from enum import Enum, auto, global_enum

from htmldom_tstring.htmldom_tstring import escape_placeholder, unescape_placeholder
from ._eval_arg import eval_constant_arg

TemplateValue: TypeAlias = "InterpType|str"
TemplateValuesList: TypeAlias = "list[TemplateValue]"
HtmlTag: TypeAlias = "TemplateValuesList|TemplateValue"
HtmlChildren: TypeAlias = "list[TemplateValue|ComponentFactory]"
HtmlAttributes: TypeAlias = "list[tuple[str, TemplateValuesList|Any]|InterpType]"


@global_enum
class InterpType(Enum):
    INTERP = auto()
INTERP = InterpType.INTERP

PLACEHOLDER = "x$x"
FRAGMENT = '_fragment'

def compile(template_strings: tuple[str, ...]):
    parser = TemplateParser()

    parser.feed(template_strings[0])
    for string in template_strings[1:]:
        parser.feed(PLACEHOLDER)
        parser.feed(escape_placeholder(string))

    return parser.result()




@dataclass
class ComponentFactory:
    tag: HtmlTag = FRAGMENT
    end_tag: HtmlTag|EllipsisType = ...
    attributes: HtmlAttributes = field(default_factory=list)
    children: HtmlChildren = field(default_factory=list)


class TemplateParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.root = ComponentFactory()
        self.stack = [self.root]
        self.n_interps = 0
    
        
    def feed(self, data) -> None:
        match data:
            case str():
                super().feed(escape_placeholder(data))

            case InterpType.INTERP:
                super().feed(PLACEHOLDER)
                self.n_interps += 1

    def result(self) -> ComponentFactory:
        root = self.root
        self.close()
        match root.children:
            case []:
                raise ValueError("Nothing to return")
            case [ComponentFactory() as child]:
                return child
            case _:
                return self.root
            

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
                    attr_list.append((ks, eval_constant_arg(attr_arg)))
                case [str() as ks], [*interpolated]:
                    # interpolated attr
                    attr_list.append((ks, interpolated))
                case [_, _, *_], _:
                    raise SyntaxError('Interpolated attribute name not supported')
                case _:
                    assert False, 'Should be unreachable'
        
        assert not self.n_interps, 'We should have consumed all interpolations at this point'

        this_node = ComponentFactory(tag_vals, attributes=attr_list)
        self.stack[-1].children.append(this_node)
        self.stack.append(this_node)

    def handle_data(self, data: str) -> None:
        interleaved_children = self.un_placeholderify(data)

        # At this point all interpolated values should have been consumed.
        assert not self.n_interps, "Did not interpolate all values"
        
        self.stack[-1].children.extend(interleaved_children)

    def handle_endtag(self, tag: str) -> None:
        node = self.stack.pop()
        end_tag = self.un_placeholderify(tag)

        assert not self.n_interps, 'Did not consume all interpolations'

        match node.tag, end_tag:
            case _, [InterpType.INTERP]:
                end_tag = InterpType.INTERP
            
            case str(), [str() as s]:
                end_tag = s
                if end_tag != node.tag:
                    raise SyntaxError(f'End tag {s} does not match start tag {node.tag}')
            
            case [*_], [str() as s]:
                raise SyntaxError(f'End tag {s} does not match start tag.')
            
            case _:
                pass
        
        node.end_tag = end_tag

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        
        self.stack.pop()

    def handle_comment(self, data: str) -> None:
        match self.un_placeholderify(data):
            case [str()]:
                pass
            case _:
                raise SyntaxError('Interpolations not allowed in comments')
    
    def handle_decl(self, decl: str) -> None:
        match self.un_placeholderify(decl):
            case [str()]:
                pass
            case _:
                raise SyntaxError('Interpolations not allowed in decl')
    
    def handle_pi(self, data: str) -> None:
        match self.un_placeholderify(data):
            case [str()]:
                pass
            case _:
                raise SyntaxError('Interpolations not allowed in PI')


                


    def un_placeholderify(self, string: str) -> list[str|InterpType]:
        if string == PLACEHOLDER:
            self.n_interps -= 1
            return [INTERP]

        *string_parts, last_string_part = string.split(PLACEHOLDER)
        remaining_n_interps = self.n_interps - len(string_parts)

        interleaved_values = [
            item
            for s in string_parts
            for item in (unescape_placeholder(s), INTERP)
        ]
        interleaved_values.append(last_string_part)

        self.n_interps = remaining_n_interps
        return interleaved_values

