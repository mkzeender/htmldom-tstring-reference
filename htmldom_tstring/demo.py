# future-tstrings

from reactpy import component

from . import render

@component
def simple_wrapper(*children):
    return render(t'<div class="simple-wrapper">{children}</div>')


@component
def demo():
    title_level = 1
    title_style = {"color": "blue"}
    body_style = {"color": "red"}

    paragraphs = {
        "First Title": "Lorem ipsum dolor sit amet. Aut voluptatibus earum non facilis mollitia.",
        "Second Title": "Ut corporis nemo in consequuntur galisum aut modi sunt a quasi deleniti.",
    }

    html_paragraphs = [
        render(t"""
            <h{title_level} { {"style": title_style} }>{title}</{...}>
            <p { {"style": body_style} }>{body}</p>
        """)
        for title, body in paragraphs.items()
    ]

    return render(t"""
        <div>
            <{simple_wrapper} v{10}="hi">{html_paragraphs}</{...}>
        </div>
    """)


