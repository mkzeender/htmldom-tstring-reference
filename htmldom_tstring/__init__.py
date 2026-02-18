
from string.templatelib import Template

from reactpy.core.types import VdomDict

from .render_template import render_template_interpolations
from .compile_template import compile_template_strings

def render(template: Template) -> VdomDict:
    return render_template_interpolations(iter(template.interpolations), compile_template_strings(template))


