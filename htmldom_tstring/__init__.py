

from .render_template import render as render
from html import escape


def _escape_to_string(value, mode):
    if isinstance(value, str):
        value = value.replace('{', '{{').replace('}', '}}').replace('\n', '{"\\n"}')
        if mode == 1:
             value = f'"{escape(value, quote=True)}"'
        else:
             value = escape(value, quote=False)

    elif hasattr(value, '__name__'):
        value = f"{{{value.__name__}}}"
    elif mode == 2:
         value = "{...}"
    else:
        value = f"{{ {value!r} }}"

    return value



def stringify_component_factory(tag, child_list, attr_dict) -> str:

        tag =_escape_to_string(tag, 0)

        val = '<' + tag

        for k, v in attr_dict.items():
            val += f' {k}={_escape_to_string(v, 1)}'

        val += '>\n'
            
        for child in child_list:
            if not (isinstance(child, str) and child.startswith('<')):
                 child = _escape_to_string(child, 0)
                 
            for line in child.splitlines():
                val += f"  {line}\n"

        val += f"</{_escape_to_string(tag, 2)}>"


        return val