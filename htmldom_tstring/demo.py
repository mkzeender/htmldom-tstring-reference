# future-tstrings

from .htmldom_tstring import html


def demo():
    title_level = 1
    title_style = {"color": "blue"}
    body_style = {"color": "red"}

    paragraphs = {
        "First Title": "Lorem ipsum dolor sit amet. Aut voluptatibus earum non facilis mollitia.",
        "Second Title": "Ut corporis nemo in consequuntur galisum aut modi sunt a quasi deleniti.",
    }

    html_paragraphs = [
        t"""
             <h{title_level} { {"style": title_style} }>{title}</{...}>
             <p { {"style": body_style} }>{body}</p>
        """
        
        for title, body in paragraphs.items()
    ]

    def simple_wrapper(*children):
        return t'<div class="simple-wrapper">{children}</div>'


    result = html(t"<simple_wrapper>{html_paragraphs}</simple_wrapper>")
    print(result)

