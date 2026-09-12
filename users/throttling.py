from rest_framework.throttling import SimpleRateThrottle


class DemoUserRateThrottle(SimpleRateThrottle):
    """Apply a modest per-IP limit only to the shared public demo account."""

    scope = 'demo_user'

    def get_cache_key(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_demo:
            return None

        ident = f'{user.pk}:{self.get_ident(request)}'
        return self.cache_format % {'scope': self.scope, 'ident': ident}
