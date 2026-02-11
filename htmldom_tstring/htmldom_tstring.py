"""
Adapted from jimbaker https://github.com/jimbaker/tagstr/tree/6c8f3fd34575403e77fab5065bfb44ae9063c457


"""
from __future__ import annotations

from textwrap import dedent
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from html import escape
from html.parser import HTMLParser

from string.templatelib import Template, Interpolation, convert
from typing import Any, Union


def html(template: Template) -> HtmlNode:
    parser = HtmlNodeParser()
    for arg in template:
        parser.feed(arg)
    return parser.result()


HtmlChildren = list[Union["HtmlNode", str]]
HtmlAttributes = dict[str, Any]


@dataclass(slots=True)
class HtmlNode:
    tag: str | Callable[..., HtmlNode] = ""
    attributes: HtmlAttributes = field(default_factory=dict)
    children: HtmlChildren = field(default_factory=list)

    def render(self) -> HtmlNode:
        # TODO: here is where we check for a reactpy Component
        if callable(self.tag):
            return self.tag(self.children, **self.attributes).render()
        else:
            return HtmlNode(
                self.tag,
                self.attributes,
                [c.render() if isinstance(c, HtmlNode) else c for c in self.children],
            )

    def __str__(self) -> str:
        node = self.render()

        attribute_list: list[str] = []
        for key, value in node.attributes.items():
            match key, value:
                case _, True:
                    attribute_list.append(f" {key}")
                case _, False | None:
                    pass
                case "style", style:
                    if not isinstance(style, dict):
                        raise TypeError("Expected style attribute to be a dictionary")
                    css_string = escape("; ".join(f"{k}:{v}" for k, v in style.items()))
                    attribute_list.append(f' style="{css_string}"')
                case _:
                    attribute_list.append(f' {key}="{escape(str(value))}"')

        children_list: list[str] = []
        for item in node.children:
            match item:
                case "":
                    pass
                case str():
                    item = escape(item, quote=False)
                case HtmlNode():
                    item = str(item)
                case _:
                    item = str(item)
            children_list.append(item)

        body = "".join(children_list)

        if not node.tag:
            if node.attributes:
                raise ValueError("Untagged node cannot have attributes.")
            result = body
        else:
            attr_body = "".join(attribute_list)
            result = f"<{node.tag}{attr_body}>{body}</{node.tag}>"

        return dedent(result)


class HtmlNodeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = HtmlNode()
        self.stack = [self.root]
        self.values: list[Any] = []

    def feed(self, data: str | Interpolation) -> None:
        match data:
            case str():
                super().feed(escape_placeholder(data))

            case Interpolation(value=value,conversion=conv, format_spec=spec):
                value = convert(value, conv)
                if spec:
                    value = format(value, spec)
                
                self.values.append(value)
                super().feed(PLACEHOLDER)

    def result(self) -> HtmlNode:
        root = self.root
        self.close()
        match root.children:
            case []:
                raise ValueError("Nothing to return")
            case [HtmlNode() as child]:
                return child
            case _:
                return self.root

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag, self.values = join_with_values(tag, self.values)

        node_attrs = {}
        for k, v in attrs:
            if k == PLACEHOLDER and v is None:
                expansion_value, *self.values = self.values
                node_attrs.update(expansion_value)
            elif PLACEHOLDER in k:
                raise SyntaxError("Cannot interpolate attribute names")
            elif v == PLACEHOLDER:
                interpolated_value, *self.values = self.values
                node_attrs[k] = interpolated_value
            elif v is None:
                raise SyntaxError(f"Attribute key {k!r} has no value.")
            else:
                interpolated_value, self.values = join_with_values(v, self.values)
                node_attrs[k] = interpolated_value

        # At this point all interpolated values should have been consumed.
        assert not self.values, "Did not interpolate all values"

        this_node = HtmlNode(tag, node_attrs)
        last_node = self.stack[-1]
        last_node.children.append(this_node)
        self.stack.append(this_node)

    def handle_data(self, data: str) -> None:
        interleaved_children, self.values = interleave_with_values(data, self.values)

        # At this point all interpolated values should have been consumed.
        assert not self.values, "Did not interpolate all values"

        for child in interleaved_children:
            self.handle_child(child)

    
    def handle_child(self, child):
        match child:
            case [*_]: # does not match strings
                for elt in child:
                    self.handle_child(elt)
            case "":
                pass
            case Template():
                self.stack[-1].children.append(html(child))
            case _:
                self.stack[-1].children.append(child)

        

    def handle_endtag(self, tag: str) -> None:
        node = self.stack.pop()

        if tag == PLACEHOLDER:
            interp_tag, *self.values = self.values
        else:
            interp_tag, self.values = join_with_values(tag, self.values)

        # At this point all interpolated values should have been consumed.
        assert not self.values, "Did not interpolate all values"

        if interp_tag is ...:
            # handle end tag shorthand
            return None

        if interp_tag != node.tag:

            raise SyntaxError(
                "Start tag {node.tag!r} does not match end tag {interp_tag!r}"
            )


# We choose this symbol because, after replacing all $ with $$, there is no way for a
# user to feed a string that would result in x$x. Thus we can reliably split an HTML
# data string on x$x. We also choose this because, the HTML parse looks for tag names
# begining with the regex pattern '[a-zA-Z]'.
PLACEHOLDER = "x$x"


def escape_placeholder(string: str) -> str:
    return string.replace("$", "$$")


def unescape_placeholder(string: str) -> str:
    return string.replace("$$", "$")


def join_with_values(string: str, values: list[Any]) -> tuple[str, list[Any]]:
    interleaved_values, remaining_values = interleave_with_values(string, values)
    match interleaved_values:
        case [value]:
            return value, remaining_values
        case values:
            return "".join(map(str, values)), remaining_values


def interleave_with_values(
    string: str, values: list[Any]
) -> tuple[list[Any], list[Any]]:
    if string == PLACEHOLDER:
        return values[:1], values[1:]

    *string_parts, last_string_part = string.split(PLACEHOLDER)
    remaining_values = values[len(string_parts) :]

    interleaved_values = [
        item
        for s, v in zip(string_parts, values)
        for item in (unescape_placeholder(s), v)
    ]
    interleaved_values.append(last_string_part)

    return interleaved_values, remaining_values

