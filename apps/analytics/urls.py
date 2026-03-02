from django.urls import path
from .views import TopBooksView

urlpatterns = [
    path('analytics/top/', TopBooksView.as_view(), name='analytics-top-books'),
]
