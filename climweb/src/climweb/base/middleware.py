from django.http import HttpResponsePermanentRedirect


class StripHomePageSlugMiddleware:
    """
    Redirect any requests prefixed with '/home-page/' to the clean canonical public URL.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path_info.startswith("/home-page/"):
            new_path = request.path_info[len("/home-page"):]
            if request.META.get("QUERY_STRING"):
                new_path = f"{new_path}?{request.META['QUERY_STRING']}"
            return HttpResponsePermanentRedirect(new_path)
        elif request.path_info == "/home-page":
            new_path = "/"
            if request.META.get("QUERY_STRING"):
                new_path = f"{new_path}?{request.META['QUERY_STRING']}"
            return HttpResponsePermanentRedirect(new_path)
        return self.get_response(request)
