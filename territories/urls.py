from django.urls import path
from .views import TerritoryListView

urlpatterns = [
    path('', TerritoryListView.as_view(), name='territory_list'),
]
