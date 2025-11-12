from django.conf import settings
from django.shortcuts import redirect
from django.urls import resolve, Resolver404


def _is_exempt(view_name: str) -> bool:
    if not view_name:
        return False
    exempt = set(settings.PROFILE_COMPLETION_EXEMPT_URLS)
    exempt.update({"login", "logout", "accounts:update"})
    if view_name in exempt:
        return True
    if view_name.startswith("admin:"):
        return True
    return False


class ProfileCompletionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated and user.must_complete_profile():
            try:
                match = resolve(request.path_info)
                view_name = match.view_name
            except Resolver404:
                view_name = None
            if not _is_exempt(view_name):
                return redirect("accounts:update")
        return self.get_response(request)
