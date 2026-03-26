from django.shortcuts import redirect
from django.urls import reverse
from django.http import JsonResponse

class FirstLoginMiddleware:
    """
    Middleware to force users to change their password on first login.
    Blocks all API access except for login and change-password if is_first_login is True.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        # Normalize path (handle double slashes)
        while '//' in path:
            path = path.replace('//', '/')

        if request.user.is_authenticated:
            from django.urls import resolve
            
            # Exempt paths
            exempt_url_names = [
                'login', 'change_password', 'logout', 'health', 'test', 'profile'
            ]
            exempt_prefixes = ['/admin/', '/swagger/', '/redoc/', '/favicon.ico']
            
            # 1. Check by URL name (robust)
            try:
                match = resolve(path)
                if match.url_name in exempt_url_names:
                    return self.get_response(request)
            except:
                pass
            
            # 2. Check by prefix
            if any(path.startswith(prefix) for prefix in exempt_prefixes):
                return self.get_response(request)

            # 3. If first login required, block everything else
            if request.user.is_first_login:
                return JsonResponse({
                    'error': 'Please change your password first.',
                    'force_password_change': True,
                    'is_first_login': True
                }, status=403)

        response = self.get_response(request)
        return response
