from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def ten_template(context):
    return context.template.name
