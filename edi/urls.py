from django.urls import path
from .views import VisualValidatorView, ToJson, SocietyListView, CsvOverview

urlpatterns = [
    path('visualvalidator/', VisualValidatorView.as_view(),
         name='visual_validator'),
    path('json/', ToJson.as_view(), name='edi_to_json'),
    path('csv/', CsvOverview.as_view(), name='edi_to_csv'),
    path('societylist/', SocietyListView.as_view(), name='societylist'),
]
