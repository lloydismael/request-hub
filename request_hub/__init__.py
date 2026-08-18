"""Project package initialization.

Django 4.2.x is not fully compatible with Python 3.14's `copy.copy()` behavior for
`django.template.context.BaseContext`. The Django test client calls `copy(context)`
while rendering templates, which triggers `BaseContext.__copy__` and breaks with:

    AttributeError: 'super' object has no attribute 'dicts'

The compatibility shim below avoids using `copy(super())` and keeps the app working
under the current runtime without changing app behavior.
"""

from __future__ import annotations


def _patch_django_context_copy_compat() -> None:
    """Work around Python 3.14 + Django 4.2 template context copying bug."""
    try:
        from django.template import context as template_context
    except Exception:
        return

    base_context = getattr(template_context, "BaseContext", None)
    if base_context is None or getattr(base_context, "_req_hub_copy_compat", False):
        return

    def __copy__(self):
        duplicate = self.__class__.__new__(self.__class__)
        duplicate.__dict__.update(self.__dict__)
        if hasattr(self, "dicts"):
            duplicate.dicts = self.dicts[:]
        return duplicate

    base_context.__copy__ = __copy__
    base_context._req_hub_copy_compat = True


_patch_django_context_copy_compat()
