import pytest
from django.test import RequestFactory
from core.middleware import SlowQueryLogMiddleware


@pytest.mark.django_db
class TestSlowQueryLogMiddleware:
    def test_middleware_passes_response_through(self):
        factory = RequestFactory()
        request = factory.get('/api/v1/books/')

        def get_response(request):
            from django.http import HttpResponse
            return HttpResponse('OK')

        middleware = SlowQueryLogMiddleware(get_response)
        response = middleware(request)
        assert response.status_code == 200
