from django.urls import path

from .views import BookSearchView, AutocompleteView

urlpatterns = [
    path("search/", BookSearchView.as_view(), name="book-search"),
    path("search/autocomplete/", AutocompleteView.as_view(), name="autocomplete"),
]
