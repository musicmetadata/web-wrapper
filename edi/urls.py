from django.urls import path
from .views import VisualValidatorView, ToJson, SocietyListView

urlpatterns = [
    path('visualvalidator/', VisualValidatorView.as_view(),
         name='visual_validator'),
    path('json/', ToJson.as_view(), name='edi_to_json'),
    path('societylist/', SocietyListView.as_view(), name='societylist'),
]
